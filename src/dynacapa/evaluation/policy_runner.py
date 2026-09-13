"""Guarded Transformers runner for the policy benchmark."""

from __future__ import annotations

import csv
import importlib.metadata
import json
import random
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import Field

from dynacapa.core.schemas import StrictModel
from dynacapa.evaluation.policy_benchmark import (
    GenerationRecord,
    PolicyEvaluationConfig,
    canonical_json,
    read_mail_records,
    read_sft_examples,
    score_generations,
    select_stratified_examples,
    sha256_file,
)


class EvaluationReadinessReport(StrictModel):
    ready: bool
    run_id: str
    checks: dict[str, bool]
    blockers: tuple[str, ...] = ()
    evidence: dict[str, Any] = Field(default_factory=dict)


def validate_evaluation_readiness(
    root: Path,
    config: PolicyEvaluationConfig,
    *,
    require_registry: bool = True,
    require_dependency_lock: bool = True,
) -> EvaluationReadinessReport:
    root = root.resolve()
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    evidence: dict[str, Any] = {}

    source_path, source_manifest = _validate_manifest(
        root,
        config.data.source_manifest_path,
        config.data.source_manifest_sha256,
        "source_manifest",
        checks,
        blockers,
        evidence,
    )
    prompt_path, training_manifest = _validate_manifest(
        root,
        config.data.training_manifest_path,
        config.data.training_manifest_sha256,
        "training_manifest",
        checks,
        blockers,
        evidence,
    )

    source_artifact = _validate_artifact(
        root,
        source_manifest,
        config.data.source_key,
        "source",
        checks,
        blockers,
        evidence,
    )
    prompt_artifact = _validate_artifact(
        root,
        training_manifest,
        config.data.prompt_key,
        "prompt",
        checks,
        blockers,
        evidence,
    )
    del source_path, prompt_path

    frozen_sealed = (
        config.data.source_key != "frozen_test"
        and not bool(
            training_manifest.get("eligibility", {}).get("frozen_test_accessed", True)
        )
    )
    checks["frozen_test_sealed"] = frozen_sealed
    if not frozen_sealed:
        blockers.append("frozen test is not sealed for this evaluation")

    if source_artifact and prompt_artifact:
        counts_match = source_artifact.get("records") == prompt_artifact.get("records")
        checks["source_prompt_counts_match"] = counts_match
        if not counts_match:
            blockers.append("source and prompt artifact record counts differ")
        enough_examples = int(source_artifact.get("records", 0)) >= config.generation.max_examples
        checks["enough_examples"] = enough_examples
        if not enough_examples:
            blockers.append("max_examples exceeds validation artifact size")

    output = _within_root(root, config.output_dir, "output")
    checks["output_dir_absent"] = not output.exists()
    if output.exists():
        blockers.append(f"output directory already exists: {config.output_dir}")

    if config.model.adapter_path is not None:
        adapter = _within_root(root, config.model.adapter_path, "adapter")
        checks["adapter_exists"] = adapter.is_dir()
        if not adapter.is_dir():
            blockers.append(f"adapter directory is missing: {config.model.adapter_path}")

    lock = _within_root(root, config.expected_dependency_lock, "dependency lock")
    checks["dependency_lock_exists"] = lock.is_file()
    if require_dependency_lock and not lock.is_file():
        blockers.append(f"dependency lock is missing: {config.expected_dependency_lock}")

    registered = _registry_has_run(root / "experiments" / "registry.csv", config.run_id)
    checks["run_registered"] = registered
    if require_registry and not registered:
        blockers.append(f"run_id is not pre-registered: {config.run_id}")

    checks["config_enabled"] = config.enabled
    if not config.enabled:
        blockers.append("evaluation config is disabled")

    return EvaluationReadinessReport(
        ready=not blockers,
        run_id=config.run_id,
        checks=checks,
        blockers=tuple(blockers),
        evidence=evidence,
    )


def execute_policy_evaluation(
    root: Path, config: PolicyEvaluationConfig, config_path: Path
) -> Path:
    report = validate_evaluation_readiness(root, config)
    if not report.ready:
        raise RuntimeError("evaluation readiness failed: " + "; ".join(report.blockers))

    root = root.resolve()
    output_dir = _within_root(root, config.output_dir, "output")
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = output_dir / "run_manifest.json"
    generations_path = output_dir / "generations.jsonl"
    scores_path = output_dir / "scores.jsonl"
    summary_path = output_dir / "summary.json"

    source_manifest = json.loads(
        _within_root(root, config.data.source_manifest_path, "source manifest").read_text(
            "utf-8"
        )
    )
    training_manifest = json.loads(
        _within_root(
            root, config.data.training_manifest_path, "training manifest"
        ).read_text("utf-8")
    )
    source_data = _within_root(
        root,
        source_manifest["files"][config.data.source_key]["path"],
        "source data",
    )
    prompt_data = _within_root(
        root,
        training_manifest["files"][config.data.prompt_key]["path"],
        "prompt data",
    )
    records = read_mail_records(source_data)
    examples = read_sft_examples(prompt_data)
    selected = select_stratified_examples(
        examples,
        records,
        seed=config.seed,
        max_examples=config.generation.max_examples,
    )

    _seed_everything(config.seed)
    model, tokenizer, torch = _load_model(root, config)
    start = time.monotonic()
    generations: list[GenerationRecord] = []
    with generations_path.open("x", encoding="utf-8", newline="\n") as handle:
        for example, record in selected:
            messages = [message.model_dump(mode="json") for message in example.prompt]
            input_ids = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=config.generation.enable_thinking,
                return_tensors="pt",
            ).to(config.generation.device)
            attention_mask = torch.ones_like(input_ids)
            with torch.inference_mode():
                output_ids = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=config.generation.max_new_tokens,
                    do_sample=config.generation.do_sample,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    use_cache=True,
                )
            completion_ids = output_ids[0, input_ids.shape[1] :]
            raw_output = tokenizer.decode(completion_ids, skip_special_tokens=True).strip()
            generation = GenerationRecord(
                run_id=config.run_id,
                model_variant=config.model.variant,
                example_id=example.example_id,
                task_id=example.task_id,
                source_fingerprint=example.source_fingerprint,
                diagnostic_group=record.diagnostic_group,
                target_mode=example.target_mode,
                raw_output=raw_output,
                prompt_tokens=int(input_ids.shape[1]),
                completion_tokens=int(completion_ids.shape[0]),
            )
            generations.append(generation)
            handle.write(canonical_json(generation) + "\n")
            handle.flush()

    summary, scores = score_generations(tuple(generations), records, purpose=config.purpose)
    with scores_path.open("x", encoding="utf-8", newline="\n") as handle:
        for score in scores:
            handle.write(canonical_json(score) + "\n")
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "run_id": config.run_id,
        "purpose": config.purpose,
        "status": "completed_pipeline_smoke",
        "git_commit": _git_commit(root),
        "config_path": str(config_path.resolve().relative_to(root)).replace("\\", "/"),
        "config_sha256": sha256_file(config_path),
        "model": config.model.model_dump(mode="json"),
        "generation": config.generation.model_dump(mode="json"),
        "selected_task_ids_sha256": _task_ids_sha256([item.task_id for item in generations]),
        "sample_count": len(generations),
        "elapsed_seconds": time.monotonic() - start,
        "artifacts": {
            "generations": {"path": "generations.jsonl", "sha256": sha256_file(generations_path)},
            "scores": {"path": "scores.jsonl", "sha256": sha256_file(scores_path)},
            "summary": {"path": "summary.json", "sha256": sha256_file(summary_path)},
        },
        "dependencies": _dependency_versions(),
        "frozen_test_accessed": False,
        "claim_boundary": "Engineering evaluation of 0.6B eight-step smoke adapters; not Gate B evidence.",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output_dir


def _load_model(root: Path, config: PolicyEvaluationConfig):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.model.model_id,
        revision=config.model.revision,
        trust_remote_code=config.model.trust_remote_code,
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        config.model.model_id,
        revision=config.model.revision,
        trust_remote_code=config.model.trust_remote_code,
        dtype=torch.bfloat16,
    )
    if config.model.adapter_path is not None:
        from peft import PeftModel

        adapter_path = _within_root(root, config.model.adapter_path, "adapter")
        model = PeftModel.from_pretrained(model, adapter_path, is_trainable=False)
    model.to(config.generation.device)
    model.eval()
    return model, tokenizer, torch


def _validate_manifest(
    root: Path,
    configured_path: str,
    expected_hash: str,
    prefix: str,
    checks: dict[str, bool],
    blockers: list[str],
    evidence: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    path = _within_root(root, configured_path, prefix)
    checks[f"{prefix}_exists"] = path.is_file()
    if not path.is_file():
        blockers.append(f"missing {prefix}: {configured_path}")
        return path, {}
    actual_hash = sha256_file(path)
    checks[f"{prefix}_hash_matches"] = actual_hash == expected_hash
    evidence[f"{prefix}_sha256"] = actual_hash
    if actual_hash != expected_hash:
        blockers.append(f"{prefix} SHA-256 mismatch")
    return path, json.loads(path.read_text("utf-8"))


def _validate_artifact(
    root: Path,
    manifest: dict[str, Any],
    key: str,
    prefix: str,
    checks: dict[str, bool],
    blockers: list[str],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    entry = manifest.get("files", {}).get(key)
    checks[f"{prefix}_artifact_declared"] = isinstance(entry, dict)
    if not isinstance(entry, dict):
        blockers.append(f"manifest does not declare artifact key: {key}")
        return {}
    path = _within_root(root, str(entry["path"]), f"{prefix} artifact")
    checks[f"{prefix}_artifact_exists"] = path.is_file()
    if not path.is_file():
        blockers.append(f"missing artifact: {entry['path']}")
        return entry
    actual_hash = sha256_file(path)
    checks[f"{prefix}_artifact_hash_matches"] = actual_hash == entry["sha256"]
    if actual_hash != entry["sha256"]:
        blockers.append(f"artifact SHA-256 mismatch: {entry['path']}")
    evidence[f"{prefix}_artifact"] = {
        "path": entry["path"],
        "records": entry["records"],
        "sha256": actual_hash,
    }
    return entry


def _within_root(root: Path, configured: str, label: str) -> Path:
    path = (root / configured).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} path escapes repository root: {configured}")
    return path


def _registry_has_run(path: Path, run_id: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8", newline="") as handle:
        return any(row.get("experiment_id") == run_id for row in csv.DictReader(handle))


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    import torch

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _task_ids_sha256(task_ids: list[str]) -> str:
    payload = "\n".join(task_ids).encode("utf-8") + b"\n"
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _dependency_versions() -> dict[str, str]:
    versions = {}
    for package in ("torch", "transformers", "peft", "pydantic"):
        versions[package] = importlib.metadata.version(package)
    return versions

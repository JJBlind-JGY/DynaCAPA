"""Re-score retained generations and build an auditable pilot comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from dynacapa.evaluation.policy_benchmark import (
    load_evaluation_config,
    read_generation_records,
    read_mail_records,
    score_generations,
    sha256_file,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--generations", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if len(args.config) != 3 or len(args.generations) != 3:
        raise ValueError("exactly three configs and generation files are required")

    root = Path(__file__).resolve().parents[1]
    output_path = _within_root(root, args.output, "comparison output")
    if output_path.exists():
        raise FileExistsError(f"comparison output already exists: {args.output}")

    variants = {}
    task_sets = []
    source_hashes = set()
    for configured, generated in zip(args.config, args.generations, strict=True):
        config_path = _within_root(root, configured, "config")
        generations_path = _within_root(root, generated, "generations")
        config = load_evaluation_config(config_path)
        generations = read_generation_records(generations_path)
        if {item.run_id for item in generations} != {config.run_id}:
            raise ValueError(f"run_id mismatch for {generations_path}")
        if {item.model_variant for item in generations} != {config.model.variant}:
            raise ValueError(f"model variant mismatch for {generations_path}")

        source_manifest_path = _within_root(
            root, config.data.source_manifest_path, "source manifest"
        )
        source_hash = sha256_file(source_manifest_path)
        if source_hash != config.data.source_manifest_sha256:
            raise ValueError(f"source manifest hash mismatch for {config_path}")
        source_hashes.add(source_hash)
        source_manifest = json.loads(source_manifest_path.read_text("utf-8"))
        source_entry = source_manifest["files"][config.data.source_key]
        source_path = _within_root(root, source_entry["path"], "source data")
        if sha256_file(source_path) != source_entry["sha256"]:
            raise ValueError(f"source data hash mismatch for {source_path}")
        records = read_mail_records(source_path)
        summary, _ = score_generations(generations, records, purpose=config.purpose)
        task_ids = tuple(item.task_id for item in generations)
        task_sets.append(task_ids)
        variants[config.model.variant] = {
            "run_id": config.run_id,
            "config_path": configured.replace("\\", "/"),
            "config_sha256": sha256_file(config_path),
            "generations_path": f"{config.output_dir}/generations.jsonl",
            "generations_sha256": sha256_file(generations_path),
            "summary": summary.model_dump(mode="json"),
        }

    if set(variants) != {"base", "sft", "dpo"}:
        raise ValueError("comparison requires exactly base, sft, and dpo")
    if len(source_hashes) != 1 or not all(item == task_sets[0] for item in task_sets[1:]):
        raise ValueError("variants do not use the same ordered validation sample")

    metrics = {
        variant: payload["summary"]["metrics"] for variant, payload in variants.items()
    }
    comparison = {
        "artifact_id": "policy_eval_qwen3_0_6b_mail_v0_2_pilot_comparison",
        "protocol_version": "policy-eval-v1",
        "status": "completed_engineering_pilot",
        "scorer_git_commit": _git_commit(root),
        "sample_count": len(task_sets[0]),
        "ordered_task_ids_sha256": hashlib.sha256(
            ("\n".join(task_sets[0]) + "\n").encode("utf-8")
        ).hexdigest(),
        "source_manifest_sha256": next(iter(source_hashes)),
        "same_ordered_sample": True,
        "frozen_test_accessed": False,
        "variants": variants,
        "numeric_metric_deltas": {
            "sft_minus_base": _numeric_deltas(metrics["sft"], metrics["base"]),
            "dpo_minus_sft": _numeric_deltas(metrics["dpo"], metrics["sft"]),
            "dpo_minus_base": _numeric_deltas(metrics["dpo"], metrics["base"]),
        },
        "claim_boundary": (
            "Sixty-case validation engineering pilot for 0.6B eight-step adapters; "
            "not population-weighted and not Gate B evidence."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(output_path), "sha256": sha256_file(output_path)}, indent=2))
    return 0


def _numeric_deltas(
    minuend: dict[str, float | None], subtrahend: dict[str, float | None]
) -> dict[str, float | None]:
    return {
        key: (
            None
            if minuend.get(key) is None or subtrahend.get(key) is None
            else float(minuend[key]) - float(subtrahend[key])
        )
        for key in sorted(set(minuend) & set(subtrahend))
    }


def _within_root(root: Path, configured: str, label: str) -> Path:
    path = (root / configured).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} path escapes repository root: {configured}")
    return path


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed validation before importing GPU training dependencies."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import Field

from dynacapa.core.schemas import StrictModel
from dynacapa.training.config import TrainingRunConfig


class ReadinessReport(StrictModel):
    ready: bool
    run_id: str
    checks: dict[str, bool]
    blockers: tuple[str, ...] = ()
    evidence: dict[str, Any] = Field(default_factory=dict)


def load_training_config(path: Path) -> TrainingRunConfig:
    import yaml

    return TrainingRunConfig.model_validate(yaml.safe_load(path.read_text("utf-8")))


def validate_training_readiness(
    root: Path,
    config: TrainingRunConfig,
    *,
    require_registry: bool = True,
    require_dependency_lock: bool = True,
) -> ReadinessReport:
    root = root.resolve()
    blockers: list[str] = []
    checks: dict[str, bool] = {}
    evidence: dict[str, Any] = {}

    manifest_path = _within_root(root, config.data.manifest_path, "manifest")
    manifest_exists = manifest_path.is_file()
    checks["manifest_exists"] = manifest_exists
    manifest: dict[str, Any] = {}
    if not manifest_exists:
        blockers.append(f"missing data manifest: {config.data.manifest_path}")
    else:
        actual_manifest_hash = _sha256_file(manifest_path)
        evidence["manifest_sha256"] = actual_manifest_hash
        checks["manifest_hash_matches"] = (
            actual_manifest_hash == config.data.manifest_sha256
        )
        if not checks["manifest_hash_matches"]:
            blockers.append("data manifest SHA-256 does not match the pinned value")
        manifest = json.loads(manifest_path.read_text("utf-8"))

    expected_keys = (config.data.train_key, config.data.validation_key)
    artifact_evidence: dict[str, Any] = {}
    for key in expected_keys:
        entry = manifest.get("files", {}).get(key)
        key_exists = isinstance(entry, dict)
        checks[f"artifact_{key}_declared"] = key_exists
        if not key_exists:
            blockers.append(f"manifest does not declare artifact key: {key}")
            continue
        artifact_path = _within_root(root, str(entry["path"]), key)
        exists = artifact_path.is_file()
        checks[f"artifact_{key}_exists"] = exists
        if not exists:
            blockers.append(f"missing generated artifact: {entry['path']}")
            continue
        actual_hash = _sha256_file(artifact_path)
        matches = actual_hash == entry["sha256"]
        checks[f"artifact_{key}_hash_matches"] = matches
        if not matches:
            blockers.append(f"artifact SHA-256 mismatch: {entry['path']}")
        artifact_evidence[key] = {
            "path": entry["path"],
            "records": entry["records"],
            "sha256": actual_hash,
        }
    evidence["artifacts"] = artifact_evidence

    frozen_accessed = bool(
        manifest.get("eligibility", {}).get("frozen_test_accessed", True)
    )
    checks["frozen_test_sealed"] = not frozen_accessed
    if frozen_accessed:
        blockers.append("training artifact is not certified as frozen-test sealed")

    eligible_key = (
        "data_pipeline_smoke" if config.purpose == "pipeline_smoke" else "formal_sft_or_dpo_claim"
    )
    eligible = bool(manifest.get("eligibility", {}).get(eligible_key, False))
    checks["artifact_eligible_for_purpose"] = eligible
    if not eligible:
        blockers.append(f"data manifest is not eligible for purpose={config.purpose}")

    output_path = _within_root(root, config.output_dir, "output")
    output_available = not output_path.exists()
    checks["output_dir_absent"] = output_available
    if not output_available:
        blockers.append(f"output directory already exists: {config.output_dir}")

    lock_path = _within_root(root, config.expected_dependency_lock, "dependency lock")
    lock_exists = lock_path.is_file()
    checks["dependency_lock_exists"] = lock_exists
    if require_dependency_lock and not lock_exists:
        blockers.append(
            f"server-specific dependency lock is missing: {config.expected_dependency_lock}"
        )

    registered = _registry_has_run(root / "experiments" / "registry.csv", config.run_id)
    checks["run_registered"] = registered
    if require_registry and not registered:
        blockers.append(f"run_id is not pre-registered: {config.run_id}")

    checks["config_enabled"] = config.enabled
    if not config.enabled:
        blockers.append("run config is disabled")

    if config.stage == "dpo" and config.model.initial_adapter_path is not None:
        adapter_path = _within_root(
            root, config.model.initial_adapter_path, "initial adapter"
        )
        adapter_exists = adapter_path.is_dir()
        checks["initial_adapter_exists"] = adapter_exists
        if not adapter_exists:
            blockers.append(
                f"preceding SFT adapter is missing: {config.model.initial_adapter_path}"
            )

    return ReadinessReport(
        ready=not blockers,
        run_id=config.run_id,
        checks=checks,
        blockers=tuple(blockers),
        evidence=evidence,
    )


def _within_root(root: Path, configured: str, label: str) -> Path:
    path = (root / configured).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} path escapes repository root: {configured}")
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _registry_has_run(path: Path, run_id: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8", newline="") as handle:
        return any(row.get("experiment_id") == run_id for row in csv.DictReader(handle))

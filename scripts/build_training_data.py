"""Build immutable, TRL-compatible SFT and DPO JSONL artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from dynacapa.data.training import (
    TrainingCompileConfig,
    canonical_jsonl,
    compile_training_examples,
    read_records,
    sha256_bytes,
)


def _within_root(root: Path, configured: str) -> Path:
    path = (root / configured).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"configured path escapes repository root: {configured}")
    return path


def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"refusing to overwrite changed artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/data/mail_training_v0_2.yaml")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config = TrainingCompileConfig.model_validate(
        yaml.safe_load(_within_root(root, args.config).read_text(encoding="utf-8"))
    )
    source_manifest_path = _within_root(root, config.dataset_manifest)
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    output_dir = _within_root(root, config.output_dir)

    files: dict[str, dict[str, Any]] = {}
    audits: dict[str, Any] = {}
    pending: list[tuple[Path, bytes]] = []
    for split in config.source_splits:
        source = _within_root(root, source_manifest["files"][split]["path"])
        source_bytes = source.read_bytes()
        actual_source_hash = sha256_bytes(source_bytes)
        expected_source_hash = source_manifest["files"][split]["sha256"]
        if actual_source_hash != expected_source_hash:
            raise ValueError(
                f"source hash mismatch for {split}: {actual_source_hash} != {expected_source_hash}"
            )
        records = read_records(source)
        compilation = compile_training_examples(records)
        audits[split] = compilation.audit
        for kind, models in (("sft", compilation.sft), ("dpo", compilation.dpo)):
            content = canonical_jsonl(models)
            path = output_dir / f"{split}.{kind}.jsonl"
            key = f"{split}_{kind}"
            files[key] = {
                "path": path.relative_to(root).as_posix(),
                "records": len(models),
                "bytes": len(content),
                "sha256": sha256_bytes(content),
            }
            pending.append((path, content))

    manifest = {
        "artifact_id": "dynacapa_mail_training_v0_2_minimal_v1",
        "artifact_status": config.artifact_status,
        "target_policy": config.target_policy,
        "source_dataset": {
            "dataset_id": source_manifest["dataset_id"],
            "dataset_version": source_manifest["dataset_version"],
            "manifest_path": source_manifest_path.relative_to(root).as_posix(),
            "manifest_sha256": sha256_bytes(source_manifest_path.read_bytes()),
            "splits": list(config.source_splits),
        },
        "files": files,
        "audits": audits,
        "eligibility": {
            "data_pipeline_smoke": True,
            "formal_sft_or_dpo_claim": False,
            "frozen_test_accessed": False,
            "reason": (
                "Minimum-intervention targets cover execute/ask/block only; "
                "sandbox/rewrite/stop need distinct semantic triggers in a later dataset version."
            ),
        },
    }
    manifest_path = _within_root(root, config.manifest_path)
    manifest_content = _json_bytes(manifest)
    pending.append((manifest_path, manifest_content))

    if not args.check_only:
        for path, content in pending:
            _write_immutable(path, content)

    print(
        json.dumps(
            {
                "artifact_id": manifest["artifact_id"],
                "status": manifest["artifact_status"],
                "files": files,
                "audits": audits,
                "written": not args.check_only,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

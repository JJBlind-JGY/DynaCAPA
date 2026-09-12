"""Build a deterministic dataset and fail closed on version-content drift."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from dynacapa.data.generators.mail_v0 import (
    MailDatasetConfig,
    build_template_catalog,
    generate_mail_dataset,
)
from dynacapa.data.task_schema import MailTaskRecord
from dynacapa.data.validation.leakage import LeakageAuditReport, audit_splits


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _jsonl_bytes(records: tuple[MailTaskRecord, ...]) -> bytes:
    return (
        "\n".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            for record in records
        )
        + "\n"
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_immutable(path: Path, content: bytes) -> str:
    digest = _sha256(content)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(
                f"refusing to overwrite changed dataset artifact {path}; bump dataset_version"
            )
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return digest


def _within_root(root: Path, configured: str) -> Path:
    path = (root / configured).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"dataset path escapes repository root: {configured}")
    return path


def build_artifacts(
    root: Path,
    config: MailDatasetConfig,
    splits: dict[str, tuple[MailTaskRecord, ...]],
    audit: LeakageAuditReport,
    write: bool,
) -> dict[str, Any]:
    output_dir = _within_root(root, config.output_dir)
    manifest_dir = _within_root(root, config.manifest_dir)
    files: dict[str, dict[str, Any]] = {}
    pending: list[tuple[Path, bytes]] = []
    for split_name, records in splits.items():
        path = output_dir / f"{split_name}.jsonl"
        content = _jsonl_bytes(records)
        files[split_name] = {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(content),
            "records": len(records),
            "bytes": len(content),
        }
        pending.append((path, content))

    catalog_content = _json_bytes(
        [template.model_dump(mode="json") for template in build_template_catalog()]
    )
    catalog_path = manifest_dir / f"{config.dataset_id}.template_catalog.json"
    pending.append((catalog_path, catalog_content))

    canonical_cases = []
    validation = splits["validation"]
    for group in (
        "iid",
        "unseen_authorization",
        "unseen_attack",
        "unseen_source",
        "unseen_schema",
        "long_horizon",
    ):
        records = [record for record in validation if record.diagnostic_group == group][:5]
        for record in records:
            canonical_cases.append(
                {
                    "task_id": record.task_id,
                    "diagnostic_group": group,
                    "record_fingerprint": record.provenance.record_fingerprint,
                    "acceptable_modes": sorted(
                        mode.value for mode in record.ground_truth.acceptable_modes
                    ),
                    "illegal_reason_codes": sorted(
                        {
                            action.reason_code.value
                            for action in record.ground_truth.illegal_actions
                            if action.reason_code is not None
                        }
                    ),
                }
            )
    canonical_path = manifest_dir / f"{config.dataset_id}.canonical_cases.json"
    pending.append((canonical_path, _json_bytes(canonical_cases)))

    dictionary = {
        "dataset_id": config.dataset_id,
        "dataset_version": config.dataset_version,
        "record_schema": "dynacapa.data.task_schema.MailTaskRecord",
        "format": "UTF-8 JSON Lines; one independently valid record per line",
        "missing_value_policy": "Fields are explicit; absent optional values serialize as null.",
        "fields": {
            "task_id": "Unique generated instance identifier; not a semantic feature.",
            "split": "train, validation, or frozen_test.",
            "diagnostic_group": "IID, one-factor validation holdout, or composite OOD.",
            "natural_language_request": "Authenticated user's requested Mail operation.",
            "context_messages": "Content plus explicit provenance; content never grants rights.",
            "ground_truth": "Rights, facts, legal/illegal actions, effects, modes, confirmations.",
            "scenario": "Attack, authorization, schema, source, and horizon factors.",
            "provenance": "Dataset/generator versions, template ID, seed, semantic hash.",
        },
        "controlled_vocabularies": {
            "policy_mode": ["execute", "ask", "sandbox", "rewrite", "block", "stop"],
            "split": ["train", "validation", "frozen_test"],
        },
    }
    dictionary_path = manifest_dir / f"{config.dataset_id}.data_dictionary.json"
    pending.append((dictionary_path, _json_bytes(dictionary)))

    split_policy = {
        "train": "40 train-role templates; v1 schema; train authorization, source, and attack-expression vocabularies; horizon 2-4.",
        "validation": {
            "iid": "All controlled factor values occur in training, but semantic fingerprints do not.",
            "unseen_authorization": "Authorization pattern is held out; other axes remain train-like.",
            "unseen_attack": "Attack wording is held out; attack types remain shared.",
            "unseen_source": "Issuer/fact-source combination is held out.",
            "unseen_schema": "Tool schema v2 is held out from v1 training.",
            "long_horizon": "Horizon 8 is longer than the training maximum of 4.",
        },
        "frozen_test": "20 disjoint templates plus disjoint authorization patterns, attack expressions, source combinations, and v3 tool schema; horizon 8 or 10.",
        "freeze_rule": "Changing any frozen record requires a dataset version bump and a new manifest; in-place overwrite is rejected.",
    }
    split_policy_path = manifest_dir / f"{config.dataset_id}.split_policy.json"
    pending.append((split_policy_path, _json_bytes(split_policy)))

    manifest = {
        "dataset_id": config.dataset_id,
        "dataset_version": config.dataset_version,
        "generator_version": config.generator_version,
        "generator_seed": config.seed,
        "logical_generation_time": config.evaluation_time.isoformat(),
        "publication_status": "internal_pre_release",
        "access_route": "private research repository during benchmark construction",
        "persistent_identifier": None,
        "license": None,
        "files": files,
        "metadata_files": {
            "template_catalog": catalog_path.relative_to(root).as_posix(),
            "canonical_cases": canonical_path.relative_to(root).as_posix(),
            "data_dictionary": dictionary_path.relative_to(root).as_posix(),
            "split_policy": split_policy_path.relative_to(root).as_posix(),
        },
        "leakage_audit": audit.model_dump(mode="json"),
        "unresolved_publication_metadata": [
            "public repository",
            "persistent identifier",
            "dataset creators",
            "publisher/repository",
            "publication year",
            "license",
            "related paper identifier",
        ],
    }
    manifest_path = manifest_dir / f"{config.dataset_id}.manifest.json"
    pending.append((manifest_path, _json_bytes(manifest)))

    if write:
        for path, content in pending:
            _write_immutable(path, content)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/data/mail_v0.yaml")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = _within_root(root, args.config)
    config = MailDatasetConfig.model_validate(
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    )
    splits = generate_mail_dataset(config)
    audit = audit_splits(splits)
    manifest = build_artifacts(root, config, splits, audit, write=not args.check_only)
    report = {
        "dataset_id": config.dataset_id,
        "dataset_version": config.dataset_version,
        "counts": {name: len(records) for name, records in splits.items()},
        "leakage_audit_passed": audit.passed,
        "errors": audit.errors,
        "files": manifest["files"],
        "written": not args.check_only,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


"""Build the blinded v0.3 six-mode semantic pilot; never reads frozen test."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from dynacapa.data.six_mode_pilot import (
    build_six_mode_review_pilot,
    canonical_jsonl,
)
from dynacapa.data.training import read_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-records", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--count-per-mode", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    outputs = {
        "review_items": args.output_dir / "review_items.jsonl",
        "answer_key": args.output_dir / "answer_key.jsonl",
        "audit": args.output_dir / "audit.json",
        "manifest": args.manifest,
    }
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite existing artifacts: {existing}")

    records = read_records(args.train_records)
    pilot = build_six_mode_review_pilot(
        records, count_per_mode=args.count_per_mode, seed=args.seed
    )
    review_bytes = canonical_jsonl(pilot.review_items)
    answer_bytes = canonical_jsonl(pilot.answers)
    audit_bytes = (
        json.dumps(pilot.audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    outputs["review_items"].write_bytes(review_bytes)
    outputs["answer_key"].write_bytes(answer_bytes)
    outputs["audit"].write_bytes(audit_bytes)
    manifest = {
        "artifact_id": "dynacapa_mail_v0_3_six_mode_semantic_pilot",
        "status": "semantic_review_only",
        "source": {
            "path": args.train_records.as_posix(),
            "sha256": _sha256(args.train_records.read_bytes()),
            "split": "train",
        },
        "count_per_mode": args.count_per_mode,
        "seed": args.seed,
        "artifacts": {
            "review_items": _entry(outputs["review_items"], review_bytes, len(pilot.review_items)),
            "answer_key": _entry(outputs["answer_key"], answer_bytes, len(pilot.answers)),
            "audit": _entry(outputs["audit"], audit_bytes, 1),
        },
        "validation_accessed": False,
        "frozen_test_accessed": False,
        "training_eligible": False,
        "claim_boundary": "Blinded semantic review pilot; not a released dataset or model experiment.",
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    args.manifest.write_bytes(manifest_bytes)
    print(json.dumps({"manifest": str(args.manifest), "audit": pilot.audit}, indent=2))


def _entry(path: Path, content: bytes, records: int) -> dict[str, object]:
    return {"path": path.as_posix(), "records": records, "sha256": _sha256(content)}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


if __name__ == "__main__":
    main()

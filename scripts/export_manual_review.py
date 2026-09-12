"""Export blinded review material and a separately stored adjudication key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.data.review import (
    ManualReviewConfig,
    attach_file_hashes,
    build_review_pack,
    key_jsonl_bytes,
    review_csv_bytes,
)


def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"refusing to overwrite review artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-config", default="configs/data/mail_v0_2.yaml")
    parser.add_argument("--review-config", default="configs/data/manual_review_v0_2.yaml")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dataset_config = MailDatasetConfig.model_validate(
        yaml.safe_load((root / args.dataset_config).read_text(encoding="utf-8"))
    )
    review_config = ManualReviewConfig.model_validate(
        yaml.safe_load((root / args.review_config).read_text(encoding="utf-8"))
    )
    records = generate_mail_dataset(dataset_config)[review_config.split]
    rows, key, manifest = build_review_pack(records, review_config)
    review_bytes = review_csv_bytes(rows)
    key_bytes = key_jsonl_bytes(key)
    manifest = attach_file_hashes(manifest, review_bytes, key_bytes)
    output_dir = (root / review_config.output_dir).resolve()
    if not output_dir.is_relative_to(root):
        parser.error("review output_dir must stay inside the repository")
    review_path = output_dir / "blinded_review.csv"
    key_path = output_dir / "adjudication_key.jsonl"
    manifest_path = root / "data/manifests/dynacapa_mail_v0_2.manual_review.json"
    manifest["files"]["blinded_review_csv"]["path"] = review_path.relative_to(root).as_posix()
    manifest["files"]["adjudication_key_jsonl"]["path"] = key_path.relative_to(root).as_posix()
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_immutable(review_path, review_bytes)
    _write_immutable(key_path, key_bytes)
    _write_immutable(manifest_path, manifest_bytes)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""Evaluate deterministic verifier baselines without touching frozen data by default."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.evaluation.verifier_benchmark import evaluate_verifier_benchmarks


def _write_immutable(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise FileExistsError(f"refusing to overwrite benchmark result: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/data/mail_v0_2.yaml")
    parser.add_argument("--split", choices=("train", "validation", "frozen_test"), default="validation")
    parser.add_argument("--unlock-frozen", action="store_true")
    parser.add_argument(
        "--include-neighboring-proxies",
        action="store_true",
        help=(
            "include transparent structured proxies for AuthGraph and ARGUS; "
            "these are not full reproductions of the original systems"
        ),
    )
    parser.add_argument(
        "--output", default="experiments/phase1/verifier_validation_v0_2_ci.json"
    )
    args = parser.parse_args()
    if args.split == "frozen_test" and not args.unlock_frozen:
        parser.error("frozen_test is sealed; pass --unlock-frozen only for a declared final run")

    root = Path(__file__).resolve().parents[1]
    config_path = (root / args.config).resolve()
    output_path = (root / args.output).resolve()
    if not config_path.is_relative_to(root) or not output_path.is_relative_to(root):
        parser.error("config and output paths must stay inside the repository")
    config = MailDatasetConfig.model_validate(
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    )
    records = generate_mail_dataset(config)[args.split]
    report = evaluate_verifier_benchmarks(
        records,
        include_neighboring_proxies=args.include_neighboring_proxies,
    )
    content = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_immutable(output_path, content)
    print(content, end="")
    return 0 if not report.full_verifier_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

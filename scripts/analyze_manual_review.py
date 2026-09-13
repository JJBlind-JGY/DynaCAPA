"""Analyze a completed blinded review only after labels are explicitly frozen."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from dynacapa.evaluation.manual_review import analyze_manual_review


def _write_immutable(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise FileExistsError(f"refusing to overwrite review analysis: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--review-csv",
        default="data/review/mail_v0_2_validation/blinded_review.csv",
    )
    parser.add_argument(
        "--adjudication-key",
        default="data/review/mail_v0_2_validation/adjudication_key.jsonl",
    )
    parser.add_argument(
        "--output",
        default="experiments/phase1/mail_v0_2_manual_review_analysis.json",
    )
    parser.add_argument(
        "--confirm-labels-frozen",
        action="store_true",
        help="required acknowledgement before the blinded adjudication key is read",
    )
    args = parser.parse_args()
    if not args.confirm_labels_frozen:
        parser.error(
            "refusing to open the adjudication key before labels are frozen; "
            "complete both reviews, then pass --confirm-labels-frozen"
        )

    root = Path(__file__).resolve().parents[1]
    paths = {
        name: (root / value).resolve()
        for name, value in {
            "review": args.review_csv,
            "key": args.adjudication_key,
            "output": args.output,
        }.items()
    }
    if any(not path.is_relative_to(root) for path in paths.values()):
        parser.error("all paths must stay inside the repository")

    with paths["review"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    key = [
        json.loads(line)
        for line in paths["key"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = analyze_manual_review(rows, key)
    content = (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    _write_immutable(paths["output"], content)
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Create a non-overwriting diagnostic summary from retained policy outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dynacapa.evaluation.failure_analysis import analyze_policy_failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--generation-token-cap", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.generation_token_cap <= 0:
        raise SystemExit("--generation-token-cap must be positive")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing artifact: {args.output}")

    result = analyze_policy_failures(
        args.generations,
        args.scores,
        generation_token_cap=args.generation_token_cap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "counts": result["counts"]}, indent=2))


if __name__ == "__main__":
    main()

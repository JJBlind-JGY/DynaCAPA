"""Single guarded entry point for SFT and DPO training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dynacapa.training.readiness import load_training_config, validate_training_readiness
from dynacapa.training.trl_runner import execute_training


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually launch training; omission performs a read-only readiness check.",
    )
    parser.add_argument(
        "--local-structural-check",
        action="store_true",
        help="Do not require the server lock or experiment pre-registration.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = (root / args.config).resolve()
    if not config_path.is_relative_to(root):
        raise ValueError("config path escapes repository root")
    config = load_training_config(config_path)
    if args.execute:
        output_dir = execute_training(root, config, config_path)
        print(json.dumps({"run_id": config.run_id, "output_dir": str(output_dir)}, indent=2))
        return 0

    report = validate_training_readiness(
        root,
        config,
        require_registry=not args.local_structural_check,
        require_dependency_lock=not args.local_structural_check,
    )
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit chat-template sequence lengths without truncating training examples."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

from dynacapa.training.readiness import load_training_config


def percentile(values: list[int], probability: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sample."""
    if not values:
        raise ValueError("cannot summarize an empty sample")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_lengths(values: list[int], limit: int) -> dict[str, int | float]:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    return {
        "count": len(values),
        "min": min(values),
        "median": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "over_limit": sum(value > limit for value in values),
        "at_limit": sum(value == limit for value in values),
    }


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _chat_length(tokenizer: Any, messages: list[dict[str, str]]) -> int:
    token_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
    )
    return len(token_ids)


def audit_split(
    tokenizer: Any,
    path: Path,
    *,
    stage: str,
    limit: int,
    offender_limit: int = 20,
) -> dict[str, Any]:
    lengths: list[int] = []
    offenders: list[dict[str, Any]] = []
    for record in _read_jsonl(path):
        branches = (
            (("completion", record["completion"]),)
            if stage == "sft"
            else (("chosen", record["chosen"]), ("rejected", record["rejected"]))
        )
        for branch, completion in branches:
            length = _chat_length(tokenizer, record["prompt"] + completion)
            lengths.append(length)
            if length > limit:
                offenders.append(
                    {
                        "example_id": record["example_id"],
                        "task_id": record["task_id"],
                        "branch": branch,
                        "tokens": length,
                    }
                )
    offenders.sort(key=lambda item: item["tokens"], reverse=True)
    return {
        "summary": summarize_lengths(lengths, limit),
        "largest_over_limit": offenders[:offender_limit],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = (root / args.config).resolve()
    if not config_path.is_relative_to(root):
        raise ValueError("config path escapes repository root")
    config = load_training_config(config_path)

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.model.model_id,
        revision=config.model.revision,
        trust_remote_code=config.model.trust_remote_code,
    )
    manifest_path = (root / config.data.manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_keys = (config.data.train_key, config.data.validation_key)
    result: dict[str, Any] = {
        "run_id": config.run_id,
        "stage": config.stage,
        "model_id": config.model.model_id,
        "model_revision": config.model.revision,
        "tokenizer_class": tokenizer.__class__.__name__,
        "max_length": config.trainer.max_length,
        "truncation_permitted": False,
        "splits": {},
    }
    for key in split_keys:
        data_path = (root / manifest["files"][key]["path"]).resolve()
        if not data_path.is_relative_to(root):
            raise ValueError(f"data path escapes repository root: {data_path}")
        result["splits"][key] = audit_split(
            tokenizer,
            data_path,
            stage=config.stage,
            limit=config.trainer.max_length,
        )
    result["passed"] = all(
        split["summary"]["over_limit"] == 0 for split in result["splits"].values()
    )

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output_path = (root / args.output).resolve()
        if not output_path.is_relative_to(root):
            raise ValueError("output path escapes repository root")
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite token audit: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

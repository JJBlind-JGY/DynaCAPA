"""Post-hoc protocol diagnostics that never alter primary policy metrics."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


_MODE_PATTERN = re.compile(r'"mode"\s*:\s*"([^"]+)"')


def analyze_policy_failures(
    generations_path: Path,
    scores_path: Path,
    *,
    generation_token_cap: int,
) -> dict[str, Any]:
    """Join retained generations and scores and summarize protocol failures.

    The regex fallback is diagnostic only. It never upgrades malformed output to
    a valid prediction and therefore cannot change any registered metric.
    """

    generations = _read_jsonl(generations_path)
    scores = _read_jsonl(scores_path)
    generation_by_task = _index_unique(generations, "generations")
    score_by_task = _index_unique(scores, "scores")
    if set(generation_by_task) != set(score_by_task):
        missing_generation = sorted(set(score_by_task) - set(generation_by_task))
        missing_score = sorted(set(generation_by_task) - set(score_by_task))
        raise ValueError(
            "generation/score task mismatch: "
            f"missing_generation={missing_generation}, missing_score={missing_score}"
        )

    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    invalid_target = Counter[str]()
    invalid_intended = Counter[str]()
    extraction_method = Counter[str]()
    missing_fields = Counter[str]()
    invalid_json = 0
    cap_hits = 0
    invalid_cap_hits = 0

    for task_id in sorted(score_by_task):
        score = score_by_task[task_id]
        generation = generation_by_task[task_id]
        target = str(score["target_mode"])
        predicted = str(score["predicted_mode"])
        confusion[target][predicted] += 1
        cap_hit = int(generation["completion_tokens"]) >= generation_token_cap
        cap_hits += int(cap_hit)
        if bool(score["schema_valid"]):
            continue

        invalid_target[target] += 1
        invalid_json += int(not bool(score["json_valid"]))
        invalid_cap_hits += int(cap_hit)
        for field in score.get("missing_fields", []):
            missing_fields[str(field)] += 1
        intended_mode, method = _extract_intended_mode(str(generation["raw_output"]))
        invalid_intended[intended_mode] += 1
        extraction_method[method] += 1

    return {
        "analysis_type": "post_hoc_protocol_diagnostic",
        "primary_metrics_modified": False,
        "inputs": {
            "generations_path": generations_path.as_posix(),
            "generations_sha256": _sha256(generations_path),
            "scores_path": scores_path.as_posix(),
            "scores_sha256": _sha256(scores_path),
            "generation_token_cap": generation_token_cap,
        },
        "counts": {
            "samples": len(scores),
            "schema_invalid": sum(invalid_target.values()),
            "invalid_json": invalid_json,
            "completion_cap_hits": cap_hits,
            "invalid_completion_cap_hits": invalid_cap_hits,
        },
        "confusion_matrix": {
            target: dict(sorted(predictions.items()))
            for target, predictions in sorted(confusion.items())
        },
        "invalid_target_mode": dict(sorted(invalid_target.items())),
        "invalid_intended_mode": dict(sorted(invalid_intended.items())),
        "invalid_intent_extraction": dict(sorted(extraction_method.items())),
        "missing_field_frequency": dict(
            sorted(missing_fields.items(), key=lambda item: (-item[1], item[0]))
        ),
        "claim_boundary": (
            "Regex-derived intent is descriptive failure analysis only; malformed "
            "outputs remain invalid in every primary metric."
        ),
    }


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict) or not isinstance(row.get("task_id"), str):
                raise ValueError(f"missing task_id at {path}:{line_number}")
            rows.append(row)
    return tuple(rows)


def _index_unique(
    rows: tuple[dict[str, Any], ...], source: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = str(row["task_id"])
        if task_id in indexed:
            raise ValueError(f"duplicate task_id in {source}: {task_id}")
        indexed[task_id] = row
    return indexed


def _extract_intended_mode(raw_output: str) -> tuple[str, str]:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("mode"), str):
        return str(parsed["mode"]), "exact_json"
    match = _MODE_PATTERN.search(raw_output)
    if match:
        return match.group(1), "regex_fallback"
    return "__unknown__", "unavailable"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

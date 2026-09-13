from __future__ import annotations

from pathlib import Path

import pytest

from dynacapa.evaluation.failure_analysis import analyze_policy_failures


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "policy_failure_analysis"


def test_failure_analysis_keeps_malformed_intent_diagnostic_only() -> None:
    result = analyze_policy_failures(
        FIXTURES / "generations.jsonl",
        FIXTURES / "scores.jsonl",
        generation_token_cap=32,
    )

    assert result["primary_metrics_modified"] is False
    assert result["counts"] == {
        "samples": 3,
        "schema_invalid": 2,
        "invalid_json": 1,
        "completion_cap_hits": 1,
        "invalid_completion_cap_hits": 1,
    }
    assert result["invalid_intended_mode"] == {"block": 1, "execute": 1}
    assert result["invalid_intent_extraction"] == {
        "exact_json": 1,
        "regex_fallback": 1,
    }
    assert result["missing_field_frequency"] == {
        "$": 1,
        "args": 1,
        "proof.object_scope": 1,
    }


def test_failure_analysis_rejects_misaligned_tasks() -> None:
    with pytest.raises(ValueError, match="task mismatch"):
        analyze_policy_failures(
            FIXTURES / "generations.jsonl",
            FIXTURES / "scores_misaligned.jsonl",
            generation_token_cap=32,
        )

from __future__ import annotations

import pytest

from scripts.audit_token_lengths import percentile, summarize_lengths


def test_percentile_interpolates_deterministically() -> None:
    values = [40, 10, 30, 20]
    assert percentile(values, 0.0) == 10
    assert percentile(values, 0.5) == 25
    assert percentile(values, 1.0) == 40


def test_summarize_lengths_counts_boundary_separately() -> None:
    summary = summarize_lengths([8, 16, 17], limit=16)
    assert summary["count"] == 3
    assert summary["at_limit"] == 1
    assert summary["over_limit"] == 1


def test_empty_length_sample_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        summarize_lengths([], limit=16)

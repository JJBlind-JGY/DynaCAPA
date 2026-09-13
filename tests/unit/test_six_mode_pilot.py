from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import pytest

from dynacapa.core.enums import PolicyMode
from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.data.mode_semantics import resolve_mode
from dynacapa.data.six_mode_pilot import build_six_mode_review_pilot


@pytest.fixture(scope="module")
def generated_dataset():
    return generate_mail_dataset(
        MailDatasetConfig(
            dataset_id="dynacapa_mail_six_mode_pilot_test",
            dataset_version="0.2.0-test",
            seed=20260912,
            train_count=4800,
            validation_count=600,
            frozen_test_count=1200,
            evaluation_time=datetime(2026, 9, 12, tzinfo=timezone.utc),
            output_dir="data/processed/test",
            manifest_dir="data/manifests",
        )
    )


def test_six_mode_pilot_is_balanced_blinded_and_source_disjoint(
    generated_dataset,
) -> None:
    pilot = build_six_mode_review_pilot(
        generated_dataset["train"], count_per_mode=3, seed=17
    )
    answer_by_id = {answer.pilot_id: answer for answer in pilot.answers}
    assert len(pilot.review_items) == len(pilot.answers) == 18
    assert len({item.source_task_id for item in pilot.review_items}) == 18
    assert Counter(answer.target_mode for answer in pilot.answers) == {
        mode: 3 for mode in PolicyMode
    }
    for item in pilot.review_items:
        dumped = item.model_dump(mode="json")
        assert "target_mode" not in dumped
        answer = answer_by_id[item.pilot_id]
        assert resolve_mode(answer.evidence).mode == answer.target_mode
    assert pilot.audit["validation_accessed"] is False
    assert pilot.audit["frozen_test_accessed"] is False


def test_six_mode_pilot_rejects_non_train_sources(generated_dataset) -> None:
    with pytest.raises(ValueError, match="train records only"):
        build_six_mode_review_pilot(
            generated_dataset["validation"], count_per_mode=1
        )


def test_action_modes_keep_a_grounded_expected_action(generated_dataset) -> None:
    pilot = build_six_mode_review_pilot(
        generated_dataset["train"], count_per_mode=1, seed=29
    )
    by_mode = {answer.target_mode: answer for answer in pilot.answers}
    for mode in (PolicyMode.EXECUTE, PolicyMode.SANDBOX, PolicyMode.REWRITE):
        assert by_mode[mode].expected_tool in {"create_draft", "send_email"}
        assert "recipient" in by_mode[mode].expected_args
    for mode in (PolicyMode.ASK, PolicyMode.BLOCK, PolicyMode.STOP):
        assert by_mode[mode].expected_tool is None

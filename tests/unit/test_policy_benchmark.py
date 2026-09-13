from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.data.training import compile_training_examples
from dynacapa.evaluation.policy_benchmark import (
    GenerationRecord,
    score_generations,
    select_stratified_examples,
)


ROOT = Path(__file__).resolve().parents[2]


def _validation_records():
    raw = yaml.safe_load((ROOT / "configs/data/mail_v0_2.yaml").read_text("utf-8"))
    config = MailDatasetConfig.model_validate(
        {**raw, "train_count": 120, "validation_count": 60, "frozen_test_count": 12}
    )
    return generate_mail_dataset(config)["validation"]


def _generations(records, *, outputs=None):
    compilation = compile_training_examples(records)
    selected_outputs = outputs or {
        example.task_id: example.completion[0].content for example in compilation.sft
    }
    return tuple(
        GenerationRecord(
            run_id="unit_policy_eval",
            model_variant="base",
            example_id=example.example_id,
            task_id=example.task_id,
            source_fingerprint=example.source_fingerprint,
            diagnostic_group=next(
                record.diagnostic_group for record in records if record.task_id == example.task_id
            ),
            target_mode=example.target_mode,
            raw_output=selected_outputs[example.task_id],
            prompt_tokens=100,
            completion_tokens=50,
        )
        for example in compilation.sft
    )


def test_oracle_targets_score_as_valid_safe_outputs() -> None:
    records = _validation_records()
    summary, scores = score_generations(_generations(records), records)

    assert summary.sample_count == 60
    assert summary.frozen_test_accessed is False
    assert summary.metrics["json_valid_rate"] == 1.0
    assert summary.metrics["schema_valid_rate"] == 1.0
    assert summary.metrics["field_complete_rate"] == 1.0
    assert summary.metrics["mode_macro_f1"] == 1.0
    assert summary.metrics["upr"] == 0.0
    assert summary.metrics["format_or_safety_failure_rate"] == 0.0
    assert summary.metrics["fbr"] == 0.0
    assert summary.metrics["shield_rate"] == 0.0
    assert all(not score.missing_fields for score in scores)


def test_malformed_output_is_not_hidden_by_upr() -> None:
    records = _validation_records()
    compilation = compile_training_examples(records)
    outputs = {
        example.task_id: example.completion[0].content for example in compilation.sft
    }
    victim = compilation.sft[0].task_id
    outputs[victim] = "not JSON"

    summary, scores = score_generations(_generations(records, outputs=outputs), records)
    victim_score = next(score for score in scores if score.task_id == victim)

    assert victim_score.json_valid is False
    assert victim_score.schema_valid is False
    assert victim_score.format_or_safety_failure is True
    assert victim_score.shield_intervened is True
    assert summary.metrics["upr"] == 0.0
    assert summary.metrics["format_or_safety_failure_rate"] == 1 / 60
    assert summary.metrics["shield_rate"] == 1 / 60


def test_missing_explicit_default_is_field_incomplete_but_schema_valid() -> None:
    records = _validation_records()
    compilation = compile_training_examples(records)
    outputs = {
        example.task_id: example.completion[0].content for example in compilation.sft
    }
    victim = compilation.sft[0]
    import json

    value = json.loads(outputs[victim.task_id])
    value.pop("termination")
    outputs[victim.task_id] = json.dumps(value)

    summary, scores = score_generations(_generations(records, outputs=outputs), records)
    victim_score = next(score for score in scores if score.task_id == victim.task_id)

    assert victim_score.schema_valid is True
    assert victim_score.field_complete is False
    assert victim_score.missing_fields == ("termination",)
    assert summary.metrics["field_complete_rate"] == 59 / 60


def test_stratified_selection_is_deterministic_and_group_balanced() -> None:
    records = _validation_records()
    examples = compile_training_examples(records).sft

    first = select_stratified_examples(examples, records, seed=17, max_examples=18)
    second = select_stratified_examples(tuple(reversed(examples)), records, seed=17, max_examples=18)

    assert [item[0].task_id for item in first] == [item[0].task_id for item in second]
    group_counts = Counter(item[1].diagnostic_group for item in first)
    mode_counts = Counter(item[0].target_mode.value for item in first)
    assert set(group_counts) == {
        "iid",
        "long_horizon",
        "unseen_attack",
        "unseen_authorization",
        "unseen_schema",
        "unseen_source",
    }
    assert max(group_counts.values()) - min(group_counts.values()) <= 1
    assert set(mode_counts) == {"ask", "block", "execute"}


def test_scorer_rejects_tampered_target_label() -> None:
    records = _validation_records()
    generations = list(_generations(records))
    generations[0] = generations[0].model_copy(update={"target_mode": "stop"})

    with pytest.raises(ValueError, match="target mode mismatch"):
        score_generations(tuple(generations), records)

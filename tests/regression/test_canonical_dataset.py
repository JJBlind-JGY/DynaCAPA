from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.regression
def test_mail_v0_2_canonical_cases_are_frozen() -> None:
    config = MailDatasetConfig.model_validate(
        yaml.safe_load(
            (ROOT / "configs/data/mail_v0_2.yaml").read_text(encoding="utf-8")
        )
    )
    splits = generate_mail_dataset(config)
    by_task_id = {
        record.task_id: record for records in splits.values() for record in records
    }
    cases = json.loads(
        (ROOT / "data/manifests/dynacapa_mail_v0_2.canonical_cases.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(cases) == 30
    for case in cases:
        record = by_task_id[case["task_id"]]
        assert record.provenance.record_fingerprint == case["record_fingerprint"]
        assert sorted(mode.value for mode in record.ground_truth.acceptable_modes) == case[
            "acceptable_modes"
        ]
        assert sorted(
            {
                action.reason_code.value
                for action in record.ground_truth.illegal_actions
                if action.reason_code is not None
            }
        ) == case["illegal_reason_codes"]


def test_old_generator_config_cannot_silently_use_new_code() -> None:
    raw = yaml.safe_load(
        (ROOT / "configs/data/mail_v0.yaml").read_text(encoding="utf-8")
    )
    with pytest.raises(ValidationError, match="generator_version"):
        MailDatasetConfig.model_validate(raw)


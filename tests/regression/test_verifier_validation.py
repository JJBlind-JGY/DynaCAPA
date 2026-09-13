from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.evaluation.verifier_benchmark import evaluate_verifier_benchmarks

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.regression
def test_validation_verifier_report_is_reproducible() -> None:
    config = MailDatasetConfig.model_validate(
        yaml.safe_load(
            (ROOT / "configs/data/mail_v0_2.yaml").read_text(encoding="utf-8")
        )
    )
    validation = generate_mail_dataset(config)["validation"]
    actual = evaluate_verifier_benchmarks(validation).model_dump(mode="json")
    expected = json.loads(
        (ROOT / "experiments/phase1/verifier_validation_v0_2_ci.json").read_text(
            encoding="utf-8"
        )
    )
    assert actual == expected


@pytest.mark.regression
def test_neighboring_proxy_probe_report_is_reproducible() -> None:
    config = MailDatasetConfig.model_validate(
        yaml.safe_load(
            (ROOT / "configs/data/mail_v0_2.yaml").read_text(encoding="utf-8")
        )
    )
    validation = generate_mail_dataset(config)["validation"]
    actual = evaluate_verifier_benchmarks(
        validation,
        include_neighboring_proxies=True,
    ).model_dump(mode="json")
    expected = json.loads(
        (
            ROOT
            / "experiments/phase1/verifier_validation_v0_2_neighbors_probes.json"
        ).read_text(encoding="utf-8")
    )
    assert actual == expected

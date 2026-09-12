from __future__ import annotations

from datetime import datetime, timezone

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.evaluation.verifier_benchmark import evaluate_verifier_benchmarks


def test_full_verifier_dominates_simple_baselines_on_validation() -> None:
    config = MailDatasetConfig(
        dataset_id="benchmark_test",
        dataset_version="0.2.0-test",
        seed=20260912,
        train_count=4800,
        validation_count=60,
        frozen_test_count=120,
        evaluation_time=datetime(2026, 9, 12, tzinfo=timezone.utc),
        output_dir="data/processed/test",
        manifest_dir="data/manifests",
    )
    validation = generate_mail_dataset(config)["validation"]
    report = evaluate_verifier_benchmarks(validation)
    full = report.baselines["dynacapa_full"]
    assert not report.full_verifier_failures
    assert full.legal_acceptance_rate == 1.0
    assert full.violation_recall == 1.0
    assert full.severe_violation_recall == 1.0
    assert full.reason_code_recall == 1.0
    assert full.macro_f1 == 1.0
    assert full.macro_f1 > report.baselines["known_tool_allow"].macro_f1
    assert full.macro_f1 > report.baselines["provenance_only"].macro_f1
    assert full.macro_f1 > report.baselines["static_authorization"].macro_f1


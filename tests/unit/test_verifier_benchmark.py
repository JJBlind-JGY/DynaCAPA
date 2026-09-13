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


def test_neighboring_proxies_expose_dynamic_authorization_gap() -> None:
    config = MailDatasetConfig(
        dataset_id="neighbor_proxy_test",
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
    report = evaluate_verifier_benchmarks(
        validation,
        include_neighboring_proxies=True,
    )

    authgraph = report.baselines["authgraph_style_proxy"]
    argus = report.baselines["argus_style_proxy"]
    full = report.baselines["dynacapa_full"]

    assert authgraph.category_recall["external_target"] == 1.0
    assert authgraph.category_recall["fact_without_authorization"] == 1.0
    assert authgraph.category_recall["revocation"] == 0.0
    assert authgraph.category_recall["schema_drift"] == 0.0
    assert argus.category_recall["external_target"] == 1.0
    assert 0.0 <= argus.category_recall["fact_without_authorization"] < 1.0
    assert argus.category_recall["revocation"] == 0.0
    assert argus.category_recall["schema_drift"] == 0.0
    assert report.baselines["provenance_only"].category_recall[
        "parameter_source_mismatch"
    ] == 0.0
    assert report.baselines["static_authorization"].category_recall[
        "parameter_source_mismatch"
    ] == 0.0
    assert authgraph.category_recall["parameter_source_mismatch"] == 1.0
    assert argus.category_recall["parameter_source_mismatch"] == 1.0
    assert full.category_recall["parameter_source_mismatch"] == 1.0
    assert report.baselines["provenance_only"].category_recall[
        "task_invariant_mismatch"
    ] == 0.0
    assert authgraph.category_recall["task_invariant_mismatch"] == 0.0
    assert argus.category_recall["task_invariant_mismatch"] == 1.0
    assert full.category_recall["task_invariant_mismatch"] == 1.0
    assert full.violation_recall > authgraph.violation_recall
    assert full.violation_recall > argus.violation_recall

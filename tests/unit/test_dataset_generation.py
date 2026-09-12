from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dynacapa.data.generators.mail_v0 import (
    MailDatasetConfig,
    build_template_catalog,
    generate_mail_dataset,
    semantic_fingerprint,
)
from dynacapa.data.validation.leakage import audit_splits


@pytest.fixture(scope="module")
def dataset_config() -> MailDatasetConfig:
    return MailDatasetConfig(
        dataset_id="dynacapa_mail_test",
        dataset_version="0.2.0-test",
        seed=20260912,
        train_count=4800,
        validation_count=600,
        frozen_test_count=1200,
        evaluation_time=datetime(2026, 9, 12, tzinfo=timezone.utc),
        output_dir="data/processed/test",
        manifest_dir="data/manifests",
    )


@pytest.fixture(scope="module")
def generated_dataset(dataset_config: MailDatasetConfig):
    return generate_mail_dataset(dataset_config)


def test_template_catalog_is_stratified_across_semantic_families() -> None:
    catalog = build_template_catalog()
    assert len(catalog) == 60
    assert sum(item.split_role == "train" for item in catalog) == 40
    assert sum(item.split_role == "frozen" for item in catalog) == 20
    families = {item.family for item in catalog}
    assert families == {"report", "meeting", "finance", "support", "people", "research"}
    for family in families:
        assert {item.split_role for item in catalog if item.family == family} == {
            "train",
            "frozen",
        }


def test_generator_produces_exact_requested_counts(generated_dataset) -> None:
    assert {name: len(records) for name, records in generated_dataset.items()} == {
        "train": 4800,
        "validation": 600,
        "frozen_test": 1200,
    }


def test_every_task_has_structured_ground_truth(generated_dataset) -> None:
    for records in generated_dataset.values():
        for record in records:
            assert record.ground_truth.acceptable_modes
            assert record.ground_truth.illegal_actions
            assert len(record.provenance.record_fingerprint) == 64


def test_leakage_audit_passes_for_full_design(generated_dataset) -> None:
    report = audit_splits(generated_dataset)
    assert report.passed, report.errors
    assert report.evidence["validation_group_counts"] == {
        "iid": 100,
        "unseen_authorization": 100,
        "unseen_attack": 100,
        "unseen_source": 100,
        "unseen_schema": 100,
        "long_horizon": 100,
    }


def test_generator_is_byte_semantics_deterministic(
    dataset_config: MailDatasetConfig, generated_dataset
) -> None:
    repeated = generate_mail_dataset(dataset_config)
    assert {
        name: [record.provenance.record_fingerprint for record in records]
        for name, records in repeated.items()
    } == {
        name: [record.provenance.record_fingerprint for record in records]
        for name, records in generated_dataset.items()
    }


def test_audit_detects_frozen_template_leakage(generated_dataset) -> None:
    train_template = generated_dataset["train"][0].provenance.template_id
    first_frozen = generated_dataset["frozen_test"][0]
    leaked = first_frozen.model_copy(
        update={
            "provenance": first_frozen.provenance.model_copy(
                update={"template_id": train_template}
            )
        }
    )
    corrupted = {
        **generated_dataset,
        "frozen_test": (leaked, *generated_dataset["frozen_test"][1:]),
    }
    report = audit_splits(corrupted)
    assert not report.passed
    assert any("template_id" in error for error in report.errors)


def test_semantic_fingerprint_ignores_instance_identifiers(generated_dataset) -> None:
    record = generated_dataset["train"][0]
    changed_id = record.model_copy(update={"task_id": "different_instance_id"})
    assert semantic_fingerprint(changed_id) == record.provenance.record_fingerprint


def test_semantic_fingerprint_changes_with_authorization_semantics(generated_dataset) -> None:
    record = next(
        item
        for item in generated_dataset["train"]
        if item.ground_truth.authorization_events
    )
    event = record.ground_truth.authorization_events[0].model_copy(update={"revoked": True})
    changed = record.model_copy(
        update={
            "ground_truth": record.ground_truth.model_copy(
                update={"authorization_events": (event,)}
            )
        }
    )
    assert semantic_fingerprint(changed) != record.provenance.record_fingerprint


def test_training_covers_all_policy_modes(generated_dataset) -> None:
    modes = {
        mode.value
        for record in generated_dataset["train"]
        for mode in record.ground_truth.acceptable_modes
    }
    assert modes == {"execute", "ask", "sandbox", "rewrite", "block", "stop"}


def test_fact_only_holdout_does_not_create_authorization(generated_dataset) -> None:
    record = next(
        item
        for item in generated_dataset["validation"]
        if item.scenario.authorization_pattern == "fact_only_no_grant"
    )
    assert record.ground_truth.authorization_events == ()
    assert record.ground_truth.initial_facts
    assert {mode.value for mode in record.ground_truth.acceptable_modes} == {"block", "stop"}

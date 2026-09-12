from __future__ import annotations

from datetime import datetime, timezone

from dynacapa.data.generators.mail_v0 import MailDatasetConfig, generate_mail_dataset
from dynacapa.data.review import ManualReviewConfig, build_review_pack


def test_review_pack_is_blinded_and_stratified() -> None:
    dataset_config = MailDatasetConfig(
        dataset_id="review_test",
        dataset_version="0.2.0-test",
        seed=20260912,
        train_count=4800,
        validation_count=60,
        frozen_test_count=120,
        evaluation_time=datetime(2026, 9, 12, tzinfo=timezone.utc),
        output_dir="data/processed/test",
        manifest_dir="data/manifests",
    )
    records = generate_mail_dataset(dataset_config)["validation"]
    review_config = ManualReviewConfig(
        review_id="test_review",
        seed=7,
        sample_size=60,
        double_review_count=12,
        output_dir="data/review/test",
    )
    rows, key, manifest = build_review_pack(records, review_config)
    assert len(rows) == 72
    assert len(key) == 60
    assert manifest["double_review_tasks"] == 12
    assert set(manifest["primary_group_counts"].values()) == {10}
    assert set(manifest["double_review_group_counts"].values()) == {2}
    assert all(row["mode_label"] == "" for row in rows)
    assert all("acceptable_modes" not in row for row in rows)
    assert all("record_fingerprint" not in row for row in rows)


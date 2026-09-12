"""Create a blinded, stratified human-review pack from non-frozen tasks."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
from collections import Counter
from typing import Any

from pydantic import Field, model_validator

from dynacapa.core.schemas import StrictModel
from dynacapa.data.task_schema import MailTaskRecord


class ManualReviewConfig(StrictModel):
    review_id: str = Field(min_length=1)
    seed: int
    split: str = "validation"
    sample_size: int = Field(gt=0)
    double_review_count: int = Field(ge=0)
    reviewer_slots: tuple[str, str] = ("primary", "secondary")
    output_dir: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_review_design(self) -> ManualReviewConfig:
        if self.split == "frozen_test":
            raise ValueError("frozen_test cannot be used for development-time manual review")
        if self.double_review_count > self.sample_size:
            raise ValueError("double_review_count cannot exceed sample_size")
        return self


def build_review_pack(
    records: tuple[MailTaskRecord, ...], config: ManualReviewConfig
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    if any(record.split != config.split for record in records):
        raise ValueError("records do not match configured review split")
    if config.sample_size > len(records):
        raise ValueError("sample_size exceeds available records")
    rng = random.Random(config.seed)
    by_group: dict[str, list[MailTaskRecord]] = {}
    for record in records:
        by_group.setdefault(record.diagnostic_group, []).append(record)
    for group_records in by_group.values():
        rng.shuffle(group_records)

    selected = _stratified_take(by_group, config.sample_size)
    selected_by_group: dict[str, list[MailTaskRecord]] = {}
    for record in selected:
        selected_by_group.setdefault(record.diagnostic_group, []).append(record)
    double_review = {
        record.task_id
        for record in _stratified_take(selected_by_group, config.double_review_count)
    }

    rows: list[dict[str, str]] = []
    key: list[dict[str, Any]] = []
    for record in selected:
        rows.append(_review_row(record, config.reviewer_slots[0]))
        if record.task_id in double_review:
            rows.append(_review_row(record, config.reviewer_slots[1]))
        key.append(
            {
                "task_id": record.task_id,
                "diagnostic_group": record.diagnostic_group,
                "acceptable_modes": sorted(
                    mode.value for mode in record.ground_truth.acceptable_modes
                ),
                "legal_actions": [
                    action.model_dump(mode="json")
                    for action in record.ground_truth.legal_actions
                ],
                "illegal_actions": [
                    action.model_dump(mode="json")
                    for action in record.ground_truth.illegal_actions
                ],
                "required_confirmations": record.ground_truth.required_confirmations,
                "record_fingerprint": record.provenance.record_fingerprint,
            }
        )
    manifest = {
        "review_id": config.review_id,
        "seed": config.seed,
        "split": config.split,
        "unique_tasks": len(selected),
        "review_rows": len(rows),
        "double_review_tasks": len(double_review),
        "primary_group_counts": dict(
            sorted(Counter(record.diagnostic_group for record in selected).items())
        ),
        "double_review_group_counts": dict(
            sorted(
                Counter(
                    record.diagnostic_group
                    for record in selected
                    if record.task_id in double_review
                ).items()
            )
        ),
        "gold_blinded": True,
        "reviewer_identities": None,
        "status": "unassigned",
    }
    return rows, key, manifest


def review_csv_bytes(rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().replace("\r\n", "\n").encode("utf-8")


def key_jsonl_bytes(key: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in key)
        + "\n"
    ).encode("utf-8")


def attach_file_hashes(
    manifest: dict[str, Any], review_bytes: bytes, key_bytes: bytes
) -> dict[str, Any]:
    return {
        **manifest,
        "files": {
            "blinded_review_csv": {
                "sha256": hashlib.sha256(review_bytes).hexdigest(),
                "bytes": len(review_bytes),
            },
            "adjudication_key_jsonl": {
                "sha256": hashlib.sha256(key_bytes).hexdigest(),
                "bytes": len(key_bytes),
            },
        },
    }


def _stratified_take(
    by_group: dict[str, list[MailTaskRecord]], count: int
) -> list[MailTaskRecord]:
    groups = sorted(by_group)
    base, remainder = divmod(count, len(groups))
    selected: list[MailTaskRecord] = []
    for index, group in enumerate(groups):
        group_count = base + int(index < remainder)
        if group_count > len(by_group[group]):
            raise ValueError(f"insufficient records in review group {group}")
        selected.extend(by_group[group][:group_count])
    return sorted(selected, key=lambda record: record.task_id)


def _review_row(record: MailTaskRecord, reviewer_slot: str) -> dict[str, str]:
    return {
        "review_unit_id": f"{record.task_id}:{reviewer_slot}",
        "task_id": record.task_id,
        "reviewer_slot": reviewer_slot,
        "diagnostic_group": record.diagnostic_group,
        "template_id": record.provenance.template_id,
        "natural_language_request": record.natural_language_request,
        "context_messages_json": json.dumps(
            [message.model_dump(mode="json") for message in record.context_messages],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "authorization_events_json": json.dumps(
            [event.model_dump(mode="json") for event in record.ground_truth.authorization_events],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "initial_facts_json": json.dumps(
            [fact.model_dump(mode="json") for fact in record.ground_truth.initial_facts],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "tool_schema_version": record.scenario.tool_schema_version,
        "horizon": str(record.scenario.horizon),
        "mode_label": "",
        "authorized_action_possible": "",
        "authorized_tool": "",
        "authorized_recipient": "",
        "requires_confirmation": "",
        "primary_reason_code": "",
        "severity": "",
        "reviewer_confidence": "",
        "reviewer_notes": "",
    }


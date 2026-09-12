"""Fail-closed split isolation and duplicate auditing."""

from __future__ import annotations

from collections import Counter

from pydantic import Field, JsonValue

from dynacapa.core.schemas import StrictModel
from dynacapa.data.generators.mail_v0 import semantic_fingerprint
from dynacapa.data.task_schema import MailTaskRecord


class LeakageAuditReport(StrictModel):
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    counts: dict[str, int] = Field(default_factory=dict)
    evidence: dict[str, JsonValue] = Field(default_factory=dict)


def audit_splits(
    splits: dict[str, tuple[MailTaskRecord, ...]],
) -> LeakageAuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    expected_names = {"train", "validation", "frozen_test"}
    if set(splits) != expected_names:
        errors.append(f"split names must be exactly {sorted(expected_names)}")
        return LeakageAuditReport(passed=False, errors=tuple(errors))

    train = splits["train"]
    validation = splits["validation"]
    frozen = splits["frozen_test"]
    all_records = (*train, *validation, *frozen)
    task_ids = [record.task_id for record in all_records]
    fingerprints = [record.provenance.record_fingerprint for record in all_records]
    if len(task_ids) != len(set(task_ids)):
        errors.append("duplicate task_id detected across splits")
    if len(fingerprints) != len(set(fingerprints)):
        errors.append("semantic record fingerprint duplicated across splits")
    invalid_fingerprints = [
        record.task_id
        for record in all_records
        if record.provenance.record_fingerprint != semantic_fingerprint(record)
    ]
    if invalid_fingerprints:
        errors.append(
            f"stored semantic fingerprint mismatch: {invalid_fingerprints[:10]}"
        )
    incomplete_ground_truth = [
        record.task_id
        for record in all_records
        if not record.ground_truth.acceptable_modes
        or not record.ground_truth.illegal_actions
    ]
    if incomplete_ground_truth:
        errors.append(f"incomplete structured ground truth: {incomplete_ground_truth[:10]}")

    train_dimensions = _dimension_sets(train)
    frozen_dimensions = _dimension_sets(frozen)
    for dimension in (
        "template_id",
        "authorization_pattern",
        "attack_expression_id",
        "tool_schema_version",
        "source_combination",
    ):
        overlap = train_dimensions[dimension] & frozen_dimensions[dimension]
        if overlap:
            errors.append(
                f"frozen_test leaks train {dimension}: {sorted(overlap)[:10]}"
            )

    validation_by_group: dict[str, tuple[MailTaskRecord, ...]] = {}
    for group in (
        "iid",
        "unseen_authorization",
        "unseen_attack",
        "unseen_source",
        "unseen_schema",
        "long_horizon",
    ):
        group_records = tuple(record for record in validation if record.diagnostic_group == group)
        validation_by_group[group] = group_records
        if not group_records:
            errors.append(f"validation diagnostic group is empty: {group}")

    _check_iid(validation_by_group["iid"], train_dimensions, errors)
    _check_controlled_holdout(
        validation_by_group["unseen_authorization"],
        train_dimensions,
        "authorization_pattern",
        errors,
    )
    _check_controlled_holdout(
        validation_by_group["unseen_attack"],
        train_dimensions,
        "attack_expression_id",
        errors,
    )
    _check_controlled_holdout(
        validation_by_group["unseen_source"],
        train_dimensions,
        "source_combination",
        errors,
    )
    _check_controlled_holdout(
        validation_by_group["unseen_schema"],
        train_dimensions,
        "tool_schema_version",
        errors,
    )
    if validation_by_group["long_horizon"]:
        train_max_horizon = max(record.scenario.horizon for record in train)
        validation_min_horizon = min(
            record.scenario.horizon for record in validation_by_group["long_horizon"]
        )
        if validation_min_horizon <= train_max_horizon:
            errors.append(
                "long_horizon validation is not strictly longer than the training maximum"
            )
        _check_shared_dimensions(
            validation_by_group["long_horizon"], train_dimensions, set(), errors
        )

    for split_name, records in splits.items():
        if not records:
            errors.append(f"empty split: {split_name}")
        mode_counts = Counter(
            mode.value
            for record in records
            for mode in record.ground_truth.acceptable_modes
        )
        if not mode_counts:
            warnings.append(f"no acceptable modes recorded for {split_name}")
        if split_name == "train":
            required_modes = {"execute", "ask", "sandbox", "rewrite", "block", "stop"}
            missing_modes = required_modes - set(mode_counts)
            if missing_modes:
                errors.append(
                    f"training split lacks acceptable-mode coverage: {sorted(missing_modes)}"
                )

    evidence: dict[str, JsonValue] = {
        "train_dimensions": _json_dimension_sets(train_dimensions),
        "frozen_test_dimensions": _json_dimension_sets(frozen_dimensions),
        "validation_group_counts": {
            group: len(records) for group, records in validation_by_group.items()
        },
        "attack_distribution": {
            split_name: dict(
                sorted(Counter(record.scenario.attack_type for record in records).items())
            )
            for split_name, records in splits.items()
        },
        "acceptable_mode_distribution": {
            split_name: dict(
                sorted(
                    Counter(
                        mode.value
                        for record in records
                        for mode in record.ground_truth.acceptable_modes
                    ).items()
                )
            )
            for split_name, records in splits.items()
        },
    }
    return LeakageAuditReport(
        passed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        counts={name: len(records) for name, records in splits.items()},
        evidence=evidence,
    )


def _dimension_sets(records: tuple[MailTaskRecord, ...]) -> dict[str, set[str]]:
    return {
        "template_id": {record.provenance.template_id for record in records},
        "authorization_pattern": {
            record.scenario.authorization_pattern for record in records
        },
        "attack_expression_id": {
            record.scenario.attack_expression_id for record in records
        },
        "tool_schema_version": {
            record.scenario.tool_schema_version for record in records
        },
        "source_combination": {record.scenario.source_combination for record in records},
    }


def _json_dimension_sets(dimensions: dict[str, set[str]]) -> dict[str, JsonValue]:
    return {name: sorted(values) for name, values in dimensions.items()}


def _check_iid(
    records: tuple[MailTaskRecord, ...],
    train_dimensions: dict[str, set[str]],
    errors: list[str],
) -> None:
    dimensions = _dimension_sets(records)
    for dimension in dimensions:
        unseen = dimensions[dimension] - train_dimensions[dimension]
        if unseen:
            errors.append(f"IID validation has unseen {dimension}: {sorted(unseen)}")


def _check_controlled_holdout(
    records: tuple[MailTaskRecord, ...],
    train_dimensions: dict[str, set[str]],
    dimension: str,
    errors: list[str],
) -> None:
    overlap = _dimension_sets(records)[dimension] & train_dimensions[dimension]
    if overlap:
        errors.append(
            f"{dimension} holdout overlaps training values: {sorted(overlap)[:10]}"
        )
    _check_shared_dimensions(records, train_dimensions, {dimension}, errors)


def _check_shared_dimensions(
    records: tuple[MailTaskRecord, ...],
    train_dimensions: dict[str, set[str]],
    excluded_dimensions: set[str],
    errors: list[str],
) -> None:
    dimensions = _dimension_sets(records)
    for name, values in dimensions.items():
        if name in excluded_dimensions:
            continue
        unexpected = values - train_dimensions[name]
        if unexpected:
            errors.append(
                f"controlled holdout unexpectedly changes {name}: {sorted(unexpected)[:10]}"
            )

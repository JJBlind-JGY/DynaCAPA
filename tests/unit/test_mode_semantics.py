from __future__ import annotations

import pytest

from dynacapa.core.enums import PolicyMode
from dynacapa.data.mode_semantics import ModeEvidence, resolve_mode


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            ModeEvidence(
                state_integrity_ok=False,
                requested_subactions=1,
                authorized_subactions=1,
                all_critical_args_trusted=True,
            ),
            PolicyMode.STOP,
        ),
        (
            ModeEvidence(
                state_integrity_ok=True,
                requested_subactions=1,
                authorized_subactions=1,
                recoverable_missing_fields=("confirmation",),
                all_critical_args_trusted=True,
            ),
            PolicyMode.ASK,
        ),
        (
            ModeEvidence(
                state_integrity_ok=True,
                requested_subactions=1,
                authorized_subactions=0,
                all_critical_args_trusted=True,
            ),
            PolicyMode.BLOCK,
        ),
        (
            ModeEvidence(
                state_integrity_ok=True,
                requested_subactions=2,
                authorized_subactions=1,
                all_critical_args_trusted=True,
                core_goal_preserved_by_authorized_subset=True,
            ),
            PolicyMode.REWRITE,
        ),
        (
            ModeEvidence(
                state_integrity_ok=True,
                requested_subactions=1,
                authorized_subactions=1,
                all_critical_args_trusted=True,
                preview_required=True,
                preview_supported=True,
                complete_action_executable=True,
            ),
            PolicyMode.SANDBOX,
        ),
        (
            ModeEvidence(
                state_integrity_ok=True,
                requested_subactions=1,
                authorized_subactions=1,
                all_critical_args_trusted=True,
                complete_action_executable=True,
            ),
            PolicyMode.EXECUTE,
        ),
    ],
)
def test_each_six_mode_trigger_resolves_uniquely(
    evidence: ModeEvidence, expected: PolicyMode
) -> None:
    assert resolve_mode(evidence).mode == expected


def test_partial_scope_without_core_goal_preservation_is_rejected() -> None:
    evidence = ModeEvidence(
        state_integrity_ok=True,
        requested_subactions=2,
        authorized_subactions=1,
        all_critical_args_trusted=True,
        core_goal_preserved_by_authorized_subset=False,
    )
    with pytest.raises(ValueError, match="resolve uniquely"):
        resolve_mode(evidence)


def test_untrusted_critical_argument_is_not_silently_ask_or_execute() -> None:
    evidence = ModeEvidence(
        state_integrity_ok=True,
        requested_subactions=1,
        authorized_subactions=1,
        all_critical_args_trusted=False,
    )
    with pytest.raises(ValueError, match="resolve uniquely"):
        resolve_mode(evidence)


def test_inconsistent_complete_action_is_rejected_at_schema_boundary() -> None:
    with pytest.raises(ValueError, match="complete_action_executable"):
        ModeEvidence(
            state_integrity_ok=True,
            requested_subactions=1,
            authorized_subactions=0,
            all_critical_args_trusted=True,
            complete_action_executable=True,
        )

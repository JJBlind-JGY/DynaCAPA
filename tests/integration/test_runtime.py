from __future__ import annotations

import pytest

from dynacapa.core.enums import PolicyMode, ReasonCode
from dynacapa.runtime import DynaCAPARuntime


@pytest.mark.integration
def test_authorized_candidate_executes_without_shield(
    runtime: DynaCAPARuntime, valid_send_candidate
) -> None:
    transition = runtime.step(valid_send_candidate)
    assert not transition.verifier_result.hard_violation
    assert not transition.shield_intervened
    assert transition.candidate_output == transition.executed_output
    assert transition.candidate_output is not transition.executed_output
    assert transition.observation["sent_count"] == 1
    assert transition.task_reward == 1.0


@pytest.mark.integration
def test_transition_isolated_from_later_candidate_mutation(
    runtime: DynaCAPARuntime, valid_send_candidate
) -> None:
    transition = runtime.step(valid_send_candidate)
    valid_send_candidate.args["recipient"] = "mutated@example.com"
    assert transition.candidate_output.args["recipient"] == "alice@example.com"
    assert transition.executed_output.args["recipient"] == "alice@example.com"


@pytest.mark.integration
def test_unauthorized_candidate_is_blocked_and_logged_separately(
    runtime: DynaCAPARuntime, valid_send_candidate
) -> None:
    proof = valid_send_candidate.proof.model_copy(
        update={"target_scope": ("mallory@example.com",)}
    )
    candidate = valid_send_candidate.model_copy(
        update={
            "args": {**valid_send_candidate.args, "recipient": "mallory@example.com"},
            "proof": proof,
        }
    )
    transition = runtime.step(candidate)
    assert transition.verifier_result.hard_violation
    assert transition.shield_intervened
    assert transition.candidate_output.mode == PolicyMode.EXECUTE
    assert transition.executed_output.mode == PolicyMode.BLOCK
    assert transition.candidate_output != transition.executed_output
    assert transition.observation["sent_count"] == 0
    assert "mode" in transition.shield_edit_fields


@pytest.mark.integration
def test_missing_confirmation_is_converted_to_ask(
    env,
    authorization,
    authorization_event,
    valid_send_candidate,
) -> None:
    authorization.update(
        events=[authorization_event.model_copy(update={"confirmation_required": True, "version": 2})]
    )
    runtime = DynaCAPARuntime(
        env=env,
        authorization=authorization,
        tool_definitions=__import__(
            "dynacapa.contracts.compiler", fromlist=["default_mail_tool_definitions"]
        ).default_mail_tool_definitions(),
    )
    transition = runtime.step(valid_send_candidate)
    assert transition.executed_output.mode == PolicyMode.ASK
    assert transition.observation["sent_count"] == 0


@pytest.mark.integration
def test_unknown_tool_never_reaches_environment(runtime, valid_send_candidate) -> None:
    candidate = valid_send_candidate.model_copy(
        update={
            "tool": "real_mail_api",
            "proof": valid_send_candidate.proof.model_copy(update={"tool_name": "real_mail_api"}),
        }
    )
    transition = runtime.step(candidate)
    assert transition.executed_output.mode == PolicyMode.BLOCK
    assert ReasonCode.TOOL_NOT_FOUND in transition.verifier_result.reason_codes

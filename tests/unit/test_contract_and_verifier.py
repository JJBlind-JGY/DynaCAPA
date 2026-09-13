from __future__ import annotations

from dynacapa.authorization.engine import AuthorizationEngine
from dynacapa.contracts.compiler import DynamicContractCompiler, default_mail_tool_definitions
from dynacapa.core.enums import IssuerType, PolicyMode, ReasonCode, SourceType
from dynacapa.core.schemas import AuthorizationEvent, Fact
from dynacapa.verifier.verifier import DeterministicVerifier


def test_compiler_uses_only_active_authorization_scope(
    authorization: AuthorizationEngine,
) -> None:
    contract = DynamicContractCompiler().compile(
        authorization.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    assert contract.allowed_target_scope == ("alice@example.com",)
    assert contract.allowed_object_scope == ("report_summary",)


def test_schema_drift_invalidates_old_proof(
    authorization: AuthorizationEngine, valid_send_candidate
) -> None:
    definition = default_mail_tool_definitions()["send_email"].model_copy(
        update={"schema_version": "v2"}
    )
    contract = DynamicContractCompiler().compile(authorization.state(), {}, definition)
    result = DeterministicVerifier().verify(
        authorization.state(), contract, valid_send_candidate
    )
    assert result.hard_violation
    assert ReasonCode.SCHEMA_VERSION_MISMATCH in result.reason_codes


def test_untrusted_parameter_source_is_rejected(
    authorization: AuthorizationEngine,
    valid_send_candidate,
    now,
) -> None:
    malicious = Fact(
        id="fact_web_recipient",
        key="recipient",
        value="mallory@example.com",
        source_type=SourceType.WEB,
        source_id="untrusted_page",
        observed_at=now,
    )
    authorization.update(facts=[malicious])
    candidate = valid_send_candidate.model_copy(
        update={
            "proof": valid_send_candidate.proof.model_copy(
                update={"source_refs": {"recipient": malicious.id}}
            )
        }
    )
    contract = DynamicContractCompiler().compile(
        authorization.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(authorization.state(), contract, candidate)
    assert result.hard_violation
    assert ReasonCode.PARAM_SOURCE_NOT_ALLOWED in result.reason_codes


def test_trusted_source_must_support_the_parameter_value(
    authorization: AuthorizationEngine,
    valid_send_candidate,
    now,
) -> None:
    unrelated = Fact(
        id="fact_trusted_but_unrelated",
        key="approval_state",
        value="approved",
        source_type=SourceType.TRUSTED_SYSTEM,
        source_id="approval_service",
        observed_at=now,
    )
    authorization.update(facts=[unrelated])
    candidate = valid_send_candidate.model_copy(
        update={
            "proof": valid_send_candidate.proof.model_copy(
                update={"source_refs": {"recipient": unrelated.id}}
            )
        }
    )
    contract = DynamicContractCompiler().compile(
        authorization.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(authorization.state(), contract, candidate)
    assert result.hard_violation
    assert ReasonCode.PARAM_SOURCE_NOT_ALLOWED in result.reason_codes


def test_confirmation_is_a_dynamic_hard_check(
    authorization_event: AuthorizationEvent,
    approval_fact: Fact,
    valid_send_candidate,
) -> None:
    engine = AuthorizationEngine()
    engine.update(
        events=[authorization_event.model_copy(update={"confirmation_required": True})],
        facts=[approval_fact],
    )
    contract = DynamicContractCompiler().compile(
        engine.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(engine.state(), contract, valid_send_candidate)
    assert result.hard_violation
    assert result.reason_codes == (ReasonCode.CONFIRMATION_REQUIRED,)


def test_revoked_reference_fails_verification(
    authorization: AuthorizationEngine,
    authorization_event: AuthorizationEvent,
    valid_send_candidate,
) -> None:
    authorization.update(
        events=[authorization_event.model_copy(update={"revoked": True, "version": 2})]
    )
    contract = DynamicContractCompiler().compile(
        authorization.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(
        authorization.state(), contract, valid_send_candidate
    )
    assert result.hard_violation
    assert ReasonCode.AUTHORIZATION_REVOKED in result.reason_codes


def test_unsatisfied_condition_has_specific_reason(
    authorization_event: AuthorizationEvent,
    approval_fact: Fact,
    valid_send_candidate,
) -> None:
    engine = AuthorizationEngine()
    engine.update(
        events=[authorization_event],
        facts=[approval_fact.model_copy(update={"value": "pending"})],
    )
    contract = DynamicContractCompiler().compile(
        engine.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(engine.state(), contract, valid_send_candidate)
    assert result.hard_violation
    assert ReasonCode.CONDITION_UNSATISFIED in result.reason_codes


def test_missing_object_scope_is_not_treated_as_wildcard(
    authorization: AuthorizationEngine, valid_send_candidate
) -> None:
    candidate = valid_send_candidate.model_copy(
        update={
            "proof": valid_send_candidate.proof.model_copy(update={"object_scope": ()})
        }
    )
    contract = DynamicContractCompiler().compile(
        authorization.state(), {}, default_mail_tool_definitions()["send_email"]
    )
    result = DeterministicVerifier().verify(authorization.state(), contract, candidate)
    assert result.hard_violation
    assert ReasonCode.SCOPE_EXCEEDED in result.reason_codes

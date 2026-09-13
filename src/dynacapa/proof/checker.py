"""Deterministic proof checker for D-CAPA contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from dynacapa.authorization.engine import AuthorizationState
from dynacapa.core.constants import SCHEMA_VERSION
from dynacapa.core.enums import IssuerType, ReasonCode, SideEffectLevel, SourceType
from dynacapa.core.schemas import (
    ActionPolicyOutput,
    DynamicToolContract,
    VerifierChecks,
)


class ProofChecker:
    def check(
        self,
        auth_state: AuthorizationState,
        contract: DynamicToolContract,
        candidate: ActionPolicyOutput,
        at: datetime | None = None,
    ) -> tuple[VerifierChecks, tuple[ReasonCode, ...]]:
        selected_at = at or datetime.now(timezone.utc)
        proof = candidate.proof

        bind_ok = proof.action_type == contract.action_type and proof.tool_name == candidate.tool
        schema_ok = (
            proof.tool_schema_version == contract.tool_schema_version
            and candidate.schema_version == SCHEMA_VERSION
            and proof.schema_version == SCHEMA_VERSION
            and contract.schema_version == SCHEMA_VERSION
        )
        mode_ok = candidate.mode in contract.allowed_modes

        referenced_events = tuple(
            event
            for ref in proof.authorization_refs
            if (event := auth_state.event_by_id(ref)) is not None
        )
        revocation_ok = all(not event.revoked for event in referenced_events)
        freshness_ok = self._facts_fresh(auth_state, referenced_events, selected_at)
        condition_unsatisfied = any(
            not event.revoked
            and event.is_time_valid(selected_at)
            and not auth_state.conditions_hold(event, selected_at)
            for event in referenced_events
        )
        active_ids = {event.id for event in auth_state.active_rights(selected_at)}
        usable_events = tuple(event for event in referenced_events if event.id in active_ids)

        auth_path_ok = any(
            event.action_type == contract.action_type
            and _covers(event.object_scope, proof.object_scope)
            and _covers(event.target_scope, proof.target_scope)
            for event in usable_events
        )
        scope_complete = (
            not contract.allowed_object_scope or bool(proof.object_scope)
        ) and (not contract.allowed_target_scope or bool(proof.target_scope))
        scope_ok = (
            scope_complete
            and
            _covers(contract.allowed_object_scope, proof.object_scope)
            and _covers(contract.allowed_target_scope, proof.target_scope)
            and self._arguments_within_scope(candidate, proof.target_scope)
        )
        param_source_ok = self._parameter_sources_ok(auth_state, contract, candidate, selected_at)
        confirm_ok = not contract.confirmation_required or self._confirmation_ok(
            auth_state, proof.confirmation_refs, selected_at
        )
        effect_ok = proof.expected_effects.get("side_effect_level") == contract.side_effect_level.value
        rollback_ok = not contract.reversible or bool(proof.rollback_plan)

        checks = VerifierChecks(
            bind_ok=bind_ok and mode_ok,
            auth_path_ok=auth_path_ok,
            param_source_ok=param_source_ok,
            scope_ok=scope_ok,
            confirm_ok=confirm_ok,
            effect_ok=effect_ok,
            rollback_ok=rollback_ok,
            freshness_ok=freshness_ok,
            revocation_ok=revocation_ok,
            schema_version_ok=schema_ok,
        )
        reasons: list[ReasonCode] = []
        if not mode_ok:
            reasons.append(ReasonCode.MODE_NOT_ALLOWED)
        if not bind_ok:
            reasons.append(ReasonCode.BINDING_MISMATCH)
        if not auth_path_ok:
            reasons.append(ReasonCode.AUTHORIZATION_MISSING)
        if condition_unsatisfied:
            reasons.append(ReasonCode.CONDITION_UNSATISFIED)
        if not revocation_ok:
            reasons.append(ReasonCode.AUTHORIZATION_REVOKED)
        if not freshness_ok:
            reasons.append(ReasonCode.FACT_STALE)
        if not param_source_ok:
            reasons.append(ReasonCode.PARAM_SOURCE_NOT_ALLOWED)
        if not scope_ok:
            reasons.append(ReasonCode.SCOPE_EXCEEDED)
        if not confirm_ok:
            reasons.append(ReasonCode.CONFIRMATION_REQUIRED)
        if not effect_ok:
            reasons.append(ReasonCode.EFFECT_MISMATCH)
        if not rollback_ok:
            reasons.append(ReasonCode.ROLLBACK_MISSING)
        if not schema_ok:
            reasons.append(ReasonCode.SCHEMA_VERSION_MISMATCH)
        return checks, tuple(dict.fromkeys(reasons))

    @staticmethod
    def _facts_fresh(
        state: AuthorizationState, events: tuple[object, ...], at: datetime
    ) -> bool:
        for event in events:
            for key in event.conditions:
                if state.freshest_fact(key, at) is None:
                    return False
        return True

    @staticmethod
    def _arguments_within_scope(
        candidate: ActionPolicyOutput, target_scope: tuple[str, ...]
    ) -> bool:
        recipient = candidate.args.get("recipient")
        return recipient is None or str(recipient) in target_scope or "*" in target_scope

    @staticmethod
    def _parameter_sources_ok(
        state: AuthorizationState,
        contract: DynamicToolContract,
        candidate: ActionPolicyOutput,
        at: datetime,
    ) -> bool:
        for argument, rule in contract.critical_args.items():
            if rule.required and argument not in candidate.args:
                return False
            if argument not in candidate.args:
                continue
            source_ref = candidate.proof.source_refs.get(argument)
            if source_ref is None:
                return False
            source_type: SourceType | None = None
            event = state.event_by_id(source_ref)
            if event is not None and not event.revoked and event.is_time_valid(at):
                source_type = {
                    IssuerType.AUTHENTICATED_USER: SourceType.AUTHENTICATED_USER,
                    IssuerType.TRUSTED_SYSTEM: SourceType.TRUSTED_SYSTEM,
                }[event.issuer_type]
                if argument == "recipient" and not _covers(
                    event.target_scope,
                    (str(candidate.args[argument]),),
                ):
                    return False
            fact = state.fact_by_id(source_ref)
            if fact is not None and fact.is_fresh(at):
                source_type = fact.source_type
                if fact.key != argument or fact.value != candidate.args[argument]:
                    return False
            if source_type not in rule.allowed_source_types:
                return False
        return True

    @staticmethod
    def _confirmation_ok(
        state: AuthorizationState, confirmation_refs: tuple[str, ...], at: datetime
    ) -> bool:
        return any(
            fact is not None
            and fact.key.startswith("confirmation")
            and fact.value is True
            and fact.is_fresh(at)
            for ref in confirmation_refs
            if (fact := state.fact_by_id(ref)) is not None
        )


def _covers(allowed: tuple[str, ...], requested: tuple[str, ...]) -> bool:
    if not requested:
        return True
    return "*" in allowed or set(requested).issubset(allowed)

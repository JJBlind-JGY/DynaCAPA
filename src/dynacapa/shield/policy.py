"""Resolve unsafe candidates into explicit, separately logged outputs."""

from __future__ import annotations

from pydantic import Field

from dynacapa.core.enums import PolicyMode, ReasonCode, Termination
from dynacapa.core.schemas import (
    AskPolicyOutput,
    BlockPolicyOutput,
    PolicyOutput,
    StrictModel,
    VerifierResult,
)


class ShieldResolution(StrictModel):
    executed_output: PolicyOutput
    intervened: bool
    edited_fields: tuple[str, ...] = Field(default_factory=tuple)


class Shield:
    def resolve(
        self,
        state: object,
        candidate_output: PolicyOutput,
        verifier_result: VerifierResult,
    ) -> ShieldResolution:
        del state  # Reserved for state-aware repair policies.
        if not verifier_result.hard_violation:
            # Equality does not imply identity: execution receives an independent copy.
            return ShieldResolution(
                executed_output=candidate_output.model_copy(deep=True), intervened=False
            )

        reasons = verifier_result.reason_codes or (ReasonCode.SHIELD_BLOCKED,)
        if set(reasons) == {ReasonCode.CONFIRMATION_REQUIRED}:
            executed: PolicyOutput = AskPolicyOutput(
                mode=PolicyMode.ASK,
                termination=Termination.CONTINUE,
                question="Please confirm this side effect before it is executed.",
                missing_fields=("confirmation",),
            )
            edited = ("mode", "tool", "args", "proof")
        else:
            executed = BlockPolicyOutput(
                mode=PolicyMode.BLOCK,
                termination=Termination.CONTINUE,
                reason_code=reasons[0],
                detail="Deterministic D-CAPA verification rejected the candidate action.",
            )
            edited = ("mode", "tool", "args", "proof")
        return ShieldResolution(
            executed_output=executed,
            intervened=True,
            edited_fields=edited,
        )

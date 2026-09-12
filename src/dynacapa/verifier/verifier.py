"""Hard checks and soft costs are deliberately separate outputs."""

from __future__ import annotations

from datetime import datetime

from dynacapa.authorization.engine import AuthorizationState
from dynacapa.core.enums import PolicyMode, ReasonCode
from dynacapa.core.schemas import (
    ActionPolicyOutput,
    DynamicToolContract,
    InterventionCandidate,
    PolicyOutput,
    VerifierChecks,
    VerifierResult,
)
from dynacapa.proof.checker import ProofChecker


class DeterministicVerifier:
    def __init__(self, proof_checker: ProofChecker | None = None) -> None:
        self.proof_checker = proof_checker or ProofChecker()

    def verify(
        self,
        auth_state: AuthorizationState,
        contract: DynamicToolContract | None,
        candidate_output: PolicyOutput,
        at: datetime | None = None,
    ) -> VerifierResult:
        if not isinstance(candidate_output, ActionPolicyOutput):
            return VerifierResult(
                hard_violation=False,
                checks=VerifierChecks.all_passed(),
                soft_costs=_soft_costs(candidate_output.mode),
            )

        if contract is None:
            return VerifierResult(
                hard_violation=True,
                checks=VerifierChecks(),
                reason_codes=(ReasonCode.TOOL_NOT_FOUND,),
                soft_costs=_soft_costs(candidate_output.mode),
                intervention_candidates=(
                    InterventionCandidate(
                        mode=PolicyMode.BLOCK,
                        reason=ReasonCode.TOOL_NOT_FOUND,
                        target_fields=("mode", "tool", "args", "proof"),
                    ),
                ),
            )

        checks, reasons = self.proof_checker.check(auth_state, contract, candidate_output, at)
        hard_violation = not all(checks.model_dump().values())
        interventions = ()
        if hard_violation:
            preferred_mode = (
                PolicyMode.ASK
                if set(reasons) == {ReasonCode.CONFIRMATION_REQUIRED}
                else PolicyMode.BLOCK
            )
            interventions = (
                InterventionCandidate(
                    mode=preferred_mode,
                    reason=reasons[0],
                    target_fields=("mode", "tool", "args", "proof"),
                ),
            )
        return VerifierResult(
            hard_violation=hard_violation,
            checks=checks,
            reason_codes=reasons,
            soft_costs=_soft_costs(candidate_output.mode),
            intervention_candidates=interventions,
        )


def _soft_costs(mode: PolicyMode) -> dict[str, float]:
    return {
        "ask": float(mode == PolicyMode.ASK),
        "sandbox": float(mode == PolicyMode.SANDBOX),
        "rewrite": float(mode == PolicyMode.REWRITE),
        "overblock": 0.0,
        "tool_call": float(mode in {PolicyMode.EXECUTE, PolicyMode.SANDBOX, PolicyMode.REWRITE}),
        "token": 0.0,
        "latency": 0.0,
        "recovery": 0.0,
    }


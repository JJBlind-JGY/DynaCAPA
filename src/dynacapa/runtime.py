"""One auditable D-CAPA transition from proposal to sandbox state update."""

from __future__ import annotations

from dynacapa.authorization.engine import AuthorizationEngine
from dynacapa.contracts.compiler import DynamicContractCompiler, ToolDefinition
from dynacapa.core.hashing import compose_state_hash
from dynacapa.core.schemas import ActionPolicyOutput, PolicyOutput, Transition
from dynacapa.envs.base import SandboxEnvironment
from dynacapa.shield.policy import Shield
from dynacapa.verifier.verifier import DeterministicVerifier


class DynaCAPARuntime:
    def __init__(
        self,
        env: SandboxEnvironment,
        authorization: AuthorizationEngine,
        tool_definitions: dict[str, ToolDefinition],
        compiler: DynamicContractCompiler | None = None,
        verifier: DeterministicVerifier | None = None,
        shield: Shield | None = None,
    ) -> None:
        self.env = env
        self.authorization = authorization
        self.tool_definitions = {
            name: definition.model_copy(deep=True)
            for name, definition in tool_definitions.items()
        }
        self.compiler = compiler or DynamicContractCompiler()
        self.verifier = verifier or DeterministicVerifier()
        self.shield = shield or Shield()

    def step(self, candidate_output: PolicyOutput) -> Transition:
        logged_candidate = candidate_output.model_copy(deep=True)
        snapshot = self.env.snapshot()
        auth_state = self.authorization.state()
        snapshot = snapshot.model_copy(
            update={
                "authorization_version": auth_state.version,
                "state_hash": compose_state_hash(
                    snapshot.environment_state_hash,
                    auth_state.version,
                    snapshot.tool_versions,
                ),
            }
        )
        contract = None
        if isinstance(logged_candidate, ActionPolicyOutput):
            definition = self.tool_definitions.get(logged_candidate.tool)
            if definition is not None:
                contract = self.compiler.compile(
                    auth_state=auth_state,
                    env_state=dict(snapshot.payload),
                    tool_schema=definition,
                )
        verifier_result = self.verifier.verify(auth_state, contract, logged_candidate)
        resolution = self.shield.resolve(snapshot, logged_candidate, verifier_result)
        env_step = self.env.step(resolution.executed_output)
        combined_costs = dict(verifier_result.soft_costs)
        combined_costs.update(env_step.soft_costs)
        return Transition(
            state_id=snapshot.state_hash,
            candidate_output=logged_candidate,
            verifier_result=verifier_result,
            executed_output=resolution.executed_output,
            shield_intervened=resolution.intervened,
            shield_edit_fields=resolution.edited_fields,
            task_reward=env_step.task_reward,
            soft_costs=combined_costs,
            observation=env_step.observation,
            next_state_id=compose_state_hash(
                env_step.state_hash, auth_state.version, snapshot.tool_versions
            ),
            snapshot_id=snapshot.id,
        )

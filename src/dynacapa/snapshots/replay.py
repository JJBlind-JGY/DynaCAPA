"""Replay executed outputs from an exact environment snapshot."""

from __future__ import annotations

from dynacapa.core.schemas import EnvironmentStep, PolicyOutput, StateSnapshot
from dynacapa.envs.base import SandboxEnvironment


class ReplayRunner:
    def run(
        self,
        env: SandboxEnvironment,
        snapshot: StateSnapshot,
        executed_output: PolicyOutput,
    ) -> EnvironmentStep:
        branch = env.clone(snapshot)
        return branch.step(executed_output)

    def run_pair(
        self,
        env: SandboxEnvironment,
        snapshot: StateSnapshot,
        original: PolicyOutput,
        intervention: PolicyOutput,
        policy_version: str,
        seed: int,
    ) -> tuple[EnvironmentStep, EnvironmentStep]:
        del policy_version  # Bound into ReplayPair by the caller.
        if snapshot.seed != seed:
            raise ValueError("replay seed must match the StateSnapshot seed")
        return (
            self.run(env, snapshot, original),
            self.run(env, snapshot, intervention),
        )


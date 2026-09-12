"""Environment interface shared by Mail, File, and DB sandboxes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from dynacapa.core.schemas import EnvironmentStep, PolicyOutput, StateSnapshot


class SandboxEnvironment(ABC):
    @abstractmethod
    def reset(self, task: Mapping[str, Any], seed: int) -> dict[str, Any]:
        """Reset to a task-defined initial state and return the first observation."""

    @abstractmethod
    def step(self, executed_output: PolicyOutput) -> EnvironmentStep:
        """Apply only the Shield-resolved output."""

    @abstractmethod
    def snapshot(self) -> StateSnapshot:
        """Capture all mutable state, versions, and RNG state."""

    @abstractmethod
    def restore(self, snapshot: StateSnapshot | str) -> dict[str, Any]:
        """Restore an exact prior snapshot after integrity verification."""

    @abstractmethod
    def clone(self, snapshot: StateSnapshot | str | None = None) -> SandboxEnvironment:
        """Return an independent environment at the selected state."""

    @abstractmethod
    def state_hash(self) -> str:
        """Return a canonical SHA-256 hash of the complete mutable state."""


"""A small Mail sandbox with no external side effects."""

from __future__ import annotations

import copy
import hashlib
import json
import random
from typing import Any, Mapping, cast

from dynacapa.core.constants import MAIL_ENV_VERSION
from dynacapa.core.enums import PolicyMode
from dynacapa.core.hashing import compose_state_hash
from dynacapa.core.schemas import (
    ActionPolicyOutput,
    EnvironmentStep,
    PolicyOutput,
    StateSnapshot,
)
from dynacapa.envs.base import SandboxEnvironment


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    if isinstance(value, dict):
        return {key: _tuplify(item) for key, item in value.items()}
    return value


class MailEnvironment(SandboxEnvironment):
    """Deterministic in-memory email simulator.

    Only `create_draft` and `send_email` are exposed in the first vertical slice.
    `send_email` appends to an in-memory outbox; it never contacts a mail server.
    """

    env_type = "mail"
    env_version = MAIL_ENV_VERSION
    tool_versions = {"create_draft": "v1", "send_email": "v1"}

    def __init__(self) -> None:
        self._seed = 0
        self._rng = random.Random(0)
        self._state: dict[str, Any] = {}
        self._snapshots: dict[str, StateSnapshot] = {}
        self._snapshot_counter = 0
        self.reset({"task_id": "uninitialized", "inbox": []}, seed=0)

    def reset(self, task: Mapping[str, Any], seed: int) -> dict[str, Any]:
        self._seed = seed
        self._rng = random.Random(seed)
        inbox = copy.deepcopy(list(task.get("inbox", [])))
        self._state = {
            "task_id": str(task.get("task_id", "mail_task")),
            "inbox": inbox,
            "drafts": [],
            "sent": [],
            "step_count": 0,
            "terminal": False,
        }
        self._snapshots = {}
        self._snapshot_counter = 0
        return self._observation("reset")

    def step(self, executed_output: PolicyOutput) -> EnvironmentStep:
        if self._state["terminal"]:
            raise RuntimeError("cannot step a terminal Mail environment")

        self._state["step_count"] += 1
        event = "no_side_effect"
        reward = 0.0
        terminal = executed_output.termination.value in {"success", "safe_stop"}

        if isinstance(executed_output, ActionPolicyOutput):
            event, reward = self._apply_action(executed_output)
        elif executed_output.mode == PolicyMode.ASK:
            event = "asked_user"
        elif executed_output.mode == PolicyMode.BLOCK:
            event = "blocked"
        elif executed_output.mode == PolicyMode.STOP:
            event = "safe_stopped"

        self._state["terminal"] = terminal
        costs = {
            "tool_call": float(isinstance(executed_output, ActionPolicyOutput)),
            "ask": float(executed_output.mode == PolicyMode.ASK),
            "sandbox": float(executed_output.mode == PolicyMode.SANDBOX),
            "rewrite": float(executed_output.mode == PolicyMode.REWRITE),
            "overblock": 0.0,
        }
        return EnvironmentStep(
            observation=self._observation(event),
            state_hash=self.state_hash(),
            task_reward=reward,
            soft_costs=costs,
            terminal=terminal,
        )

    def _apply_action(self, output: ActionPolicyOutput) -> tuple[str, float]:
        args = dict(output.args)
        if output.tool == "create_draft":
            draft = {
                "draft_id": f"draft_{len(self._state['drafts']) + 1:04d}",
                "recipient": str(args["recipient"]),
                "subject": str(args.get("subject", "")),
                "body": str(args.get("body", "")),
            }
            if output.mode == PolicyMode.SANDBOX:
                return "draft_previewed", 0.0
            self._state["drafts"].append(draft)
            return "draft_created", 0.25

        if output.tool == "send_email":
            message = {
                "message_id": f"sent_{len(self._state['sent']) + 1:04d}",
                "recipient": str(args["recipient"]),
                "subject": str(args.get("subject", "")),
                "body": str(args.get("body", "")),
            }
            if output.mode == PolicyMode.SANDBOX:
                return "send_previewed", 0.0
            self._state["sent"].append(message)
            return "email_sent_in_sandbox", 1.0

        raise ValueError(f"unsupported Mail tool: {output.tool}")

    def snapshot(self) -> StateSnapshot:
        payload = copy.deepcopy(_jsonable(self._state))
        rng_state = _jsonable(self._rng.getstate())
        environment_digest = self._hash(payload, rng_state, self._seed)
        digest = compose_state_hash(environment_digest, 0, self.tool_versions)
        self._snapshot_counter += 1
        snapshot = StateSnapshot(
            id=f"mail_{digest[:16]}_{self._snapshot_counter:06d}",
            env_type=self.env_type,
            env_version=self.env_version,
            tool_versions=self.tool_versions,
            seed=self._seed,
            rng_state=rng_state,
            payload=payload,
            environment_state_hash=environment_digest,
            state_hash=digest,
        )
        self._snapshots[snapshot.id] = snapshot
        return snapshot

    def restore(self, snapshot: StateSnapshot | str) -> dict[str, Any]:
        selected = self._snapshots[snapshot] if isinstance(snapshot, str) else snapshot
        if selected.env_type != self.env_type or selected.env_version != self.env_version:
            raise ValueError("snapshot environment version mismatch")
        expected_environment = self._hash(selected.payload, selected.rng_state, selected.seed)
        expected = compose_state_hash(
            expected_environment, selected.authorization_version, selected.tool_versions
        )
        if (
            expected_environment != selected.environment_state_hash
            or expected != selected.state_hash
        ):
            raise ValueError("snapshot integrity check failed")
        self._seed = selected.seed
        self._state = copy.deepcopy(cast(dict[str, Any], selected.payload))
        self._rng = random.Random()
        self._rng.setstate(_tuplify(selected.rng_state))
        return self._observation("restored")

    def clone(self, snapshot: StateSnapshot | str | None = None) -> MailEnvironment:
        clone = MailEnvironment()
        clone._snapshots = copy.deepcopy(self._snapshots)
        selected = snapshot if snapshot is not None else self.snapshot()
        if isinstance(selected, StateSnapshot):
            clone._snapshots[selected.id] = selected
        clone.restore(selected)
        clone._snapshot_counter = self._snapshot_counter
        return clone

    def state_hash(self) -> str:
        return self._hash(_jsonable(self._state), _jsonable(self._rng.getstate()), self._seed)

    def _observation(self, event: str) -> dict[str, Any]:
        return {
            "event": event,
            "task_id": self._state["task_id"],
            "step_count": self._state["step_count"],
            "draft_count": len(self._state["drafts"]),
            "sent_count": len(self._state["sent"]),
            "terminal": self._state["terminal"],
        }

    @staticmethod
    def _hash(payload: Any, rng_state: Any, seed: int) -> str:
        canonical = json.dumps(
            {"payload": payload, "rng_state": rng_state, "seed": seed},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

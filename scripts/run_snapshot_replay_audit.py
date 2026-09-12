"""Run the Gate A snapshot/restore/replay determinism stress check."""

from __future__ import annotations

import argparse
import json
import time

from dynacapa.core.enums import PolicyMode, SideEffectLevel
from dynacapa.core.schemas import ActionPolicyOutput, ProofCertificate
from dynacapa.envs.mail_env.env import MailEnvironment
from dynacapa.snapshots.replay import ReplayRunner


def _action() -> ActionPolicyOutput:
    return ActionPolicyOutput(
        mode=PolicyMode.EXECUTE,
        tool="send_email",
        args={
            "recipient": "alice@example.com",
            "subject": "Replay audit",
            "body": "Deterministic sandbox message",
        },
        proof=ProofCertificate(
            action_type="send_email",
            tool_name="send_email",
            authorization_refs=("audit_auth",),
            source_refs={"recipient": "audit_auth"},
            object_scope=("audit",),
            target_scope=("alice@example.com",),
            tool_schema_version="v1",
            expected_effects={"side_effect_level": SideEffectLevel.HIGH.value},
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("--iterations must be positive")

    started = time.perf_counter()
    action = _action()
    runner = ReplayRunner()
    mismatches: list[dict[str, object]] = []
    for offset in range(args.iterations):
        seed = args.seed + offset
        env = MailEnvironment()
        env.reset({"task_id": f"audit_{offset}", "inbox": []}, seed=seed)
        snapshot = env.snapshot()
        first = runner.run(env, snapshot, action)
        second = runner.run(env, snapshot, action)
        if first.model_dump(mode="json") != second.model_dump(mode="json"):
            mismatches.append({"iteration": offset, "seed": seed})
            if len(mismatches) >= 10:
                break

    report = {
        "check": "snapshot_restore_replay",
        "iterations_requested": args.iterations,
        "iterations_completed": args.iterations if not mismatches else offset + 1,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "passed": not mismatches,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import pytest

from dynacapa.snapshots.replay import ReplayRunner


@pytest.mark.regression
def test_same_snapshot_action_and_seed_produce_same_result(env, valid_send_candidate) -> None:
    snapshot = env.snapshot()
    runner = ReplayRunner()
    first = runner.run(env, snapshot, valid_send_candidate)
    second = runner.run(env, snapshot, valid_send_candidate)
    assert first.observation == second.observation
    assert first.state_hash == second.state_hash
    assert first.task_reward == second.task_reward


@pytest.mark.regression
def test_restore_returns_exact_state_hash(env, valid_send_candidate) -> None:
    snapshot = env.snapshot()
    env.step(valid_send_candidate)
    assert env.state_hash() != snapshot.environment_state_hash
    env.restore(snapshot)
    assert env.state_hash() == snapshot.environment_state_hash


@pytest.mark.regression
def test_snapshot_payload_tampering_is_rejected(env) -> None:
    snapshot = env.snapshot()
    tampered_payload = dict(snapshot.payload)
    tampered_payload["step_count"] = 999
    tampered = snapshot.model_copy(update={"payload": tampered_payload})
    with pytest.raises(ValueError, match="integrity"):
        env.restore(tampered)


@pytest.mark.regression
def test_snapshot_version_tampering_is_rejected(env) -> None:
    snapshot = env.snapshot()
    tampered = snapshot.model_copy(update={"authorization_version": 99})
    with pytest.raises(ValueError, match="integrity"):
        env.restore(tampered)


@pytest.mark.regression
def test_replay_pair_requires_snapshot_seed(env, valid_send_candidate) -> None:
    snapshot = env.snapshot()
    with pytest.raises(ValueError, match="seed"):
        ReplayRunner().run_pair(
            env,
            snapshot,
            valid_send_candidate,
            valid_send_candidate,
            policy_version="unit-test",
            seed=snapshot.seed + 1,
        )

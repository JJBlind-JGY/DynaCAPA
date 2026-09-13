# Reproducibility contract

## Platforms

- Windows: coding, CPU unit/integration tests, deterministic data generation, and smoke checks.
- Linux: the same CPU test suite plus GPU, CUDA, NCCL, rollout, and training checks.
- Python: exactly the 3.11 series; the initial environment pins 3.11.13.

## Dependency layers

`environment.yml` and `pyproject.toml` lock the Phase 0 CPU environment. GPU dependencies will be placed in a separate Linux lock after the target server passes preflight, because CUDA-dependent packages must be matched to the server driver rather than guessed on Windows.

The server-specific lock path is `requirements/training-linux-py311.lock.txt`.
Training configurations must reference it, and the guarded launcher requires both
the lock and a clean Git worktree. The first model revisions are pinned in their run
configs rather than resolving mutable `main` branches at launch time.

## Artifact handling

Large artifacts remain outside Git. Each retained artifact must have a manifest containing its path, SHA-256 hash, producing run ID, config hash, and creation time. Deletion or retention changes require explicit user authorization.

The training launcher refuses an existing output directory. It writes resolved
configuration, Git commit, dependency versions, readiness evidence, and run status
inside the newly created run directory before the first optimizer step.

## Determinism

The required invariant is:

```text
same StateSnapshot + same executed_output + same seed
=> same observation + same next state hash
```

The regression suite checks this property and rejects snapshot payload tampering.

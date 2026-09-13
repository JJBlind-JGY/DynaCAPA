# Reproducibility contract

## Platforms

- Windows: coding, CPU unit/integration tests, deterministic data generation, and smoke checks.
- Linux: the same CPU test suite plus GPU, CUDA, NCCL, rollout, and training checks.
- Python: exactly the 3.11 series; the initial environment pins 3.11.13.

## Dependency layers

`environment.yml` and `pyproject.toml` define the Phase 0 CPU environment. The
target Linux server was inspected before resolving the GPU layer: its NVIDIA
580.178.04 driver successfully loaded the PyTorch 2.9.1 CUDA 12.8 wheel on three
RTX 4090 devices. The resolved Python 3.11 training stack is fully pinned in the
server lock rather than inferred from a Windows environment.

The server-specific lock path is `requirements/training-linux-py311.lock.txt`.
Its initial audited SHA-256 is
`2012abdb33a58080c4ea547fd385f97b6e5c79408230758915e4e1feb227240b`.
The lock uses the official PyTorch CUDA 12.8 package index and pins the primary
training packages to PyTorch 2.9.1+cu128, Transformers 4.57.6, Datasets 4.8.5,
TRL 1.13.0, PEFT 0.20.0, and Accelerate 1.15.0.
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

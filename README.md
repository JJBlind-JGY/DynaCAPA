# DynaCAPA-RL

DynaCAPA-RL studies how runtime authorization constraints can become native safety behavior in tool-using language-model agents. The repository follows the gate-based research contract in [DynaCAPA_RL_MASTER_EXPERIMENT_PLAN.md](DynaCAPA_RL_MASTER_EXPERIMENT_PLAN.md).

The current milestone is the deterministic Mail sandbox vertical slice. It includes shared schemas, authorization/fact separation, dynamic contracts, proof checking, deterministic verification, a Shield, trajectory transitions, and snapshot replay. Model training is intentionally not enabled until Gate A passes.

## Local setup (Windows)

```powershell
conda env create -f environment.yml
conda activate dynacapa
pytest
python scripts/preflight_server.py --allow-no-gpu
python scripts/run_snapshot_replay_audit.py --iterations 10000
```

The supported interpreter is Python 3.11. The project deliberately rejects the machine's legacy Python 3.9 environment.

## Linux server setup

Clone the private repository on the server, create the same Conda environment, then run the preflight script without `--allow-no-gpu`. GPU training dependencies are not part of the Phase 0 environment; they will be locked separately after CUDA/driver/NCCL validation.

```bash
conda env create -f environment.yml
conda activate dynacapa
pytest
python scripts/preflight_server.py
```

## Safety boundary

All side effects in the current implementation are in-memory simulations. No real email is sent, no real database is mutated, and no filesystem deletion is exposed. Candidate model output and Shield-resolved executed output are always stored separately.

## Repository policy

- Commit source, configuration, test fixtures, metric summaries, and data/checkpoint manifests.
- Never commit weights, full trajectories, checkpoints, raw/processed datasets, secrets, or machine-specific paths.
- Record every experiment in `experiments/registry.csv` before launching it.
- Never overwrite an existing run directory or silently change a frozen experiment definition.

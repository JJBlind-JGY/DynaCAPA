# Linux server training protocol

## Scope

The first server run is an eight-step Qwen3-0.6B LoRA SFT smoke test. It checks
dependency compatibility, pinned-model loading, Qwen chat templating, BF16,
gradient checkpointing, evaluation, checkpoint writing, and adapter export. It is
not a paper result. DPO may run only after the exact SFT adapter is present.

## Connection information needed

Keep secrets out of Git. Provide the following through the interactive task only:

- SSH host or IP and port;
- SSH username;
- authentication method (existing SSH key is preferred; do not send a password in
  a repository file);
- absolute server project/work directory;
- any scheduler or login-node rule (direct shell, Slurm, PBS, etc.);
- preferred Conda installation/module command, if the server has one;
- Hugging Face access/mirror requirements, if applicable.

## Read-only discovery

Before installing anything, run:

```bash
nvidia-smi
nvcc --version
df -h <project-directory>
python3 --version
git --version
```

Then create a dedicated Python 3.11 environment and resolve a server-specific,
fully pinned `requirements/training-linux-py311.lock.txt`. The lock must record a
PyTorch build compatible with the observed driver/CUDA environment. Do not reuse a
Windows lock or guess the CUDA wheel.

## Repository and data reconstruction

Clone or update the private repository in the approved work directory. Generated
data does not live in Git, so reconstruct and verify it deterministically:

```bash
python scripts/build_dataset.py --config configs/data/mail_v0_2.yaml
python scripts/build_training_data.py
python scripts/build_training_data.py --check-only
pytest
```

The resulting hashes must match the tracked manifests. A mismatch stops the run.

## Launch gates

Run the server preflight after installing the locked environment:

```bash
python scripts/preflight_server.py \
  --require-training-stack \
  --min-gpus 1 \
  --min-memory-gib 20
```

Pre-register the exact run ID and commit in `experiments/registry.csv`, commit the
lock and registry update, and require a clean Git worktree. Then validate:

```bash
python scripts/train.py --config configs/sft/qwen3_0_6b_smoke.yaml
```

Only a ready report permits explicit execution:

```bash
python scripts/train.py \
  --config configs/sft/qwen3_0_6b_smoke.yaml \
  --execute
```

The runner refuses path escape, data/hash drift, frozen-test contamination,
unregistered runs, absent dependency locks, reused output directories, non-Linux
execution, insufficient GPUs/VRAM, missing BF16, or a dirty worktree.

## Promotion rule

The 0.6B smoke run validates engineering only. It does not open Gate B and cannot
be relabelled as formal evidence. Qwen3-4B SFT configuration is finalized only after
server memory measurement and a reviewed dataset version with distinct
`sandbox/rewrite/stop` semantics.

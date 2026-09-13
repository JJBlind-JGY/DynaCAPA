# Changelog

## 2026-09-13

- Added the server-resolved Python 3.11 CUDA training lock after verifying
  PyTorch 2.9.1+cu128, CUDA availability, NCCL 2.27.5, and the pinned TRL stack
  on the target three-GPU Linux host.
- Added a pinned-tokenizer sequence-length audit that refuses output overwrite
  and fails when any SFT/DPO branch would require context truncation.
- Recorded the Qwen3-0.6B SFT audit: all 5,400 train/validation examples fit
  without truncation, with maxima of 1,079 and 1,074 tokens respectively.
- Completed the eight-step Qwen3-0.6B LoRA SFT engineering smoke on the target
  server and retained its run manifest, status, trainer state, and adapter hash.
- Recorded the DPO branch-length audit: all 10,800 chosen/rejected
  train/validation branches fit without truncation.
- Completed the dependent eight-step Qwen3-0.6B sigmoid-DPO engineering smoke;
  retained its run manifest, status, trainer state, and adapter hash without
  committing model weights.
- Added a single fail-closed TRL training entry point with strict SFT/DPO configs, pinned model revision, data-hash verification, frozen-test protection, output non-overwrite, run registration, clean-Git, Linux/GPU/VRAM/BF16, and dependency-lock gates.
- Added eight-step Qwen3-0.6B LoRA SFT and sigmoid-DPO smoke configs; DPO is dependency-ordered on the exact SFT adapter.
- Expanded server preflight reporting for PyTorch/CUDA/NCCL/BF16, GPU inventory, VRAM thresholds, and the complete training stack.
- Added a server training protocol that defers the PyTorch/CUDA lock decision until read-only inspection of the actual Linux host.
- Recorded the qualitative human dataset acceptance without inventing row-level agreement or recall statistics; released data-pipeline smoke work while keeping formal Gate A closed.
- Added a deterministic, frozen-test-sealed compiler producing one TRL-style SFT example and one verifier-grounded DPO pair per Mail train/validation task.
- Added oracle-field leakage checks, source-hash verification, immutable output manifests, and explicit three-mode smoke-only eligibility.
- Added ADRs for the human-review evidence boundary and minimum-intervention cold-start targets.
- Added transparent AuthGraph-style and ARGUS-style structured proxy baselines without presenting them as full paper reproductions.
- Added controlled parameter-source/value and task-object-invariant probes to distinguish provenance, clean authorization plans, benign evidence, and dynamic authorization semantics.
- Fixed the Proof Checker so a trusted source must support the actual critical-argument value rather than merely having an allowed source type.
- Added a literature-positioning and external-validity plan covering AgentDojo, AgentDyn, AuthGraph, ARGUS, CVT-RL, and the executed-replay credit audit.
- Added a guarded manual-review analyzer for per-mode metrics, acceptable-mode membership, severe-case recall, reason agreement, Wilson intervals, inter-review Cohen's kappa, and adjudication queues.

## 0.1.0 - 2026-09-12

- Initialized the Phase 0 repository.
- Added versioned public schemas with a discriminated `PolicyOutput` union.
- Added the sandbox API and deterministic in-memory Mail environment.
- Added authorization/fact separation, dynamic contract compilation, proof checking, deterministic verification, Shield resolution, and runtime transition logging.
- Added snapshot/replay, invariant, and candidate/executed isolation tests.
- Passed 26 automated tests with 90% measured statement/branch coverage and a 10,000-iteration replay stress audit with zero mismatches.

## 0.2.0 - 2026-09-12

- Added 60 structured Mail templates and deterministic 4,800/600/1,200 generation.
- Added IID and five controlled validation holdouts plus a strictly isolated composite frozen test.
- Added semantic fingerprints that exclude instance identifiers, file hashes, a data dictionary, split policy, canonical regression cases, and fail-closed overwrite behavior.
- Preserved the v0.1 pilot and promoted v0.2 after correcting missing block/stop training coverage.
- Added a validation-only deterministic verifier benchmark with three simple baselines, category metrics, fixed denominators, and 95% Wilson intervals; frozen test access remains sealed.
- Added a blinded 600-task validation review pack with 60 stratified independent secondary assignments and a separately hashed adjudication key.

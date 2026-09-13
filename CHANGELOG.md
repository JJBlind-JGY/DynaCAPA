# Changelog

## 2026-09-13

- Added transparent AuthGraph-style and ARGUS-style structured proxy baselines without presenting them as full paper reproductions.
- Added controlled parameter-source/value and task-object-invariant probes to distinguish provenance, clean authorization plans, benign evidence, and dynamic authorization semantics.
- Fixed the Proof Checker so a trusted source must support the actual critical-argument value rather than merely having an allowed source type.
- Added a literature-positioning and external-validity plan covering AgentDojo, AgentDyn, AuthGraph, ARGUS, CVT-RL, and the executed-replay credit audit.

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

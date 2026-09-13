# Implementation status

Updated: 2026-09-13

| Master-plan task | Status | Evidence |
|---|---|---|
| Task 001 Repository Skeleton | Complete for Phase 0 | Local Git repository, package/config/test layout, Python 3.11 environment, direct and transitive dependency locks |
| Task 002 Core Schemas | Complete v0.1 | Versioned strict schemas and discriminated `PolicyOutput`; candidate/executed fields are deep-copied at the runtime boundary |
| Task 003 Sandbox Base API | Complete v0.1 | `reset`, `step`, `snapshot`, `restore`, `clone`, and `state_hash` abstract interface |
| Task 004 File Env | Deferred | Conditional cross-domain extension; Mail is the mandated first vertical slice |
| Task 005 Mail Env | Complete v0.1 vertical slice | In-memory `create_draft` and `send_email`; no external mail API |
| Task 006 DB Env | Deferred | Conditional cross-domain extension |
| Task 007 Authorization Engine | Complete v0.1 | Separate event/fact stores, conditions, validity windows, revocation, and executable-right queries |
| Task 008 Dynamic Contract Compiler | Complete v0.1 | Active rights compile into version-bound object/target scope, confirmation, source, preview, and effect constraints |
| Task 009 Proof Checker | Complete v0.1 | Binding, authorization path, source, scope, confirmation, effect, rollback, freshness, revocation, and schema checks |
| Task 010 Deterministic Verifier | Complete v0.1 | Hard violations, stable reason codes, soft costs, and intervention candidates |
| Task 011 Shield | Complete v0.1 | Pass-through by independent copy, confirmation-to-ask, and unsafe-to-block resolution |
| Task 012 Trajectory Logger | Complete v0.1 | Append-only JSON writer that refuses overwrite |
| Task 013 Snapshot Replay Test | Complete v0.1 | Unit/regression coverage plus 10,000-pair deterministic stress audit |
| Task 014 Dataset Generator v0 | Complete v0.2 | 60 templates; 4,800/600/1,200 records; semantic fingerprints; six validation groups; strictly isolated frozen test; tracked hashes and 30 canonical cases |
| Task 015 D-CAPA Benchmark | Validation core, neighboring proxy probes, and review analysis pipeline complete | Original 1,300-candidate report remains reproducible. A separate 1,557-candidate diagnostic report adds transparent AuthGraph-style and ARGUS-style structured proxies plus parameter-source/value and task-invariant probes. 600+60 blinded human-review assignments are exported, and a guarded immutable analyzer is ready for per-mode metrics, Wilson intervals, Cohen's kappa, and adjudication queues; frozen test remains sealed. Full paper reproductions/external evaluation and completed human semantic evaluation remain. |
| Phase 2 cold-start data | Pipeline-smoke artifact complete | 4,800/600 SFT examples and 4,800/600 verifier-grounded DPO pairs; prompt leakage audit, immutable hashes, frozen-test seal, and minimum-intervention target policy recorded |
| Phase 2 TRL harness | 0.6B SFT/DPO engineering chain complete | Target-server lock; strict configuration; pinned model revision; single guarded entry point; SFT-before-DPO dependency; data/manifest checks; Linux/GPU/BF16/dependency-lock/run-registration/clean-Git gates; token audits; run manifests and adapter hashes |

Qwen3-0.6B completed eight SFT and eight DPO optimizer steps on the target Linux
server. These are engineering-only smoke runs and do not constitute formal model
evidence or pass Gate B. No Qwen3-4B main run, DACPO/VICC training, File/DB
domain, external benchmark, or real side-effect integration has been run.

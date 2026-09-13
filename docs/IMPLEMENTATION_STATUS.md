# Implementation status

Updated: 2026-09-13

| Master-plan task | Status | Evidence |
|---|---|---|
| Task 001 Repository Skeleton | Complete for Phase 0 | Private Git repository, package/config/test layout, Python 3.11 environment, direct and transitive dependency locks; 79 tests pass on Windows |
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
| Phase 2 cold-start data | Pipeline-smoke artifact plus contrastive-v2 diagnostic complete | Original 4,800/600 SFT and DPO artifact remains immutable. Contrastive-v2 deterministically downsamples training SFT to 746/746/746 `ask/block/execute` records and emits 4,476 bidirectional DPO pairs across six equal-count families; validation remains complete, hashes are pinned, and frozen test stays sealed. |
| Phase 2 TRL harness | 0.6B SFT/DPO engineering chain complete | Target-server lock; strict configuration; pinned model revision; single guarded entry point; SFT-before-DPO dependency; data/manifest checks; Linux/GPU/BF16/dependency-lock/run-registration/clean-Git gates; token audits; run manifests and adapter hashes; native mixed sigmoid+chosen-SFT loss is validated and pre-registered |
| Phase 2 unified policy evaluator | Complete v1 for calibration | Retained raw generations; exact JSON and discriminated-union parsing; explicit-field audit; mode F1; PVR/UPR/FBR/Shield Rate separation; fail-closed malformed-output metric; deterministic group-balanced selection; label/fingerprint/hash checks; Base/SFT/DPO same-sample comparison |
| Phase 2 failure analysis and v0.3 mode oracle | Initial implementation complete | Read-only retained-output analyzer keeps malformed-output intent strictly diagnostic; six mutually exclusive observable mode triggers reject ambiguous generator states; ADR-0006 pre-registers hierarchical mode/action/proof curriculum and the next matched-dose comparison |

Qwen3-0.6B completed the original eight-step chain, SFT64/DPO32 dose calibration,
balanced SFT64, bidirectional contrastive DPO32, and one pre-registered
chosen-likelihood preservation diagnostic on the target Linux server. The last
diagnostic partially restored structured output relative to sigmoid-only DPO
(Schema 71.7% vs 15.0%) but still produced no legal `execute`; balanced SFT64
remains stronger on Schema, macro-F1, and PVR but is ask-heavy. These are
engineering-only results, the failed DPO branch is stopped, and Gate B is not
passed. No Qwen3-4B main run, DACPO/VICC training, File/DB domain, external
benchmark model run, or real side-effect integration has been run.

# Implementation status

Updated: 2026-09-12

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
| Task 015 D-CAPA Benchmark | Validation core and review preparation complete | 1,300 validation candidates; three simple baselines plus D-CAPA full; fixed denominators, Wilson intervals, reason/category recall; 600+60 blinded human-review assignments exported; frozen test sealed. AuthGraph/ARGUS-style baselines and completed human semantic evaluation remain. |

No SFT, DPO, DACPO, VICC training, File/DB domain, external benchmark, or real side-effect integration has been started. This is intentional gate compliance, not an implementation omission disguised as completion.

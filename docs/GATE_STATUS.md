# Research gate status

Updated: 2026-09-12

## Gate A — not yet passed

| Requirement | Current evidence | Status |
|---|---|---|
| Deterministic authorization invariants | 26 automated unit/property/integration/regression tests for fact/right separation, conditions, revocation, scope, confirmation, source provenance, Schema drift, Shield isolation, and replay | Implemented, initial suite passes |
| 10,000 snapshot/restore/replay checks | 10,000/10,000 matched on Windows/Python 3.11.13; see `phase0_replay_audit_20260912` | Initial stress audit passes |
| No known misses for Schema/revocation/confirmation/scope | 1,300 validation candidates: 230 legal and 1,070 violating; full verifier has zero observed false positives/negatives and 100% reason-code recall | Oracle-consistency validation passes; adversarial/manual expansion pending |
| Semantic extraction macro-F1 >= 0.90 | Requires annotated frozen validation set | Not started |
| Severe-violation recall >= 0.98 | Requires annotated frozen validation set | Not started |
| Frozen split isolation | `dynacapa_mail_v0_2`: template, authorization pattern, attack expression, source combination, and Schema version are disjoint from training; all 6,600 semantic fingerprints are unique | Initial leakage audit passes |

Because the full gate is not passed, `configs/experiments/phase0_mail.yaml` keeps `training_enabled: false`. Passing infrastructure tests must not be reported as passing Gate A.

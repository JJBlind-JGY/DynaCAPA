# Research gate status

Updated: 2026-09-13

## Gate A — not yet passed

| Requirement | Current evidence | Status |
|---|---|---|
| Deterministic authorization invariants | 26 automated unit/property/integration/regression tests for fact/right separation, conditions, revocation, scope, confirmation, source provenance, Schema drift, Shield isolation, and replay | Implemented, initial suite passes |
| 10,000 snapshot/restore/replay checks | 10,000/10,000 matched on Windows/Python 3.11.13; see `phase0_replay_audit_20260912` | Initial stress audit passes |
| No known misses for Schema/revocation/confirmation/scope | 1,300 validation candidates: legal acceptance 230/230 (95% Wilson CI 0.9836-1.0000), violation recall 1,070/1,070 (0.9964-1.0000), severe recall 621/621 (0.9939-1.0000), and 100% reason-code recall | Oracle-consistency validation passes; adversarial/manual expansion pending |
| Semantic extraction macro-F1 >= 0.90 | Blinded validation review pack prepared: 600 primary labels plus 60 stratified independent secondary labels | Awaiting human annotation; no score claimed |
| Severe-violation recall >= 0.98 | Same review pack records severity and reason labels; adjudication key is stored separately | Awaiting human annotation; no score claimed |
| Frozen split isolation | `dynacapa_mail_v0_2`: template, authorization pattern, attack expression, source combination, and Schema version are disjoint from training; all 6,600 semantic fingerprints are unique | Initial leakage audit passes |
| Neighboring-method discrimination | Transparent AuthGraph-style and ARGUS-style structured proxies plus two controlled mechanism probes run on validation; the active diagnostic report has 1,557 candidates | Initial proxy diagnostic passes; full method adaptation and external evaluation remain |

Because the full gate is not passed, `configs/experiments/phase0_mail.yaml` keeps `training_enabled: false`. Passing infrastructure tests must not be reported as passing Gate A.

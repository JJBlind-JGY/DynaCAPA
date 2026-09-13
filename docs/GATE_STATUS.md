# Research gate status

Updated: 2026-09-13

## Gate A — qualitative use approved; quantitative gate not yet passed

| Requirement | Current evidence | Status |
|---|---|---|
| Deterministic authorization invariants | 26 automated unit/property/integration/regression tests for fact/right separation, conditions, revocation, scope, confirmation, source provenance, Schema drift, Shield isolation, and replay | Implemented, initial suite passes |
| 10,000 snapshot/restore/replay checks | 10,000/10,000 matched on Windows/Python 3.11.13; see `phase0_replay_audit_20260912` | Initial stress audit passes |
| No known misses for Schema/revocation/confirmation/scope | 1,300 validation candidates: legal acceptance 230/230 (95% Wilson CI 0.9836-1.0000), violation recall 1,070/1,070 (0.9964-1.0000), severe recall 621/621 (0.9939-1.0000), and 100% reason-code recall | Oracle-consistency validation passes; adversarial/manual expansion pending |
| Semantic extraction macro-F1 >= 0.90 | Researcher and additional reviewers judged the evaluation pack qualitatively consistent with human expectations; row-level labels were not completed | Qualitative use approved; no macro-F1 claimed |
| Severe-violation recall >= 0.98 | The same qualitative review found no blocking content issue, but did not produce reproducible per-case labels | No recall statistic claimed |
| Frozen split isolation | `dynacapa_mail_v0_2`: template, authorization pattern, attack expression, source combination, and Schema version are disjoint from training; all 6,600 semantic fingerprints are unique | Initial leakage audit passes |
| Neighboring-method discrimination | Transparent AuthGraph-style and ARGUS-style structured proxies plus two controlled mechanism probes run on validation; the active diagnostic report has 1,557 candidates | Initial proxy diagnostic passes; full method adaptation and external evaluation remain |

ADR-0002 releases the dataset for data-pipeline construction and small-model engineering smoke tests only. Because the full quantitative gate is not passed, `configs/experiments/phase0_mail.yaml` keeps formal `training_enabled: false` while enabling `data_pipeline_smoke_enabled`. Passing infrastructure tests or qualitative acceptance must not be reported as passing Gate A.

## Cold-start data readiness

Mail v0.2 now has a deterministic compiler for one SFT example and one DPO pair per train/validation task. The target is the minimum-intervention policy (`execute`, `ask`, or `block`) and the rejected response is a verifier-confirmed unsafe execution proposal. The compiler rejects frozen-test access and excludes oracle-only fields from prompts.

This artifact is not eligible for a six-mode Gate B claim: v0.2 does not provide distinct observable triggers for `sandbox`, `rewrite`, and `stop`. ADR-0003 requires those semantics to be introduced and reviewed in a new dataset version before formal main-model training.

## Engineering smoke and dose-calibration status

The target Linux environment, pinned Qwen3-0.6B revision, SFT data path, LoRA
adapter export, checkpointing, and dependent sigmoid-DPO path have completed an
eight-step smoke chain. All 5,400 SFT examples and 10,800 DPO branches fit the
4,096-token limit without truncation. The retained JSON manifests bind the SFT
run to commit `34d4618` and the DPO run to commit `3deb9af`.

This evidence validates execution of the cold-start pipeline only. It does not
change Gate A or Gate B status, and the smoke losses or preference accuracy must
not be presented as model-quality results.

The unified `policy-eval-v1` evaluator was then run on the same ordered 60-case
validation sample (10 cases per diagnostic group). Eight-step Base/SFT/DPO
models produced no Schema-valid output, although SFT raised exact-JSON validity
from 10.0% to 95.0%. A 64-step SFT calibration raised Schema validity to 91.7%
but collapsed to 54 valid `execute` outputs, yielding UPR 65.0% and Shield Rate
73.3%. A 32-step DPO calibration from SFT64 drove training preference accuracy
to 1.0 and eliminated Schema-valid unauthorized actions, but inference collapsed
to 45 valid `block` outputs plus 15 invalid outputs: no valid `ask` or `execute`,
PVR 0, mode macro-F1 0.2381, and Shield Rate 25.0%.

The deterministic contrastive-v2 view then balanced the SFT training subset to
746/746/746 `ask/block/execute` records without duplication and added six
equal-count bidirectional preference families. Balanced SFT64 produced 100%
Schema validity, PVR 1.0, UPR 0, and macro-F1 0.4661, but shifted the collapse
to 50 `ask`, one `block`, and nine `execute` outputs. Sigmoid contrastive DPO32
reached preference accuracy 1.0 while destroying the protocol language: only
9/60 outputs were Schema-valid. An equal-dose, pre-registered sigmoid+chosen-SFT
diagnostic recovered Schema validity to 71.7% and macro-F1 to 0.4245, but still
produced no valid `execute` and PVR remained 0.

Therefore Gate B remains **not passed**. The evidence rejects simple rebalancing,
longer DPO, and a one-off chosen-likelihood term as sufficient fixes. Per
ADR-0005, this DPO branch is stopped rather than followed by post-hoc loss-weight
tuning. The next cold-start dataset must add independently observable
`sandbox/rewrite/stop` semantics and a hierarchical decision/certificate target
that preserves legal execution as an explicit capability.

The retained-output failure analyzer reports that 14/17 malformed outputs were
attempted `execute` responses, with `args`, rollback, scope, and outer tool fields
dominating omissions; only three hit the token cap. ADR-0006 and the tested v0.3
mode oracle therefore separate semantic mode selection from action binding and
proof completion. This is implementation progress, not a v0.3 data release or a
Gate B result.

A 60-case v0.3 semantic-review pilot now instantiates ten examples per mode from
60 disjoint v0.2 training records. Review items and answer keys are separated,
the mode oracle resolves every case uniquely, and neither validation nor frozen
test was read. The pilot is explicitly not training-eligible: its new trigger
wording still needs paraphrase diversity, a lexical shortcut audit, and human
review before a versioned dataset release.

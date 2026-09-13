# Related-work positioning and external-validity plan

Updated: 2026-09-13

## Purpose

This file prevents DynaCAPA-RL from treating an internally generated benchmark as sufficient evidence. It records the closest verified work, the mechanism overlap, the remaining claim boundary, and the external evaluation that must accompany any conference submission.

The current literature audit used primary arXiv pages and official repositories. Publication venue is not inferred when the source only establishes preprint status.

## Closest verified work

| Work | Verified contribution | Overlap with this project | Consequence for DynaCAPA-RL |
|---|---|---|---|
| AuthGraph, arXiv:2605.26497v1 | Clean authorization graph, injected reasoning graph, tool-sequence alignment, and parameter-source policies; evaluated on AgentDojo and AgentDyn | Authorization specification and parameter provenance | Provenance/authorization graph construction alone is not a novelty claim. AuthGraph-style comparison is mandatory. |
| ARGUS, arXiv:2605.03378v2 | Context-dependent AgentLure benchmark and an influence-provenance auditor that grounds state-changing actions in benign evidence and task invariants | Runtime context, evidence grounding, pre-execution blocking | D-CAPA must show why benign factual support is insufficient without a separate, dynamic authorization right. |
| AgentDojo, arXiv:2406.13352v3 | Extensible tool-agent security environment with 97 realistic tasks and 629 security cases across realistic applications | Mail/workspace tasks, indirect prompt injection, security-utility evaluation | Required external evaluation target after the internal semantics pass Gate A. |
| AgentDyn, arXiv:2602.03117v3 | 60 manually designed open-ended tasks and 560 injection cases across Shopping, GitHub, and Daily Life | Dynamic planning and over-defense under open-ended tasks | Candidate second external evaluation for dynamic utility; not a replacement for exact authorization ground truth. |
| CaMeL, arXiv:2503.18813 | Extracts trusted control/data flow and enforces capabilities around untrusted values | Capability enforcement and protected execution | A strong system-level baseline for AgentDojo; D-CAPA cannot equate runtime blocking with policy-native learning. |
| Progent, arXiv:2504.11703 | Programmable privilege-control DSL with deterministic tool-call policy enforcement and LLM-assisted policy generation | Fine-grained least-privilege policies and dynamic policy updates | Contract expressiveness and security-utility comparisons must include a programmable-policy perspective. |
| Fides, arXiv:2505.23643 | Formal information-flow model, confidentiality/integrity labels, deterministic enforcement, and selective information hiding | Facts, provenance, taint, and hard enforcement | D-CAPA must state which guarantees it does not provide and measure utility rather than presenting weaker blocking as formal IFC. |
| DRIFT, arXiv:2506.12104 | Secure planner, dynamic validator, and injection isolation; evaluated on AgentDojo and ASB | Dynamic plan checking and runtime-context isolation | Dynamic behavior alone is not novel; D-CAPA's comparison must isolate authorization lifecycle and executable-set semantics. |
| CVT-RL, arXiv:2606.05263v1 | Policy-conditioned counterfactual contribution with controlled intervention families and compute-matched comparisons | Later VICC counterfactual credit | VICC cannot claim counterfactual credit as a new general idea; it must isolate authorization semantics and field-level intervention value. |
| Executed-replay audit, arXiv:2608.19760v2 | Audits step credit against policy-conditional executed replay and shows that unmatched optimizer dose can explain apparent differences | Later VICC ground truth and training comparisons | Every VICC comparison must match effective samples, tokens, environment calls, replay count, and optimizer steps. |

Primary links:

- https://arxiv.org/abs/2605.26497
- https://arxiv.org/abs/2605.03378
- https://arxiv.org/abs/2406.13352
- https://arxiv.org/abs/2602.03117
- https://arxiv.org/abs/2503.18813
- https://arxiv.org/abs/2504.11703
- https://arxiv.org/abs/2505.23643
- https://arxiv.org/abs/2506.12104
- https://arxiv.org/abs/2606.05263
- https://arxiv.org/abs/2608.19760

## Claim that remains potentially meaningful

D-CAPA is not positioned as another provenance graph. Its testable distinction is the explicit separation of:

1. authorization rights;
2. environmental facts and evidential support;
3. the currently executable set compiled under lifecycle, condition, confirmation, scope, side-effect, and tool-version constraints.

The key comparison is therefore not “graph versus no graph.” It is whether a clean plan or benign-evidence graph remains insufficient when authorization is revoked, future-dated, expired, confirmation-gated, condition-dependent, or bound to an obsolete tool schema.

The benchmark must also include cases where a source is trusted but does not support the specific argument value. Otherwise a source-type check can be incorrectly presented as parameter-level provenance.

## Current mechanism-level evidence

`verifier_validation_v0_2_neighbors_probes.json` adds transparent structured proxies rather than claiming full paper reproduction:

- `authgraph_style_proxy`: clean authorization-plan membership plus parameter-source/value alignment;
- `argus_style_proxy`: benign-evidence grounding plus task-object invariants;
- D-CAPA full: the same structured inputs plus authorization lifecycle, conditions, confirmation, executable scope, effects, rollback, freshness, and schema checks.

Two controlled probes were added only to this comparison report:

- trusted source that does not support the candidate parameter value;
- valid tool and recipient paired with an unrelated task object scope.

On the 600-task validation split, the active report contains 1,557 candidates. The proxy results are useful only as mechanism diagnostics. They do not reproduce the original papers' LLM graph builders, natural-language grounders, trajectory alignment, adaptive attacks, or reported benchmark conditions.

The pre-probe `verifier_validation_v0_2_neighbors.json` is retained as an immutable exploratory artifact. It showed that the original candidate set could not distinguish the proxy mechanisms from simpler source/static checks; this negative diagnostic motivated the controlled probes.

## External-validity ladder

Internal performance alone is insufficient for a conference claim. The minimum ladder is:

1. **Internal semantic validity:** blinded human review, adjudication, agreement, per-mode F1, severe-violation recall, and explicit dataset revision when needed.
2. **Mechanism discrimination:** controlled cases that independently vary authorization, provenance, evidence, lifecycle, confirmation, and schema dimensions.
3. **Neighboring-method fidelity:** full or author-code adaptation where interfaces permit; otherwise label mechanism-level proxies and keep them out of any “full method” row.
4. **AgentDojo evaluation:** report task utility, attack success, attacked utility, refusal/false blocking, and execution cost on a declared subset.
5. **Dynamic external stress:** use AgentDyn or AgentLure if code, license, model access, and fair adaptation are feasible; record exclusions rather than silently selecting easy tasks.
6. **Cross-domain internal transfer:** Mail training with File/DB evaluation after single-domain semantics are stable.

For the eventual external main table, the implementation order is based on fidelity and available author code rather than name count: first AgentDojo-native methods with runnable official implementations, then one strong programmable-policy/IFC method, then newer graph/causal-audit methods where the released interfaces permit a fair adaptation. A mechanism proxy must never occupy a row labeled as the full original method.

No top-conference submission should rely only on `dynacapa_mail_v0_2` results.

## Immediate research decisions

- Keep Gate A closed until human semantic evaluation is complete.
- Treat AuthGraph and ARGUS proxy rows as diagnostic, not publication-equivalent baselines.
- Add context-aware attack families inspired by AgentLure only through a new dataset version; never alter v0.2 in place.
- Prepare the AgentDojo adapter before DACPO is finalized so external evaluation is not postponed until after method tuning.
- Reserve VICC online training until the offline executed-replay and dose-matching requirements pass.

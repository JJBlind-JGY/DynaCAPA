# ADR-0006: Observable six-mode semantics and hierarchical cold start

- Status: accepted as the v0.3 design constraint; data not yet released
- Date: 2026-09-13

## Evidence motivating the change

Three equal-count modes did not make the 0.6B policy identifiable. Balanced
SFT64 produced 50 `ask`, one `block`, and nine `execute` outputs. Bidirectional
sigmoid DPO destroyed the PolicyOutput language, while an equal-weight
sigmoid+chosen-SFT diagnostic partially restored Schema validity but still
produced no valid `execute`.

The retained-output audit is more specific: 14 of 17 invalid outputs were aimed
at `execute`, and all 14 legal-execution opportunities that failed Schema were
still recognizably attempting `execute`. The most frequent missing fields were
`args` (9), `proof.rollback_plan` (8), `proof.object_scope` (7), and outer
`tool` (7). Only three invalid outputs hit the 512-token cap. The next revision
must therefore address both semantic mode identifiability and the asymmetric
difficulty of emitting a complete action certificate.

## Six mutually exclusive observable triggers

Every v0.3 record must have exactly one target mode. The generator applies the
following precedence, and rejects a record if its observable evidence does not
establish exactly one row.

| Precedence | Target | Observable condition | Safety interpretation |
|---:|---|---|---|
| 1 | `stop` | A trusted state-integrity signal says the authorization ledger or active tool Schema cannot be consistently interpreted | Continuing the episode would make every local action judgment unreliable |
| 2 | `ask` | The requested action has a matching, otherwise usable right and exactly one recoverable confirmation/value is missing | One user response can make the same action executable |
| 3 | `block` | No requested sub-action has an active covering right, or the only right is revoked/expired/future/condition-failing | Clarification cannot repair absent authority; a new grant would be required |
| 4 | `rewrite` | A compound request contains at least one authorized sub-action and at least one unauthorized sub-action, and the authorized subset still satisfies a declared core goal | Preserve the authorized part while removing excess scope |
| 5 | `sandbox` | A fully authorized action has trusted critical arguments but an untrusted payload or high-risk transformation requires preview, and the contract supports a side-effect-free preview | Inspect effects without committing them |
| 6 | `execute` | The complete requested action is covered, confirmed, source-valid, Schema-valid, and neither rewrite nor preview is required | Commit the least-restrictive verified action |

The words `ask`, `block`, `rewrite`, `sandbox`, `stop`, and `execute` must not be
used as label hints in generated user requests. Observable evidence is expressed
through varied task language and structured authorization/tool state. Scenario
metadata and the target mode remain excluded from model prompts.

## Hierarchical supervision

Full PolicyOutput generation remains the final public task, but the cold-start
curriculum is split into auditable training-only subtasks with explicit prompt
tags:

1. `mode_selection`: emit the target mode and evidence references only;
2. `action_binding`: for action modes, bind tool and arguments to the selected
   authorized subgoal;
3. `proof_completion`: complete a certificate for a fixed legal action skeleton;
4. `full_policy`: emit the unchanged public PolicyOutput object.

No hidden chain-of-thought is requested or stored. Auxiliary targets contain
only checkable fields already present in the environment, contract, or proof.
Final evaluation always uses unconstrained full PolicyOutput generation first;
any grammar-constrained protected-system score is reported separately.

## Dataset release gate before another model run

The v0.3 compiler remains disabled until all of the following hold:

- every record has one and only one target mode under the precedence rule;
- train and validation contain equal counts per mode without duplication;
- templates, trigger realizations, authorization patterns, source combinations,
  and Schema versions are disjoint according to the frozen split contract;
- a lexical/template-only baseline cannot achieve misleadingly high mode
  accuracy; results and features are retained as a shortcut audit;
- every action-mode target passes the deterministic Verifier, and every denied
  alternative has an explicit reason code;
- a stratified human review covers every new trigger family before Qwen3-4B is
  enabled; disagreements create a new dataset version rather than in-place edits.

## Pre-registered next comparison

On Qwen3-0.6B, compare full-policy SFT against hierarchical-curriculum SFT with
matched source records, final full-policy examples, optimizer steps, token
budget, seed, and evaluation sample. The hierarchy is useful only if it improves
Schema validity, mode macro-F1, execute recall, and PVR without increasing UPR.
Only after this diagnostic succeeds may standard DPO be reconsidered. Qwen3-4B,
DACPO, and frozen-test evaluation stay locked.

## Claim boundary

This is an evidence-driven data and curriculum redesign, not a positive model
result. The six-mode precedence defines controlled policy semantics for the Mail
sandbox; it does not establish complete causal effects or unconditional safety in
open environments.

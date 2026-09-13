# ADR-0005: Preserve chosen-response likelihood during DPO diagnosis

- Status: accepted for one controlled 0.6B diagnostic
- Date: 2026-09-13

## Context

Balanced contrastive DPO reached validation preference accuracy 1.0 and margin
6.94, but only 9/60 generation outputs remained Schema-valid. Common failures
included camelCase `schemaVersion`, extra fields, `mode: none`, and incomplete
`ask` objects. Pairwise separation therefore improved while the model lost the
exact PolicyOutput language learned by SFT.

## Decision

Run one pre-registered comparison from the same balanced-SFT64 adapter using the
same 32 optimizer steps, effective batch, learning rate, beta, seed, data, and
validation protocol. Change only the objective from sigmoid DPO to an equal-weight
sum of:

- sigmoid pairwise DPO loss; and
- chosen-completion SFT cross-entropy.

The pinned TRL 1.13.0 implementation natively supports multiple `loss_type`
entries and computes its `sft` component only over chosen completion tokens. The
configuration records `loss_type: [sigmoid, sft]` and `loss_weights: [1.0, 1.0]`.
No custom trainer or untracked loss implementation is introduced.

## Interpretation rule

The mixed objective is useful only if it materially restores Schema validity and
mode coverage without reintroducing unsafe execution or excessive restriction.
Preference accuracy, margin, or loss alone cannot establish improvement. A failed
result ends this DPO branch; it is not followed by post-hoc weight tuning in the
same comparison family.

## Limits

This remains a single-seed 0.6B mechanism diagnostic on three modes. It is not a
Gate B result and does not replace the required six-mode semantic dataset.

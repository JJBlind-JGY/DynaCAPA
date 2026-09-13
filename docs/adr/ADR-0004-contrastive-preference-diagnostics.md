# ADR-0004: Balanced and bidirectional preference diagnostics

- Status: accepted for mechanism diagnosis; not formal Gate B evidence
- Date: 2026-09-13

## Context

The first 0.6B calibration exposed two different policy collapses under the same
60-example validation protocol. SFT produced almost exclusively `execute`; DPO then
produced almost exclusively `block`. The v0.2 train targets are imbalanced
(`execute` 2447, `block` 1607, `ask` 746), and every minimum-intervention-v1 DPO
negative is an unsafe `execute`. Consequently, perfect pairwise accuracy can be
obtained without learning the distinction among legal execution, recoverable
missing confirmation, and irrecoverable missing authorization.

## Decision

Create an immutable `minimum_intervention_contrastive_v2` training view over the
already approved Mail v0.2 source records:

1. deterministically down-sample train records to equal `execute`, `ask`, and
   `block` target counts; never duplicate a task;
2. preserve all validation records and the existing frozen-test prohibition;
3. generate two preference pairs per selected task:
   - a hard-safety pair against verifier-rejected execution; and
   - a mode-disambiguation pair against excessive restriction or an unresolvable
     request for confirmation;
4. label the rejection basis explicitly so safety and utility contrasts cannot be
   conflated in later analyses.

The three mode-disambiguation comparisons are:

- valid `execute` over unnecessary `block`;
- resolvable `ask` over unnecessary `block`;
- terminal `block` over an `ask` that cannot supply missing authorization.

## Controlled comparison

This view is used only for 0.6B mechanism diagnostics. The comparison must retain
the same base revision, seed, optimizer settings, update count, validation sample,
generation settings, and scorer. Results are interpreted jointly with mode recall,
PVR, UPR, FBR, and Shield Rate; DPO loss or pairwise accuracy alone is insufficient.

## Limits

This artifact still supervises only `execute`, `ask`, and `block`. It is not a
six-mode dataset and cannot establish Gate B. Distinct observable semantics for
`sandbox`, `rewrite`, and `stop` remain a versioned follow-up requirement.

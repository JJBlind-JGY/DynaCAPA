# ADR-0003: Minimum-intervention SFT targets for Mail v0.2

- Status: accepted for pipeline smoke; full-mode dataset pending
- Date: 2026-09-13

## Context

Mail v0.2 records permit multiple safe modes for the same observation:
`execute/sandbox/rewrite` when execution is authorized and `block/stop` when it is
not. Emitting every acceptable mode as an SFT target for an identical prompt would
create contradictory single-target supervision. Arbitrarily rotating those labels
would make mode behavior depend on instance IDs rather than safety semantics.

## Options considered

1. Duplicate each prompt with every acceptable completion.
2. Randomly choose one acceptable mode.
3. Use a deterministic least-restrictive target now, and add distinct semantic
   triggers for `sandbox`, `rewrite`, and `stop` in a versioned follow-up dataset.

## Decision

Use option 3. The canonical v0.2 cold-start target order is:

- valid executable right: `execute`;
- missing confirmation: `ask`;
- no executable right: `block`.

DPO pairs compare that target with a concrete verifier-rejected `execute` proposal.
The compiler produces exactly one SFT example and one DPO pair per source task and
never reads the frozen test split.

## Consequences

The generated artifact is eligible for tokenizer/trainer/data-loader smoke tests but
not for a six-mode Gate B claim. A later dataset version must define observable,
non-overlapping triggers for `sandbox`, `rewrite`, and `stop`; it must be reviewed
before formal training.

## Research-definition impact

This does not redefine D-CAPA or DACPO. It explicitly limits the first cold-start
artifact so ambiguous supervision is not mistaken for scientific evidence.

# Research specification

## Frozen central claim

DynaCAPA-RL tests whether a hard runtime authorization boundary can be converted into policy-native safety behavior without unacceptable task-utility loss.

The first evidence chain is deliberately narrow:

1. Authorization rights, environmental facts, and the executable action set are represented separately.
2. A deterministic verifier and Shield prevent unauthorized side effects in a dynamic Mail sandbox.
3. Later training stages may learn from the same representation and feedback, but cannot redefine the Phase 0 semantics.

## Claim boundary

The project may claim controlled, local, policy-conditional intervention effects. It must not claim complete causal effects in open environments or unconditional safety guarantees.

## Gate discipline

- Gate A controls entry into model training.
- Gate B controls entry into online RL.
- Gate C selects the benchmark/security or policy-internalization paper branch.
- Gate D controls whether VICC is allowed into online RL.

File/DB domains, AgentDojo, larger models, and browser/OS environments are conditional extensions rather than prerequisites for the first vertical slice.


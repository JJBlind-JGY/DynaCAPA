# Experiment protocol

## Run identity

Every run must bind its configuration path, Git commit, seed, dataset hash, environment version, verifier version, schema versions, and artifact manifest. A reused experiment ID is an error.

## Comparison contract

Comparisons must match the relevant budget: environment calls, examples, generated tokens, optimizer steps, and effective training dose. Counterfactual methods additionally report intervention count and replay cost.

## Candidate versus execution

`candidate_output` is the native policy proposal. `executed_output` is the action resolved by the Shield and passed to the environment. Proposal safety metrics use the former; execution safety and state updates use the latter. They must never be reconstructed from one another after the fact.

## Stop conditions

A training run must stop on NaN, snapshot mismatch, any serious unauthorized real execution, three consecutive evaluations with KL greater than 0.2, or a PVR drop exceeding five percentage points. Phase 0 has no real external side effects.


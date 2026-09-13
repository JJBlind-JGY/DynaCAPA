# Phase 1 deterministic verifier experiments

`verifier_validation_v0_2_ci.json` is the active report for 600 validation tasks and 1,300 constructed candidates, including Wilson intervals. The earlier `verifier_validation_v0_2.json` is retained as the pre-interval result rather than overwritten. Both are oracle-consistency experiments over programmatic ground truth, not measurements of natural-language semantic extraction and not evidence of open-world safety.

`verifier_validation_v0_2_neighbors_probes.json` is a separate mechanism-discrimination report. It adds structured AuthGraph-style and ARGUS-style proxies plus controlled parameter-source/value and task-object-invariant probes, producing 1,557 candidates. The proxy names are intentional: neither row is a full reproduction of the corresponding paper's LLM graph construction, grounding, trajectory alignment, or external benchmark setup.

`verifier_validation_v0_2_neighbors.json` is retained as the immutable pre-probe exploratory result. Its proxy rows collapsed to the simpler source/static baselines, demonstrating that the original candidate construction did not distinguish the neighboring mechanisms. It is not the active neighboring-method report.

The frozen test remains sealed during implementation. The current simple baselines are known-tool allow, provenance-only, and static authorization. AuthGraph-style and ARGUS-style neighboring baselines remain required before a paper-level D-CAPA comparison.

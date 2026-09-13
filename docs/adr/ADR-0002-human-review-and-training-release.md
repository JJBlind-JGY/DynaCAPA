# ADR-0002: Human review evidence and training release boundary

- Status: accepted
- Date: 2026-09-13

## Context

The dataset evaluation pack was inspected by the researcher and additional human
reviewers, who judged the content broadly consistent with human expectations and
authorized use of the dataset. They did not complete the row-level annotation
columns or adjudication workflow.

The existing Gate A protocol separately requires reproducible macro-F1, severe
violation recall, and agreement statistics. Qualitative review cannot be converted
into those numbers after the fact.

## Decision

Treat the review as a qualitative acceptability sign-off that releases the dataset
for data-pipeline construction and small-model engineering smoke tests. Keep Gate A
quantitative human-validation requirements open. Do not report macro-F1, recall,
Cohen's kappa, or a fully passed Gate A from this review.

The frozen test split remains sealed. Main-model SFT/DPO results are not eligible for
paper claims until the outstanding quantitative validation is resolved or the gate
protocol is prospectively revised with a defensible alternative.

## Consequences

- Work can continue without discarding the useful human inspection already done.
- No fabricated labels or statistics enter the research record.
- Engineering smoke work and scientific evidence remain explicitly distinguishable.

## Research-definition impact

No algorithm definition changes. This ADR narrows the evidentiary claim attached to
the human review.

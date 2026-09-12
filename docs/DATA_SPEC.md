# Data specification

## Inventory

`dynacapa_mail_v0_2` is the active synthetic Mail-agent dataset candidate, generated without external model APIs or personal data. Each record binds the authenticated request, source-labelled context, authorization events, facts, legal and illegal actions, expected effects, acceptable policy modes, confirmation requirements, scenario factors, and a semantic provenance hash that excludes instance identifiers.

The target counts are 4,800 training records, 600 validation records, and 1,200 frozen test records. The template catalog contains 60 base templates across report, meeting, finance, support, people, and research families.

## Split semantics

Validation contains six equal diagnostic groups: IID, unseen authorization pattern, unseen attack expression, unseen source combination, unseen Schema version, and longer horizon. These groups isolate one factor at a time.

Frozen test is stricter: its template IDs, authorization patterns, attack-expression IDs, source combinations, and tool Schema version are all disjoint from training. It measures composite generalization and is never used for tuning.

## Files and provenance

Generated JSONL files live under `data/processed/mail_v0/` and remain outside Git. Tracked manifests under `data/manifests/` record SHA-256 hashes, counts, controlled vocabularies, template membership, canonical regression cases, split rules, and the leakage audit.

Generator behavior is fail-closed. If the same dataset version would produce different bytes, the build refuses overwrite and requires a version bump.

The earlier `dynacapa_mail_v0` pilot is retained for provenance but is not eligible for training or final claims because its training split lacked no-authorization/revoked/expired acceptable-mode cases. Version 0.2.0 corrects this without overwriting the old hashes.

## Availability status

The dataset is currently an internal pre-release research artifact. No public repository, persistent identifier, creator list, publication year, or licence has been assigned; the manifest records these as unresolved rather than inventing them. Before paper submission, the release candidate must receive a repository record, licence decision, README, citation metadata, and paper/code links.

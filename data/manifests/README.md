# Dataset manifest index

- `dynacapa_mail_v0` / generator v0.1.0 is a preserved pilot snapshot. Its split leakage audit passed, but its training tasks did not include no-authorization/revoked/expired acceptable-mode cases, so it must not be used for SFT or final benchmark claims.
- `dynacapa_mail_v0_2` / generator v0.2.0 is the active dataset candidate. It adds all six policy modes to training, includes revoked and expired grants in training, and reserves fact-only and future-dated authorization patterns for controlled validation.

The v0.1 files are retained rather than overwritten so that every reported hash remains reproducible. Frozen data for either version must not be opened for tuning decisions.

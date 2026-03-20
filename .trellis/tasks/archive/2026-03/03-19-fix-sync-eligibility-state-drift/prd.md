# Fix Sync Eligibility And State Drift

## Goal
Make downstream diff/sync/propose workflows use consistent local-state and contribution-eligibility semantics, and remove stale lock-cache dependence from proposal generation.

## Requirements
- Proposal generation must not rely on stale `library-lock.yaml` contribution eligibility cache.
- Local state classification for imported assets must treat directory structure drift consistently across diff, sync, and pull-analysis flows.
- Directory checksums must use a shared implementation with stable path normalization.
- Existing CLI workflows should remain compatible unless a behavior change is required to fix the bugs.
- Add regression coverage for the three confirmed defects.

## Acceptance Criteria
- [ ] `sync --mode propose` recomputes eligibility from current source/target state and rejects assets with structural drift or private-hint content even if lock cache says eligible.
- [ ] A directory asset with file-set drift is classified consistently as structural divergence across downstream sync and diff-style flows.
- [ ] Shared checksum logic normalizes directory entry paths consistently and is reused instead of duplicated per script.
- [ ] Regression tests fail before the fix and pass after the fix.

## Technical Notes
- Touches cross-layer flow: source assets -> target imports -> `.trellis/library-lock.yaml` -> diff/sync/propose scripts.
- Keep `last_local_checksum` semantics as accepted baseline unless a new field is intentionally introduced.
- Prioritize shared helper extraction over copy-paste logic.

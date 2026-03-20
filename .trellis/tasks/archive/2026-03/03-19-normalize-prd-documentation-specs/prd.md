# Normalize PRD Documentation Specs

## Goal
Normalize the `prd-documentation` spec assets so the structure is self-consistent with library conventions and the content clearly defines format rules for customer-facing and developer-facing PRDs.

## Requirements
- Align the asset structure and manifest mapping with the library's spec authoring conventions.
- Keep a clear separation between customer-facing and developer-facing guidance.
- Make both specs define minimum document sections, audience-specific writing requirements, and explicit exclusions.
- Tighten verification criteria so each normative rule has an observable review check.
- Keep the scope limited to the PRD documentation concern and its manifest entries.

## Acceptance Criteria
- [ ] `prd-documentation` assets and manifest entries are structurally self-consistent.
- [ ] Customer-facing spec defines a readable but explicit PRD format from the customer's perspective.
- [ ] Developer-facing spec defines a technical PRD format with concrete implementation-oriented requirements.
- [ ] Verification files contain checkable items that cover the normative rules.
- [ ] `trellis-library/cli.py validate --strict-warnings` exits successfully after the changes.

## Technical Notes
- This task modifies trellis-library spec assets and `manifest.yaml`.
- The change should avoid expanding into unrelated product-and-requirements concerns.

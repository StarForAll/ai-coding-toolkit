# Refresh trellis-library with current stable docs

## Goal

Audit version-sensitive and technology-bound content under `trellis-library/`, verify it against current stable official documentation, and correct or remove content that is outdated, experimental-only, or no longer justified as a reusable library asset.

## What I already know

* `trellis-library/` is the source asset library and must stay in English by default.
* The highest-risk drift currently appears in `specs/technologies/frameworks/nextjs/`, `specs/technologies/frameworks/electron/`, and example/template content that hard-codes versions, model names, or experimental APIs.
* Current local findings include:
  * `nextjs/shared/dependencies.md` contains many exact version ranges plus `latest`.
  * `nextjs/backend/ai-sdk-integration.md` and `nextjs/backend/logging.md` still use `experimental_telemetry`.
  * `nextjs/overview.md` and `electron/overview.md` hard-code stack versions in overview text.
  * `examples/universal-domains/product-and-requirements/developer-facing-prd-example.md` contains old Java/Spring Boot baseline examples.
* Some technology assets may still be useful, but low-signal volatile details inside them may not be worth keeping.

## Assumptions (temporary)

* This task should prioritize high-drift assets that make explicit third-party version, model, or experimental API claims rather than attempting a full semantic rewrite of every file in `trellis-library/`.
* When a document section is inherently unstable and not necessary for reusable guidance, the right fix is to remove or generalize it instead of replacing it with another brittle exact-value list.
* Stable official docs should be sourced through `context7` for the main affected technologies before editing.

## Open Questions

* None currently blocking. Proceed with evidence-first audit and keep scope focused on files with clear drift or low long-term value.

## Requirements

* Identify `trellis-library/` files whose guidance depends on third-party APIs, versions, or concrete compatibility claims.
* Verify the current stable, non-experimental official guidance for the main affected technologies through `context7`.
* Update content that is stale, misleading, or anchored to experimental APIs.
* Remove content that does not justify its maintenance cost as a reusable library asset.
* Preserve manifest validity and internal link integrity after changes.

## Acceptance Criteria

* [ ] Version-sensitive files selected for this task have documented evidence for each substantive correction.
* [ ] No edited file recommends experimental-only APIs as the default stable path.
* [ ] Volatile exact-version or exact-model guidance is either validated as still appropriate or rewritten/removed.
* [ ] Any removed content is also removed from manifest references or pack references when applicable.
* [ ] `python3 trellis-library/cli.py validate --strict-warnings` passes.
* [ ] Relevant tests or validation commands are run and results recorded truthfully.

## Definition of Done

* Stable-doc evidence collected in task research files
* `trellis-library/` content corrected with minimal necessary scope
* Validation run and outcomes recorded
* Residual risks and remaining non-audited areas explicitly called out

## Out of Scope

* Rewriting every technology guide in `trellis-library/`
* Introducing new framework families or expanding pack coverage
* Refactoring unrelated assets that do not show clear evidence of drift

## Technical Notes

* Local authoring rules already reviewed:
  * `.trellis/spec/library-assets/index.md`
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/manifest-maintenance.md`
  * `.trellis/spec/docs/index.md`
* Initial local drift scan focused on explicit versions, `latest`, and `experimental_*` references.

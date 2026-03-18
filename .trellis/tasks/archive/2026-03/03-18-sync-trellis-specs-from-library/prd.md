# brainstorm: sync trellis specs from trellis-library

## Goal

Review the existing reusable specs in `trellis-library/specs/`, choose the subset that should be added into this project's `.trellis/spec/`, and stage the work through an explicit human approval checkpoint before any final spec content is copied into place. If the needed spec does not exist or is incomplete in `trellis-library`, fill the gap there first and only then proceed with project-local adoption.

## What I already know

* The project currently has a minimal `.trellis/spec/` tree with only top-level indexes and two shared thinking guides.
* `trellis-library/specs/` already contains broad reusable coverage across universal domains, scenarios, platforms, and technologies.
* The user requires manual confirmation before any formal spec addition into `.trellis/spec/`.
* If target specs are missing or incomplete, the source of truth must be fixed in `trellis-library` first.
* The existing library-native import mechanism is `trellis-library/cli.py assemble`, which copies selected assets into a target project's `.trellis/specs/...` tree and writes `.trellis/library-lock.yaml`.

## Assumptions (temporary)

* The task is to enrich the current project's Trellis spec set, not to mirror the entire library.
* The preferred output is a curated subset with rationale, not a bulk import.
* Selection should favor specs that fit this repository as an AI coding toolkit / meta-project.

## Open Questions

* Should this project adopt the library-native target layout `.trellis/specs/...` plus `.trellis/library-lock.yaml`, or should the work keep the existing `.trellis/spec/` layout and therefore require an adaptation layer beyond the library's current native mechanism?

## Requirements (evolving)

* Inventory current `.trellis/spec/` coverage and relevant `trellis-library/specs/` candidates.
* First pass should target a minimal core set, not a broad import.
* First pass is governance-first only.
* Propose a curated set of candidate specs with rationale and impact.
* Pause for explicit human confirmation before copying or editing project-local spec files.
* If required specs are missing or incomplete in `trellis-library`, patch `trellis-library` first.
* Keep project-local specs aligned with the project's actual repo type and workflows.
* Prefer using the library's native assembly and sync mechanism rather than hand-copying files.

## Acceptance Criteria (evolving)

* [ ] A candidate import set is identified with reasons for inclusion and exclusion.
* [ ] Human approval is recorded before project-local spec content is added.
* [ ] Missing source specs, if any, are completed in `trellis-library` before local adoption.
* [ ] Added `.trellis/spec/` content matches the chosen source specs and project context.

## Definition of Done (team quality bar)

* Tests added/updated when behavior changes
* Lint / typecheck / CI green where relevant
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Blindly mirroring the full `trellis-library/specs/` tree
* Changing unrelated project code or workflows without approval
* Treating preliminary candidate discovery as final adoption

## Technical Notes

* Current project spec files inspected:
  * `.trellis/spec/index.md`
  * `.trellis/spec/agents/index.md`
  * `.trellis/spec/commands/index.md`
  * `.trellis/spec/config/index.md`
  * `.trellis/spec/docs/index.md`
  * `.trellis/spec/skills/index.md`
  * `.trellis/spec/guides/index.md`
* Source library inventory inspected at directory level under `trellis-library/specs/`.
* This repository is a meta-project for agents, commands, skills, and config, so platform/framework-specific specs may have low relevance.
* High-relevance source families for a minimal first pass:
  * `specs/universal-domains/product-and-requirements/*`
  * `specs/universal-domains/project-governance/*`
  * `specs/universal-domains/verification/*`
* Optional-but-relevant source families for this repo type:
  * `specs/universal-domains/agent-collaboration/*`
  * `specs/universal-domains/context-engineering/*`
  * `specs/universal-domains/ai-execution/*`
* Native library mechanism findings:
  * `scripts/assembly/assemble-init-set.py` copies selected `spec` / `template` / `checklist` assets to `target/.trellis/<asset.path>`
  * For spec assets, that means target paths like `.trellis/specs/universal-domains/...`
  * The same flow writes `.trellis/library-lock.yaml` for downstream sync and provenance tracking

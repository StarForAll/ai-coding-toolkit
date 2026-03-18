# brainstorm: universal spec taxonomy for trellis

## Goal

Define a library of universal, atomic spec files for software development and AI-assisted workflows. These specs will live in this repository as reusable source assets, so future projects can select and initialize only the relevant spec files after project setup.

## What I already know

* This repository is not a product app; it is an AI-assisted development toolkit covering personal workflows, reusable development specs, and agent-related practices.
* The current request is about a reusable spec asset library under the current project, not about the current project's own active `.trellis/spec/` usage.
* The desired outputs are atomic spec files that can be mixed and matched for future projects during initialization.
* The current Trellis spec taxonomy is narrow: `.trellis/spec/backend/`, `.trellis/spec/frontend/`, and `.trellis/spec/guides/`.
* That taxonomy is useful for project-local conventions, but it does not yet model a reusable cross-project spec library.
* `docs/workflows/新项目开发工作流/工作流总纲.md` already contains broader, reusable spec candidates:
* project rules and naming/quality constraints
* interface and data contract rules
* AI execution and output constraints
* context management and contamination handling
* verification, self-review, and risk grading
* `.agents/skills/update-spec`, `finish-work`, and `break-loop` all treat spec docs as living contracts, which suggests Trellis should separate stable universal rules from project-local conventions.

## Assumptions (temporary)

* We are defining a reusable source taxonomy under this repo, from which future project templates or initialization flows can pull selected spec files.
* Each spec file should be atomic enough to reuse independently, but not so small that initialization becomes unmanageable.
* The taxonomy should separate universal specs from project-instance specs cleanly.

## Open Questions

* How should the reusable library handle platform-specific and stack-specific domains such as Android/iOS/HarmonyOS, JDK8/JDK17/MySQL/Vue, and development-scenario specs such as refactoring and bug fixing?

## Requirements (evolving)

* Identify universal spec categories that recur across software projects and AI-assisted development workflows.
* Ensure every spec file is atomic and reusable across projects.
* Organize the spec library so future project initialization can select only relevant files.
* Cover broad software development concerns, not only frontend/backend code conventions.
* Distinguish reusable source specs in this repo from project-instance specs generated into a target project.
* For each spec file, define its exact professional angle to avoid overlap and ambiguity.
* Cover not only technical and AI engineering concerns, but also product, requirement, project management, collaboration, and delivery concerns.
* The reusable source assets should be organized under a common parent directory with three primary child areas: `specs/`, `templates/`, and `checklists/`.
* The taxonomy must explicitly decide what to do with:
* platform-specific implementation guidance
* stack/version-specific technology guidance
* development-scenario guidance such as refactoring and bug fixing
* The taxonomy should expand scenario coverage before directory restructuring, so scenario gaps do not force repeated tree redesign.

## Acceptance Criteria (evolving)

* [ ] A candidate list of universal spec categories exists, with rationale for each.
* [ ] A proposed atomic file taxonomy exists for the reusable spec library.
* [ ] The boundary between reusable source specs and generated project specs is explicit.
* [ ] Out-of-scope categories are explicitly listed.

## Definition of Done (team quality bar)

* The taxonomy is derived from repository evidence, not only intuition.
* Trade-offs between different organization schemes are explicit.
* The final proposal can be turned into concrete reusable files under a source spec library in this repo.

## Out of Scope (explicit)

* Filling the final content of every reusable spec file.
* Choosing stack-specific conventions for a particular target app.
* Implementing the taxonomy changes before requirements are confirmed.

## Technical Notes

* Files inspected:
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `.trellis/workflow.md`
* `.trellis/spec/backend/index.md`
* `.trellis/spec/frontend/index.md`
* `.trellis/spec/guides/index.md`
* `.agents/skills/start/SKILL.md`
* `.agents/skills/before-dev/SKILL.md`
* `.agents/skills/finish-work/SKILL.md`
* `.agents/skills/update-spec/SKILL.md`
* Evidence highlights from workflow docs:
* universal rules already documented include naming, data/interface constraints, context strategy, AI tool-call/output constraints, self-review, and context contamination handling
* current Trellis default spec folders do not represent those dimensions explicitly
* [Evidence Gap] `ace.search_context` was attempted first for semantic repo search but failed with `401 Unauthorized`; fallback was local file inspection via `rg` and direct reads

## Research Notes

### What this repo suggests about reusable spec layers

* A pure `frontend/backend` split is sufficient for application coding style, but insufficient for a reusable spec asset library.
* The workflow docs treat "spec" as more than code style: they use it as the contract source for planning, implementation, self-check, verification, and session reset.
* Therefore, a reusable library likely needs multiple orthogonal axes:
* concern domain specs
* implementation-layer specs
* workflow/governance specs

### Feasible approaches here

**Approach A: Organize by project layer**  
(backend/frontend/guides and similar layer buckets)

* How it works:
  Reusable source specs are grouped by implementation layer, with cross-cutting rules placed in guides.
* Pros:
  Familiar and easy to navigate for app developers.
* Cons:
  Broad lifecycle and governance specs get awkwardly forced into generic buckets.

**Approach B: Organize by concern domain**  
(recommended)

* How it works:
  Build a reusable source library around stable concern domains such as architecture, contracts, data, quality, verification, AI execution, context, agent collaboration, and frontend/backend implementation patterns.
* Pros:
  Better matches cross-project reuse and supports selective initialization.
* Cons:
  Requires clearer naming discipline to avoid overlap between domains.

**Approach C: Organize by lifecycle stage**

* How it works:
  Group reusable specs under phases like discovery, planning, design, implementation, verification, release, and operations.
* Pros:
  Maps naturally to workflow execution order.
* Cons:
  The same concern often appears in multiple phases, which hurts atomic reuse.

## Decision (ADR-lite)

**Context**: We need a reusable spec asset library for future project initialization. The library must support broad reuse, atomic file selection, and clear boundaries between files.

**Decision**: Organize the reusable spec library by concern domain rather than by implementation layer or lifecycle stage.

**Consequences**:

* Each file must declare a single professional angle and responsibility boundary.
* Initialization can select files by domain without inheriting irrelevant stack-specific content.
* Taxonomy design now needs stronger file naming and scope definitions to avoid overlap.
* The reusable library must support broader domains beyond engineering implementation, including upstream planning and downstream delivery/operations.

## Additional Decisions

### Library Parent Directory

**Decision**: Use `trellis-library/` as the parent directory for reusable source assets.

**Why**:

* It clearly distinguishes reusable source assets from project-instance `.trellis/` directories.
* It is explicit about Trellis relevance without binding assets to a single target project structure.

### Asset Types

**Decision**: The reusable library will contain separate top-level asset types:

* `specs/` for normative reusable rules
* `templates/` for reusable document or initialization templates
* `checklists/` for execution and review checklists

**Why**:

* This preserves atomicity and prevents one file from mixing rules, templates, and verification artifacts.

## Additional Research Notes

### Candidate scope classes that need an explicit inclusion policy

**Class 1: Platform-specific implementation specs**

Examples:

* Android
* iOS
* HarmonyOS

These are highly reusable across many projects, but not universal across all projects.

**Class 2: Stack- or version-specific technology specs**

Examples:

* JDK 8
* JDK 17
* MySQL
* Vue

These are also reusable, but they are dependency- and version-bound rather than universally applicable.

**Class 3: Development-scenario specs**

Examples:

* refactoring
* bug fixing
* debugging
* code review fixes

These are not stack-bound; they are process scenarios that recur across many projects.

### Preliminary inclusion judgment

**Platform-specific implementation specs**

* Include: yes
* But not in the same domain layer as universal governance specs
* Best treated as optional specialization packs under implementation-oriented domains

**Stack- or version-specific technology specs**

* Include: yes
* But only when the spec is tied to a real compatibility, version, or ecosystem decision boundary
* Best treated as optional technology packs with explicit version scope

**Development-scenario specs**

* Include: yes, strongly
* These are highly reusable in AI-assisted workflows and map directly to execution behavior, verification, and collaboration
* Best treated as cross-stack scenario specs rather than implementation-layer docs

### Additional scenario classes to consider before restructuring

**Class 4: Delivery lifecycle scenarios**

Examples:

* new feature delivery
* spike / feasibility study
* release preparation
* hotfix / emergency fix
* rollback / recovery

These scenarios shape what evidence, checks, and coordination rules are needed.

**Class 5: Maintenance and evolution scenarios**

Examples:

* dependency upgrade
* framework migration
* legacy code cleanup
* deprecation rollout
* performance optimization

These recur across projects and often require specialized rules beyond normal feature work.

**Class 6: Collaboration and review scenarios**

Examples:

* code review response
* design review
* handoff to another developer or agent
* parallel multi-agent execution
* external stakeholder review

These are especially important for Trellis because they affect context transfer and execution quality.

**Class 7: Reliability and incident scenarios**

Examples:

* production incident handling
* postmortem follow-up
* regression investigation
* flaky test triage
* observability gap fixing

These bridge engineering, operations, and verification.

**Class 8: Data and contract change scenarios**

Examples:

* schema migration
* API version upgrade
* breaking contract change
* third-party integration swap
* backfill / repair job

These are high-risk and often deserve dedicated reusable specs.

# brainstorm: trellis-library consistency audit

## Goal

Audit all files in `trellis-library/` for terminology and format consistency, then
propose a bounded normalization plan for user approval before making any edits.

## What I already know

* User wants a plan first, then modifications after confirmation.
* `trellis-library/` is the source asset library and uses `manifest.yaml` as the
  source registry.
* `spec` assets are not uniform in physical shape today:
  * complex concern directories with `overview.md`, `scope-boundary.md`,
    `normative-rules.md`, and `verification.md`
  * grouped multi-file spec sets using `<meta>.yaml`
  * single-file spec documents inside grouped directories
* `taxonomy.md` already defines canonical terms such as `concern`,
  `verification`, `validation`, `source-library`, and `target-project`.
* Root docs and `.trellis/spec/library-assets/*.md` provide current authoring
  expectations, but they do not yet guarantee full-library terminology drift
  detection.

## Assumptions (temporary)

* The requested scope is content normalization inside `trellis-library/`, not a
  redesign of the asset model.
* Existing spec shape diversity is intentional if it is registered and
  semantically justified.
* Format consistency should mean "consistent within each allowed asset shape",
  not "force one universal document layout across every asset type".

## Open Questions

* Should this pass normalize only registered source assets under
  `trellis-library/`, or also include implementation/support files such as
  `_internal/` and `tests/`?

## Requirements (evolving)

* Inventory the current asset shapes and terminology baselines before proposing
  edits.
* Distinguish strict inconsistencies from allowed structural variation.
* Produce a concrete modification strategy with clear boundaries and approval
  gate before editing files.
* Scope includes registered assets under `trellis-library/` plus root control
  documents `README.md`, `taxonomy.md`, and `manifest.yaml`.
* When a spec baseline affects linked assets, synchronize the associated
  `templates/`, `checklists/`, and `examples/` as part of the same pass.

## Acceptance Criteria (evolving)

* [ ] There is a documented audit strategy for terminology and format
      consistency in `trellis-library/`.
* [ ] The strategy explicitly allows multiple valid spec shapes.
* [ ] The user confirms the strategy before any repository files are modified.

## Definition of Done (team quality bar)

* Audit scope and normalization rules are explicit
* Proposed edits are grouped by category, not ad hoc file-by-file churn
* Validation approach is defined before implementation starts

## Out of Scope (explicit)

* Redesigning the manifest schema
* Replacing all spec assets with one mandatory structure
* Editing files before user confirms the proposed plan
* Non-registered implementation/support files such as `_internal/` and `tests/`
  unless a direct consistency blocker is discovered later

## Technical Notes

* Task directory: `.trellis/tasks/03-30-trellis-library-consistency-audit`
* Relevant guidance:
  * `.trellis/spec/library-assets/index.md`
  * `.trellis/spec/library-assets/spec-authoring.md`
  * `.trellis/spec/library-assets/template-authoring.md`
  * `.trellis/spec/library-assets/checklist-authoring.md`
  * `.trellis/spec/library-assets/manifest-maintenance.md`
* Key baseline docs:
  * `trellis-library/README.md`
  * `trellis-library/taxonomy.md`
  * `trellis-library/manifest.yaml`
* Observed non-4-file spec groups include:
  * `specs/technologies/frameworks/nextjs/**`
  * `specs/technologies/frameworks/electron/**`
  * `specs/scenarios/defect-and-debugging/*-pitfalls/**`

## Research Notes

### What the repo already enforces

* `trellis-library/cli.py validate` delegates to
  `scripts/validation/validate-library-sync.py`.
* Current validation already checks:
  * manifest shape and schema
  * asset registration drift
  * path/type/format alignment
  * standard spec directory file presence when applicable
  * template and checklist top-level structure
* Current validation does **not** enforce:
  * canonical terminology usage across all markdown files
  * wording consistency between `README.md`, `taxonomy.md`,
    `manifest.yaml`, and asset bodies
  * allowed spec-shape classification beyond structure heuristics

### Constraints from the repo

* `spec` shape diversity is real and must be preserved when intentional.
* `taxonomy.md` is the strongest existing terminology baseline.
* `manifest.yaml` is the registry baseline for asset type, path, format, and
  concern naming.
* A good solution should prefer deterministic scanning over manual grep-only
  cleanup.

### Feasible approaches here

**Approach A: One-time manual audit and patch**

* How it works:
  inspect files, produce a deviation list, edit files directly, then run
  existing validation.
* Pros:
  fastest to start; smallest code change.
* Cons:
  drift can reappear; no reusable guardrail.

**Approach B: Add a consistency audit rule set and run targeted cleanup** (Recommended)

* How it works:
  define canonical terminology + per-asset-type format rules, implement a new
  validation script or extend the existing validator, run it to generate
  findings, then fix flagged files in controlled batches.
* Pros:
  repeatable; future regressions become detectable; aligns with library tooling.
* Cons:
  slightly larger scope; requires defining allowed exceptions explicitly.

**Approach C: Full normalization including asset-shape refactor**

* How it works:
  in addition to terminology cleanup, refactor spec groups toward a tighter
  common shape and rewrite docs accordingly.
* Pros:
  maximum uniformity.
* Cons:
  highest churn; conflicts with the requirement to allow multiple valid spec
  shapes.

## Scan Findings

### Terminology and language drift found from content scan

* Root documentation is not internally language-consistent:
  * `trellis-library/README.md` is mostly English but contains a Chinese
    "Recent Additions" section and mixed phrases such as `For外包`.
* Some registered templates are structurally English but contain mixed field
  labels and prose:
  * `templates/universal-domains/project-governance/external-project-delivery-tasks/trial-run-delivery.md`
    contains `Task Type |交付任务 |` and `Parallel属性`.
* Some technology spec documents are fully Chinese while adjacent files in the
  same library are English:
  * `specs/technologies/frameworks/electron/shared/pnpm-electron-setup.md`
* Canonical compound terms are not yet guarded by a validator; current usage is
  mostly aligned but enforcement is informal.

### Format-pattern findings

* Standard 4-file concern directories are common and already partly validated.
* Grouped spec sets with `<meta>.yaml` and many leaf markdown files are also
  common in:
  * `specs/technologies/frameworks/nextjs/**`
  * `specs/technologies/frameworks/electron/**`
  * `specs/scenarios/defect-and-debugging/*-pitfalls/**`
* Therefore, "format consistency" must be defined as:
  * consistent within each allowed asset shape
  * consistent title/section/field conventions within a file family
  * not "force every spec into one structure"

## Decision (ADR-lite)

**Context**: The library already contains real terminology and format drift, but
`spec` assets intentionally use multiple valid shapes.

**Decision**:

* Use the "registered assets + root control docs" scope.
* Include associated `templates/`, `checklists/`, and `examples/` when they are
  linked by manifest relations or clearly belong to the same domain package.
* Treat consistency as normalization within allowed asset families, not a full
  shape refactor.

**Consequences**:

* The pass stays bounded and auditable.
* Fixes can touch multiple directories when one concept spans spec/template/
  checklist/example assets.
* A follow-up validator is still recommended to prevent regressions.

## Technical Approach

1. Build the audit baseline from:
   * `trellis-library/taxonomy.md`
   * `trellis-library/README.md`
   * `trellis-library/manifest.yaml`
2. Scan all registered markdown/yaml assets for:
   * language mixing inside primarily English assets
   * canonical term drift (`source-library`, `target-project`, etc.)
   * inconsistent file-family structure or field labels
3. Determine associated assets by:
   * manifest relations: `implements-template-for`, `verified-by`,
     `related-to`, `includes`
   * same-domain grouped assets when relation metadata is absent but the asset
     set is clearly authored as one package
4. Apply fixes in batches:
   * root control docs
   * project-governance linked asset set
   * scenario linked asset sets
   * remaining standalone drifts
5. Validate with existing library validation and a consistency-focused audit
   command or scripted scan output.

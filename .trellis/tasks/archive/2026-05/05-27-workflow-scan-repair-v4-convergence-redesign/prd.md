# workflow-scan-repair-v4 convergence redesign

## Goal

Redesign the coupled `workflow-scan` / `workflow-repair` skill model so it can
converge reliably for `docs/workflows/新项目开发工作流/` without falling into:

- incremental discovery loops, where each repair round only reveals the next
  batch of defects after a fresh embed, and
- multi-round repair drift, where current repair decisions get pulled away from
  the present truth by stale reports, stale temp projects, or over-broad
  closure absorption.

The redesign must upgrade the pair to a new explicit `v4` contract, make
version truth and stale-report rejection hard gates, and move convergence
responsibility into `workflow-repair` through bounded closure verification.

## What I already know

- The current coupled pair is `skills/workflow-scan/` and
  `skills/workflow-repair/`, with shared protocol
  `workflow-scan-repair-v3`.
- `workflow-scan` currently emits `WORKFLOW_QUESTIONS.md` from a single temp
  project and records `workflow-version` /
  `workflow-schema-version` from temp-project installed surfaces.
- `workflow-repair` currently validates protocol and shared report fields, but
  only reads version fields; it does not yet hard-stop on stale workflow
  version mismatch.
- The current workflow source-of-truth version anchor is
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py`:
  `WORKFLOW_VERSION` and `WORKFLOW_SCHEMA_VERSION`.
- Installer and upgrade paths currently write both version fields from the same
  source constants into target-project records, so
  `workflow-version == same` while `workflow-schema-version != same` should be
  treated as an invalid embedded state rather than a normal supported case.
- Old issue-history data is intentionally being dropped from the new model
  instead of migrated.
- The accepted new workflow versioning rule is:
  - current source example: `0.1.2800`
  - each successful repair bumps only the last numeric segment:
    `0.1.2800 -> 0.1.2801`
  - carry is numeric rather than fixed-width:
    `0.1.9999 -> 0.1.10000`
  - repair may not decide the first or second numeric segments.

## Assumptions (temporary)

- The redesign will be expressed as `workflow-scan-repair-v4` rather than
  continued as patchy `v3` compatibility growth.
- `workflow-repair` becomes the single convergence coordinator; `workflow-scan`
  remains the initial external discovery entrypoint.
- Same-version stale-report blocking is stricter than the old `legacy/unknown`
  tolerance model; missing version fields now fail rather than degrade.
- No repo requirement remains to preserve or consume the old
  `tmp/workflow-issues/` corpus once the new model is in place.

## Open Questions

- Default closure scenario matrix: exact naming and expansion rules still need
  to be frozen, but repo evidence already supports a recommendation:
  - baseline default: one fresh `clean` scenario with `outsourcing` profile and
    `claude,opencode,codex`
  - expand to `personal` only when profile-specific install/runtime logic is
    touched
  - expand to `existing-trellis` and `existing-workflow` only when the repair
    touches install record, upgrade, cleanup, uninstall, or runtime patch
    surfaces
- Task-local closure findings schema: current `repair-log-template.md` is too
  coarse for round/scenario-level closure facts, so `v4` should likely use a
  dedicated task-local closure artifact per round and keep only summary links
  in the repair log.
- Version-bump synchronization: current source-of-truth should remain
  `workflow_assets.py::WORKFLOW_VERSION`; the implementation should enforce
  search-driven active-source synchronization rather than introduce a second
  version manifest.
- Whether `tmp/workflow-issues/` should survive in `v4` at all. Current
  redesign direction strongly suggests removing it from repair decision-making
  and relying on same-version task-local closure artifacts instead.
- Closure artifact decision is now accepted at the design level:
  - keep `workflow-repair-log.md` as the high-level audit artifact
  - add dedicated task-local closure artifacts such as
    `closure-round-<N>.md` for round/scenario/family-level detail
  - link those artifacts from the repair log instead of flattening closure
    detail into the per-fix repair log shape

## Requirements (confirmed)

### Protocol and version truth

- [x] Upgrade the coupled scan/repair protocol to `workflow-scan-repair-v4`.
- [x] The current source workflow version truth source is only
      `docs/workflows/新项目开发工作流/commands/workflow_assets.py::WORKFLOW_VERSION`.
- [x] `workflow-scan` reports must include the actual embedded
      `workflow-version` and `workflow-schema-version`; `unknown` is no longer
      acceptable in the successful output contract.
- [x] `workflow-repair` must require three-way workflow version equality:
      report version, temp-project install-record version, and current source
      `WORKFLOW_VERSION`.
- [x] Workflow version mismatch means
      `Blocked / Stale Scan Report` and the run stops immediately.
- [x] `workflow-version` equality with `workflow-schema-version` mismatch means
      `Blocked / Invalid Embedded State` and the run stops immediately.
- [x] Stale reports are not reused. The user must re-embed / re-scan.

### Workflow version bump rule

- [x] The source workflow version format moves from values like `0.1.28` to
      values like `0.1.2800`.
- [x] A successful repair bumps only the final numeric segment.
- [x] The final numeric segment is a decimal counter, not a fixed-width field.
- [x] Repair does not change the first or second numeric segments.
- [x] Version bump happens only after repair work remains in source and
      closure has fully converged.
- [x] Failed, reverted, blocked, or no-op repair runs do not consume a new
      workflow version.

### Convergence model

- [x] `workflow-repair` becomes the only convergence coordinator.
- [x] `workflow-scan` remains an initial discovery artifact producer, not the
      final convergence authority.
- [x] `workflow-repair` must own bounded closure verification after source
      edits.
- [x] Close-out is forbidden whenever closure still has any unresolved new
      in-scope finding.
- [x] Version bump is forbidden whenever closure still has any unresolved new
      in-scope finding.

### Closure findings and anti-drift rules

- [x] Closure findings do not generate a second `workflow-scan` report.
- [x] Closure findings are recorded only inside the current repair task.
- [x] Closure findings must be separated from original scan findings in the
      repair artifact structure.
- [x] Closure may auto-absorb only findings in the same family and same
      contract surface.
- [x] A new family discovered during closure stops automatic progression of the
      current batch and returns control to a new planning/decision checkpoint.
- [x] `current closure truth > old scan interpretation`.
- [x] No unresolved in-scope finding may be downgraded merely to permit
      close-out.

### Closure fixture isolation

- [x] Closure must use fresh isolated fixtures, not the canonical
      `/tmp/trellis-{VERSION}-2` temp project reused by ordinary scan.
- [x] Each closure round and scenario must have its own dedicated temp root.
- [x] Existing closure fixture directories are not overwritten.
- [x] Residual scan reports, stale install records, or version mismatch inside
      a closure fixture mean `Blocked / Invalid Embedded State`.

### Recommended closure matrix

- [x] Recommended baseline closure scenario:
      `clean-outsourcing-all-cli`
- [x] Recommended expansion trigger for profile-specific logic:
      add `clean-personal-all-cli`
- [x] Recommended expansion trigger for install/upgrade/cleanup/runtime-patch
      logic:
      add `existing-trellis-outsourcing-all-cli`
      and `existing-workflow-outsourcing-all-cli`
- [x] Closure scenario expansion should be mechanical from touched surface
      classes rather than decided ad hoc during execution.

### Closure stopping rules

- [x] Same-family absorb is bounded to two closure rounds.
- [x] If the same family still emits new in-scope findings after the allowed
      absorb rounds, the run must stop as not converged and route to broader
      audit or equivalent blocker handling.
- [x] New-family discovery in closure must stop automatic progression rather
      than silently expanding repair scope.
- [x] Closure-added repair work should roll back at a bounded round-local
      granularity rather than leave half-applied state.

### Closure artifact strategy

- [x] The current repair log is retained as the high-level audit artifact.
- [x] Detailed closure findings should live in a dedicated task-local closure
      artifact rather than being flattened directly into the per-fix repair log.
- [x] Closure artifacts should be same-version only and should not become
      cross-version repair memory.
- [x] Accepted concrete direction: use per-round task-local artifacts such as
      `closure-round-<N>.md`, with the repair log summarizing and linking to
      them instead of embedding all closure detail directly.

### Issue-history replacement direction

- [x] Old `tmp/workflow-issues/` data is ignored rather than migrated.
- [x] `v4` should remove old issue-history memory from repair decision-making.
- [x] Same-version task-local closure artifacts should replace cross-version
      issue-history as the convergence memory surface.

### Version-reference synchronization

- [x] Any source-controlled current-version references tied to the active
      workflow version must be updated in the same change.
- [x] The exact affected files are not pre-fixed; they must be found from the
      actual repository state at implementation time.

## Acceptance Criteria (evolving)

- [ ] A written `v4` contract exists for both `workflow-scan` and
      `workflow-repair`, with synchronized templates/specs/tests.
- [ ] `workflow-scan` successful output can no longer emit `unknown`
      workflow-version fields.
- [ ] `workflow-repair` rejects stale reports via explicit version gates rather
      than merely reading the version fields.
- [ ] The redesign removes dependence on old cross-version issue-history memory
      for repair decisions.
- [ ] The repair flow defines bounded closure behavior with explicit anti-drift
      and no-close-out gates.
- [ ] Version bump semantics are explicit, deterministic, and verified by
      tests or equivalent validation.
- [ ] Default closure scenario selection and expansion rules are frozen
      mechanically enough that execution no longer depends on ad hoc operator
      judgment.
- [ ] A dedicated closure artifact schema exists and is sufficient to record
      scenario id, round, family boundary, and disposition without overloading
      the legacy repair log shape.

## Definition of Done (team quality bar)

- Repo specs and paired skill contracts are updated together.
- `implement.jsonl` and `check.jsonl` are curated with the needed spec files.
- Relevant skill/reference/test assets are updated together with no protocol
  drift.
- Relevant validation commands are run and reported truthfully.

## Out of Scope (explicit)

- Restoring compatibility with old `v3` repair-history semantics.
- Building a general-purpose matrix framework independent from the
  workflow-scan / workflow-repair redesign.
- Changing Trellis core product behavior outside what this workflow can patch
  or declare in its own source tree.
- Deciding major/minor workflow version changes unrelated to repair convergence.

## Technical Notes

- Coupled spec guidance:
  - `.trellis/spec/skills/index.md`
  - `.trellis/spec/skills/workflow-scan.md`
  - `.trellis/spec/skills/workflow-repair.md`
- Primary source version anchor:
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Current protocol emit/intake assets:
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-repair/references/correction-plan-template.md`
  - `skills/workflow-repair/references/repair-log-template.md`
  - `skills/workflow-repair/references/issue-history-template.md`
- Expected implementation impact:
  - protocol bump to `v4`
  - report contract hardening
  - repair-side version gate and closure redesign
  - version string migration from `0.1.28` style to `0.1.2800` style
  - likely retirement or demotion of `tmp/workflow-issues/` from the v4 core
    decision path

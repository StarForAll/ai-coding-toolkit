# fix workflow-audit skill compatibility

## Goal

Repair the repo-local `workflow-audit` skill only where current evidence proves a real compatibility or discoverability defect in its live entry surfaces, while preserving the current Trellis implementation in this repository, the current workflow-managed platform boundaries, and the repo-local skill contract under `.trellis/spec/skills/workflow-audit.md` without introducing new behavioral drift or unsupported workflow semantics.

## What I already know

- The live repo-local entry surfaces for this skill are:
  - `.agents/skills/workflow-audit/SKILL.md`
  - `.claude/skills/workflow-audit/SKILL.md`
- The behavioral source of truth is `.trellis/spec/skills/workflow-audit.md`.
- The repository uses Trellis native runtime under `.trellis/` and platform carrier layers under `.claude/`, `.opencode/`, `.codex/`, `.kiro/`, and `.qoder/`.
- In this repository, `.trellis/config.yaml` keeps `codex.dispatch_mode: inline`, and `.trellis/spec/platforms/codex-workflow-behavior.md` forbids manual subagent dispatch in inline Codex sessions.
- Codex uses `AGENTS.md`, `.codex/config.toml`, and `.codex/hooks.json` as its primary repo-local control surfaces; `.codex/skills/` is present but not the default primary carrier.
- Claude and OpenCode have native skills carriers plus hook/plugin-based workflow-state and subagent-context injection.
- `.kiro/` and `.qoder/` exist in the source repo but are outside `workflow-audit`'s current supported managed surface unless `workflow_assets.py` expands that scope.
- `.agents/skills/workflow-audit/` and `.claude/skills/workflow-audit/` are currently identical, so the problem is not entry-surface divergence between those two files.
- Static inspection shows the live skill still contains the core audit contract areas: version gate, supported surface, execution modes, Codex handoff, runtime-validation triggers, report contracts, sync rules, references, and persisted scenario list.
- The confirmed defect repaired in this task is the live-skill frontmatter discovery contract, not a broader audit-behavior rewrite.

## Assumptions (temporary)

- The user wants an actual repair, not only an analysis memo.
- The repair should keep the live skill behavior aligned with the existing source-of-truth spec, rather than changing the workflow product's managed-surface contract.
- Companion references/tests only need edits if the repaired live skill semantics make any current reference or persisted scenario inaccurate.
- No workflow product source files under `docs/workflows/新项目开发工作流/` should be changed unless current evidence proves the live skill defect comes from an outdated workflow-side contract instead of skill-surface drift.

## Open Questions

- None currently blocking. If a reference/test contract conflicts with the repaired live skill wording, decide whether the behavior should be normalized in the skill or propagated through companion files in the same change.

## Requirements (evolving)

- Align the live `workflow-audit` skill contract with the current Trellis implementation actually used by this repository.
- Limit edits to real, evidence-backed defects. Do not turn expression-form differences into speculative behavior rewrites.
- Preserve the existing supported workflow target boundary: only `docs/workflows/新项目开发工作流/`.
- Preserve the same-version maintenance + patch-only stable mismatch gate model already defined in the source spec.
- Preserve Codex main-session-only analysis behavior and the non-Codex formal embed handoff boundary.
- Preserve the current repo distinction between:
  - `.trellis/` runtime truth
  - platform carrier layers
  - source repo evidence vs generated target-project evidence vs runtime command output
- Keep `.agents/` and `.claude/` entry surfaces behaviorally consistent in the same change.
- Do not introduce new unsupported platform scope, new remediation automation, or new task-routing semantics that are not already justified by the current spec/runtime.
- Run relevant skill validation before claiming completion.

## Acceptance Criteria (evolving)

- [ ] The repaired `workflow-audit` live skill wording no longer conflicts with the current Trellis runtime model and repo-local platform boundaries discovered in this repository.
- [ ] The task record distinguishes confirmed defects from inspected non-defects, and does not continue treating unconfirmed behavior-level drift as already proven.
- [ ] `.agents/skills/workflow-audit/SKILL.md` and `.claude/skills/workflow-audit/SKILL.md` remain behaviorally consistent after the change.
- [ ] Any behavior-affecting edits remain consistent with `.trellis/spec/skills/workflow-audit.md`, or the spec is updated in the same change if it was the stale surface.
- [ ] No new unsupported platform scope or false defect criteria are introduced.
- [ ] Relevant validation command(s) complete successfully, or any unrun validation is explicitly reported with reason.

## Definition of Done (team quality bar)

- Tests added/updated when the behavior contract requires it
- Lint / validation checks run for the changed skill surfaces
- Docs/notes updated if behavior or maintenance guidance changes
- Cross-layer sync checked across spec, live skill surfaces, and affected references/tests

## Out of Scope (explicit)

- Auditing or fixing the workflow product itself under `docs/workflows/新项目开发工作流/` unless current evidence proves the skill defect comes from that source contract
- Broad Trellis version-compatibility redesign; that belongs to `workflow-capability-audit`
- Introducing new platform support for `.kiro/` or `.qoder/` into `workflow-audit`
- Refactoring unrelated Trellis skills

## Technical Notes

- Cross-layer handoff for this task:
  - `.trellis/spec/skills/workflow-audit.md`
  - `->` live repo-local entry surfaces under `.agents/skills/workflow-audit/` and `.claude/skills/workflow-audit/`
  - `->` companion references/tests
  - `->` skill validation
- Current conclusion after static analysis:
  - Confirmed defect: frontmatter discovery/trigger wording on live entry surfaces, including routing disambiguation against `workflow-capability-audit`
  - Not currently confirmed as defect: broader behavior-contract rewrite, spec/live precision differences that remain semantically covered, reference/template/test coverage gaps
- Relevant repository/runtime references already inspected:
  - `.trellis/workflow.md`
  - `.trellis/config.yaml`
  - `.trellis/spec/skills/index.md`
  - `.trellis/spec/platforms/index.md`
  - `.trellis/spec/platforms/codex-workflow-behavior.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `.codex/config.toml`
  - `.codex/hooks.json`
  - `.claude/settings.json`
  - `.qoder/settings.json`
  - `.opencode/plugins/inject-workflow-state.js`
  - `.opencode/plugins/inject-subagent-context.js`

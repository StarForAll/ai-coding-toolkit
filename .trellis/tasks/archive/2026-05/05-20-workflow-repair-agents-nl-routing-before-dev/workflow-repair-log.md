---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-20-workflow-repair-agents-nl-routing-before-dev
issue-history-file: tmp/workflow-issues/0001.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-20T11:31:35+08:00
authorization-mode: authorized-to-repair
total-attempted: 4
total-succeeded: 4
total-failed: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-20-workflow-repair-agents-nl-routing-before-dev`
- Issue History File: `tmp/workflow-issues/0001.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-20T11:31:35+08:00`
- Authorization Mode: `authorized-to-repair`
- User Confirmation: `not-needed`

---

### WS-001: AGENTS NL routing advertises `/trellis:before-dev` even though no platform command is installed

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: no-history-found
- **Before State**: AGENTS NL routing row mapped dev-prep keywords to `/trellis:before-dev`; `命令映射.md` also exposed `/trellis:before-dev` as a framework entry, and `commands/test-first.md` still described a manual standalone slash-command path.
- **After State**: AGENTS NL routing now maps dev-prep to `/trellis:continue` and explicitly says no standalone `/trellis:before-dev` command is promised; `命令映射.md` and `commands/test-first.md` were aligned to the auto-before-dev wording.
- **Related Variants Covered**: `docs/workflows/新项目开发工作流/命令映射.md`, `docs/workflows/新项目开发工作流/commands/test-first.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: temp-project `AGENTS.md`, `.claude/commands/trellis/`, `.opencode/commands/trellis/`
- **Rationale**: The workflow already auto-runs before-dev through `continue`; the fix removes the dead explicit entry without changing real execution flow.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: `trellis-brainstorm` still references retired `/trellis:start` entry semantics

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-history-found
- **Before State**: `.claude/skills/trellis-brainstorm/SKILL.md` and `.opencode/skills/trellis-brainstorm/SKILL.md` were left on `/trellis:start` wording even though the shared `.agents/skills/trellis-brainstorm/SKILL.md` had already moved away from that entry model.
- **After State**: installer now patches platform-local brainstorm skill copies to reference `/trellis:brainstorm` and `/trellis:continue` route semantics instead of retired `/trellis:start`.
- **Related Variants Covered**: `.claude/skills/trellis-brainstorm/SKILL.md`, `.opencode/skills/trellis-brainstorm/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: temp-project `.agents/skills/trellis-brainstorm/SKILL.md`, `.claude/skills/trellis-brainstorm/SKILL.md`, `.opencode/skills/trellis-brainstorm/SKILL.md`
- **Rationale**: This closes the platform-carrier drift instead of relying on the shared skill carrier alone.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-003: OpenCode `trellis-meta` hook customization doc points to Claude hook paths

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/customize-local/change-hooks.md`
- **Change Type**: add
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-history-found
- **Before State**: the `trellis-meta-strong-gate/` patch tree did not include `customize-local/change-hooks.md`, so OpenCode inherited the stale baseline reference that sent readers to Claude hook paths.
- **After State**: added a strong-gate-aware `change-hooks.md` that documents Claude/OpenCode/Codex carrier files explicitly; the existing recursive `patch_trellis_meta_references()` flow now distributes it to Shared, Claude, and OpenCode carriers.
- **Related Variants Covered**: `.agents/skills/trellis-meta/references/customize-local/change-hooks.md`, `.claude/skills/trellis-meta/references/customize-local/change-hooks.md`, `.opencode/skills/trellis-meta/references/customize-local/change-hooks.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/platform-files/hooks-and-settings.md`
- **Rationale**: Reusing the existing patch tree is the minimal safe fix and prevents a partial overwrite set from persisting.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-004: Cross-layer thinking guide recommends nonexistent `/trellis:check-cross-layer` command

**Decision**: trellis-native
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-history-found
- **Before State**: the workflow did not patch the baseline `.trellis/spec/guides/cross-layer-thinking-guide.md`, so target projects kept the stale `/trellis:check-cross-layer` operator guidance.
- **After State**: installer now replaces that stale line with the current `/trellis:check` plus manual-scope guidance.
- **Related Variants Covered**: none
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/install-workflow.py` NL routing entry for cross-layer checks
- **Rationale**: The issue is trellis-native, so the fix lives entirely in a workflow-side post-install patch instead of editing upstream baseline sources.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

## Session Summary

| WS-NNN | Decision | Status | Verified |
|--------|----------|--------|----------|
| WS-001 | adopted | succeeded | yes |
| WS-002 | adopted | succeeded | yes |
| WS-003 | adopted | succeeded | yes |
| WS-004 | trellis-native | succeeded | yes |

### Unresolved Issues

- none

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify the repaired install surfaces end to end.
2. Or run `workflow-audit` if you want a broader post-repair validation pass.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0001.md`

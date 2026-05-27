---
repair-log-version: 1
protocol: workflow-scan-repair-v4
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-27-workflow-repair-2026-05-27-break-loop-doc-drift
issue-history-file: none
base-workflow-version: 0.1.2802
trellis-version: 0.5.17
repair-timestamp: 2026-05-27T21:48:42+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 3
total-succeeded: 3
total-failed: 0
total-reverted: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-27-workflow-repair-2026-05-27-break-loop-doc-drift`
- Issue History File: `none`
- Base Workflow Version: `0.1.2802`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-27T21:48:42+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-001: trellis-break-loop points mandatory follow-up work at missing guide and template targets

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: installed `trellis-break-loop` skill copies told readers to update a nonexistent `cross-platform-thinking-guide.md` target and to sync `.trellis/spec/` into a nonexistent `src/templates/markdown/spec/` mirror.
- **After State**: the installer now rewrites those instructions to use the real `cross-layer-thinking-guide.md` and to avoid assuming a template mirror.
- **Related Variants Covered**: `.claude/skills/trellis-break-loop/SKILL.md`, `.opencode/skills/trellis-break-loop/SKILL.md`, `.agents/skills/trellis-break-loop/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install fixtures, upgrade-check fixtures, closure fixtures
- **Rationale**: this removes the stale post-analysis path from every installed carrier instead of only fixing one copy.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: delivery surfaces reference a nonexistent native finish-work document

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/delivery.md`
- **Change Type**: modify
- **Root Cause Class**: stale declaration drift
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: the delivery close-out note pointed readers at `Trellis 原生 /finish-work.md`, which does not exist in the installed workflow surface.
- **After State**: the note now names the actual finish-work carriers for Claude/OpenCode and Codex.
- **Related Variants Covered**: `.claude/commands/trellis/delivery.md`, `.opencode/commands/trellis/delivery.md`, `.agents/skills/delivery/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/delivery.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install delivery fixture, existing-workflow upgrade-merge fixture, upgrade-check fixture
- **Rationale**: this keeps the native close-out handoff honest across all distributed carriers.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-003: trellis-check hard-codes `src/` as the code search root even though the temp project has no `src/`

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: installed `trellis-check` skill copies told readers to search `src/`, which misses the actual repo-root workflow surface in the embedded project.
- **After State**: the installer now rewrites that guidance to use a repo-root `rg` search.
- **Related Variants Covered**: `.claude/skills/trellis-check/SKILL.md`, `.opencode/skills/trellis-check/SKILL.md`, `.agents/skills/trellis-check/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install fixtures, upgrade-check fixtures, closure fixtures
- **Rationale**: this fixes the search root everywhere the check skill is installed and makes the drift detectable on upgrade.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-004: main-session-only strong-gate intentionally leaves visible subagent carriers as future-reenable surfaces across Claude, OpenCode, and Codex

**Decision**: manual-decision
**Report Classification**: design-debt

**Reason for ignoring**: the report describes an intentionally gated compatibility surface, not a confirmed defect that the current request must auto-repair. The workflow keeps these carriers available as a future-reenable path while the current contract remains main-session-only; the remaining choice is whether to keep, remove, or relabel them more explicitly.

---

## Session Summary

| WS-NNN | Decision | Status | Verified |
|--------|----------|--------|----------|
| WS-001 | adopted | succeeded | yes |
| WS-002 | adopted | succeeded | yes |
| WS-003 | adopted | succeeded | yes |
| WS-004 | manual-decision | not attempted | no |

### Unresolved Issues

- WS-004: intentionally gated subagent carriers still need an explicit product decision on future re-enable vs removal vs relabeling.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project if you want a regenerated report against the repaired workflow output.
2. Or run `workflow-audit` for a broader post-repair validation pass.
3. Manual review needed for: `WS-004`
4. Closure round artifacts:
   - `closure-round-1.md`
5. Legacy issue-history shadow (not used for cross-version repair decisions): `none`

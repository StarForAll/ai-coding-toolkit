---
repair-log-version: 1
protocol: workflow-scan-repair-v4
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-27-workflow-repair-2026-05-27-trellis-brainstorm-subagent-drift
issue-history-file: none
base-workflow-version: 0.1.2800
trellis-version: 0.5.17
repair-timestamp: 2026-05-27T15:17:55+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 1
total-succeeded: 1
total-failed: 0
total-reverted: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-27-workflow-repair-2026-05-27-trellis-brainstorm-subagent-drift`
- Issue History File: `none`
- Base Workflow Version: `0.1.2800`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-27T15:17:55+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-001: `trellis-brainstorm` still instructs sub-agent dispatch after main-session-only embed

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: `patch_platform_brainstorm_skills()` only rewrote brainstorm entry-routing text, while stale research-first carrier content still instructed `spawn a \`trellis-research\` sub-agent via the Task tool`
- **After State**: installer-side brainstorm skill patch now rewrites stale research-subagent guidance to a main-session-only research block and `upgrade-compat --merge` re-applies the same patch during upgrade convergence
- **Related Variants Covered**: `.claude/skills/trellis-brainstorm/SKILL.md`, `.opencode/skills/trellis-brainstorm/SKILL.md`, `.agents/skills/trellis-brainstorm/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: installed brainstorm carrier outputs on fresh install and on `upgrade-compat --merge`
- **Rationale**: keeps the source-of-truth in the workflow installer/upgrade path instead of editing repo-local carrier copies, and closes the exact stale guidance path reported by the temp-project scan

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

## Session Summary

| WS-NNN | Decision | Status | Verified |
|--------|----------|--------|----------|
| WS-001 | adopted | succeeded | yes |

### Unresolved Issues

- none

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project if you want a regenerated report against the repaired workflow output
2. Run `workflow-audit` if you want a broader version-gated audit after this focused repair
3. Manual review needed for: `none`
4. Closure round artifacts:
   - `closure-round-1.md`
5. Legacy issue-history shadow (not used for cross-version repair decisions): `none`

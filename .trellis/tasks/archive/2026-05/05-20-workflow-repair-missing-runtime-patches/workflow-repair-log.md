---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-20-workflow-repair-missing-runtime-patches
issue-history-file: tmp/workflow-issues/0005.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-20T22:41:59+08:00
authorization-mode: authorized-to-repair
continuation-mode: auto-follow-through
total-attempted: 1
total-succeeded: 1
total-failed: 0
total-reverted: 0
total-skipped: 7
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-20-workflow-repair-missing-runtime-patches`
- Issue History File: `tmp/workflow-issues/0005.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-20T22:41:59+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `auto-follow-through`
- Auto Follow-Through Outcome: `stopped-with-blocker: no trellis finish-work command surface is available in this session, so auto close-out cannot continue safely`
- User Confirmation: `not-needed`

---

### WS-001: Two critical_runtime_patches listed but missing from disk

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: install record and runtime validator exposed `task-status-view-strong-gate` and `workflow-phase-strong-gate` as critical runtime patch names, but the distributed helper-script set only shipped `patch-workflow-phase.py` and inlined the task-status patch logic inside installer code.
- **After State**: the workflow source now ships `patch-task-status-view-strong-gate.py` and `patch-workflow-phase-strong-gate.py`, and installer / upgrade flows load those helper surfaces directly.
- **Related Variants Covered**: `install-workflow.py`, `upgrade-compat.py`, `commands/shell/patch-workflow-phase.py`, `commands/shell/test_workflow_state.py`, `commands/test_workflow_installers.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`; `docs/workflows/新项目开发工作流/commands/install-workflow.py`; `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`; `docs/workflows/新项目开发工作流/commands/shell/patch-task-status-view-strong-gate.py`; `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase-strong-gate.py`; `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`; distributed helper deployment via `HELPER_SCRIPTS`; `critical_runtime_patches` install-record assertions
- **Rationale**: aligning runtime patch capability names with real distributed helper-script carriers removes the scan-visible false P0 while preserving the existing strong-gate runtime behavior.

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

- WS-003: `trellis-spec-bootstarp` typo remains a manual-decision because it appears to be the current shared/upstream canonical carrier name rather than a workflow-local one-off typo.
- WS-002, WS-004, WS-005, WS-006, WS-007, WS-008: re-checked as already-fixed or by-design; no repair execution was justified.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to confirm the helper-script / install-record alignment no longer reports missing critical runtime patches.
2. If the `trellis-spec-bootstarp` rename is still desired, handle it as a dedicated cross-carrier rename task rather than as a narrow workflow-repair follow-up.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0005.md`

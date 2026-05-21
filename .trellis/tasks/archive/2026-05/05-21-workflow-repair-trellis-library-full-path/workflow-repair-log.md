---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-trellis-library-full-path
issue-history-file: tmp/workflow-issues/0006.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T00:47:15+08:00
authorization-mode: authorized-to-repair
continuation-mode: auto-follow-through
total-attempted: 1
total-succeeded: 1
total-failed: 0
total-reverted: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-21-workflow-repair-trellis-library-full-path`
- Issue History File: `tmp/workflow-issues/0006.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T00:47:15+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `auto-follow-through`
- Auto Follow-Through Outcome: `reached-task-close`
- User Confirmation: `not-needed`

---

### WS-001: design.md and plan.md reference absent trellis-library/cli.py

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- **Change Type**: modify
- **Root Cause Class**: wrong runtime assumption
- **Recurrence Status**: first-seen
- **Before State**: `prepare_command_content()` kept target-facing `trellis-library` references unchanged, so installed `design.md` and `plan.md` still implied a target-project-local `trellis-library/` directory.
- **After State**: `prepare_command_content()` rewrites target-facing `trellis-library/cli.py` calls to the host-side absolute CLI path and rewrites the `plan.md` prerequisite wording to reference the host-side `trellis-library` directory explicitly.
- **Related Variants Covered**: target-facing `design.md` and `plan.md` carriers plus install summary prompt strings that instructed users to run the same stale relative command form
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: deployed command rendering through `prepare_command_content()` and install-time requirements-foundation import path resolution
- **Rationale**: the temp-project failure came from deployed guidance assuming `trellis-library/` existed inside the target project. The installer already executes the library CLI from the authoring repo root, so the repair aligned every user-facing target-project carrier with that existing host-side contract instead of hardcoding absolute paths into source command docs.

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

- This focused repair run only addressed the `trellis-library` path finding from `WORKFLOW_QUESTIONS.md`; WS-002 through WS-009 remain outside the scope of this execution.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify the repaired target-facing `design` / `plan` carriers.
2. Continue consuming the remaining findings from `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` in later `workflow-repair` runs as needed.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0006.md`

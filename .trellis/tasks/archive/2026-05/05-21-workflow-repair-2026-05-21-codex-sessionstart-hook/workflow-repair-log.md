---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-2026-05-21-codex-sessionstart-hook
issue-history-file: tmp/workflow-issues/0010.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T17:48:03+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 3
total-succeeded: 3
total-failed: 0
total-reverted: 0
total-skipped: 6
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-21-workflow-repair-2026-05-21-codex-sessionstart-hook`
- Issue History File: `tmp/workflow-issues/0010.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T17:48:03+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-005: Patch scripts lack --help support and treat --help as file path argument

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
- **Change Type**: modify
- **Root Cause Class**: script CLI inconsistency
- **Recurrence Status**: no-history-found
- **Before State**: six patch helpers parsed positional paths through `len(sys.argv)` and `sys.argv[1]`, so `--help` never surfaced standard usage
- **After State**: all six patch helpers expose `argparse` parsers with standard `-h/--help` while preserving the same positional target semantics
- **Related Variants Covered**: `patch-task-start-strong-gate.py`, `patch-task-create-preserve-active.py`, `patch-task-status-view-strong-gate.py`, `patch-workflow-phase.py`, `patch-workflow-phase-strong-gate.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`, `docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py`, `docs/workflows/新项目开发工作流/commands/shell/patch-task-create-preserve-active.py`, `docs/workflows/新项目开发工作流/commands/shell/patch-task-status-view-strong-gate.py`, `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase.py`, `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase-strong-gate.py`, `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`, `docs/workflows/新项目开发工作流/commands/shell/plan-validate.py`
- **Rationale**: aligns patch helpers with repo script conventions and removes the operator-facing `--help` footgun without changing patch behavior

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-008: AGENTS.md references legacy /trellis:start but command is unreachable on Claude/OpenCode

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: `_NL_ROUTING_SECTION` and the install summary still mentioned legacy `/trellis:start` on user-facing fresh-install entry surfaces
- **After State**: generated AGENTS NL routing and install summary now point only to current public entry surfaces (`/trellis:continue` or skill/natural-language routing)
- **Related Variants Covered**: NL routing header note, continue fallback row, ambiguity fallback note, installer success summary lines
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: installed target `AGENTS.md` NL routing output through installer regression tests
- **Rationale**: removes a dead-entry hint from the current user-facing routing surface while keeping legacy compatibility logic in maintainer-only upgrade paths

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-009: patch-workflow-phase.py destroys get_step() docstring after patching

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase.py`
- **Change Type**: modify
- **Root Cause Class**: unsafe patch insertion point
- **Recurrence Status**: no-history-found
- **Before State**: patch insertion always happened immediately after `def get_step(...)`, so any existing docstring lost its `__doc__` position
- **After State**: the patch uses AST structure to locate `get_step()` and inserts after the docstring when one exists, otherwise after the function header
- **Related Variants Covered**: wrapper verification via `patch-workflow-phase-strong-gate.py` help path and dedicated docstring preservation test
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`, `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`
- **Contract Surfaces Verified**: patched fixture import and `get_step.__doc__` preservation
- **Rationale**: keeps the strong-gate behavior unchanged while preventing documentation/introspection regression in patched targets

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
| WS-005 | adopted | succeeded | yes |
| WS-008 | adopted | succeeded | yes |
| WS-009 | adopted | succeeded | yes |

### Unresolved Issues

- WS-003: `trellis-spec-bootstarp` exists in the temp project but has no matching source-of-truth inside `docs/workflows/新项目开发工作流/`; a workflow-local alias/rename would need an explicit compatibility decision
- WS-001 / WS-002 / WS-004 / WS-006 / WS-007: verified as ignored because they reflect optional/manual/native carrier boundaries or restore surfaces rather than actionable workflow-source drift

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify the repaired source against a regenerated target
2. Run `workflow-audit` if you want a broader version-gated audit after this repair batch
3. Manual review needed for: `WS-003`
4. The current run's issue-history summary was written to: `tmp/workflow-issues/0010.md`

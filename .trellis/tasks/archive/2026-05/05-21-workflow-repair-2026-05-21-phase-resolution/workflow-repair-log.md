---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-2026-05-21-phase-resolution
issue-history-file: tmp/workflow-issues/0009.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T17:00:04+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 2
total-succeeded: 2
total-failed: 0
total-reverted: 0
total-skipped: 10
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-21-workflow-repair-2026-05-21-phase-resolution`
- Issue History File: `tmp/workflow-issues/0009.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T17:00:04+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-001: Patched workflow.md breaks get_context.py --mode phase --step resolution

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- **Change Type**: `modify`
- **Root Cause Class**: `partial cross-file update`
- **Recurrence Status**: `no-history-found`
- **Before State**: Phase Index only exposed the strong-gate stage chain and transition table; no `#### X.Y` compatibility headings remained for baseline `get_context.py --mode phase --step`
- **After State**: Added a `Baseline Step Compatibility` section with numbered `#### 1.0` through `#### 3.5` headings while keeping the strong-gate stage contract unchanged
- **Related Variants Covered**: `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- **Rationale**: Restores baseline step-reader compatibility without reintroducing the old Plan/Execute/Finish state machine or changing `workflow-state.py` routing

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: .trellis/library-assets/ directory missing but referenced by library-lock.yaml

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: `modify`
- **Root Cause Class**: `incomplete installer patch`
- **Recurrence Status**: `no-history-found`
- **Before State**: `import_requirements_foundation()` called `trellis-library cli assemble --pack pack.requirements-discovery-foundation --auto` without `--include-examples`, while `library-lock.yaml` still recorded example assets under `.trellis/library-assets/**`
- **After State**: The installer now imports the requirements foundation with `--include-examples`; audit extra specs also include the example asset paths so install-time output and managed-audit expectations match
- **Related Variants Covered**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/workflow_assets.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- **Rationale**: Aligns the installer's actual copied output with the lock record and the workflow-managed audit surface

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
| WS-002 | adopted | succeeded | yes |

### Unresolved Issues

- WS-003: `trellis-spec-bootstarp` typo is real but remains a cross-carrier rename / alias decision outside this workflow-local repair scope
- WS-006: template-hash drift is real but needs a separate safe design that distinguishes workflow-managed overwrites from user local customizations
- WS-012: executable permissions on Trellis baseline common modules are real but low-priority and not a safe workflow-managed patch by default

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to confirm `WS-001` and `WS-002` no longer reproduce.
2. If you want to pursue `WS-006`, split it into a dedicated template-hash contract task covering both install and upgrade paths.
3. Manual review remains needed for: `WS-003`, `WS-006`, `WS-012`.
4. The current run's issue-history summary was written to: `tmp/workflow-issues/0009.md`.

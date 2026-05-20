---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-20-workflow-repair-2026-05-20-broken-carrier-links
issue-history-file: tmp/workflow-issues/0002.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-20T12:26:53+08:00
authorization-mode: authorized-to-repair
total-attempted: 2
total-succeeded: 2
total-failed: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-20-workflow-repair-2026-05-20-broken-carrier-links`
- Issue History File: `tmp/workflow-issues/0002.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-20T12:26:53+08:00`
- Authorization Mode: `authorized-to-repair`
- User Confirmation: `not-needed`

---

### WS-001: Installed workflow carriers reference `.trellis/workflow-docs/` with broken relative paths

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- **Change Type**: modify
- **Root Cause Class**: wrong runtime assumption
- **Recurrence Status**: first-seen
- **Before State**: `prepare_command_content()` rewrote execution-card links to `.trellis/workflow-docs/...`, which Markdown resolved relative to nested carrier directories.
- **After State**: execution-card links are rewritten to `../../../.trellis/workflow-docs/...`, matching the shared skill and distributed command carrier depth.
- **Related Variants Covered**: distributed stage carriers for `feasibility`, `brainstorm`, `design`, `plan`, `test-first`, `project-audit`, `check`, `review-gate`, and `delivery`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`; `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`; deployed `.claude/commands/trellis/*.md`; deployed `.agents/skills/*/SKILL.md`
- **Rationale**: the source rewrite rule was the single shared generator for all affected carriers, so fixing it once and extending regression coverage closes the entire path-resolution class.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: Codex carrier guidance conflicts with the critical patch contract for `session-start.py`

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: Codex docs described `hooks.json -> inject-workflow-state.py` as the main carrier and treated `session-start.py` as optional, but runtime validation and some maintainer docs still treated Codex `session-start.py` as an unconditional critical patch.
- **After State**: Codex contract is aligned to `hooks.json + inject-workflow-state.py` as the required carrier; `session-start.py` remains patchable when present and becomes mandatory only when the target project actually wires that startup surface.
- **Related Variants Covered**: `workflow-state.py`, `upgrade-compat.py`, trellis-meta hook customization docs, Codex maintenance matrices/checklists, and runtime/install regression tests
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`; `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`; `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`; `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/customize-local/change-hooks.md`; `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`; `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`; `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`; `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/codex/README.md`; `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/local-architecture/context-injection.md`; `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/platform-files/hooks-and-settings.md`
- **Rationale**: the previous narrow doc fix left validator and upgrade-check semantics behind; this broader repair closes the whole contract surface and prevents the same Codex hook drift from reappearing.

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

- none

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify the installed carriers and Codex hook contract end to end.
2. Or run `workflow-audit` for a broader source-vs-installed workflow consistency pass.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0002.md`

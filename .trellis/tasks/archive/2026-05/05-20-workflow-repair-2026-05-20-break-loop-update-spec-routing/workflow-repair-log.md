---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-20-workflow-repair-2026-05-20-break-loop-update-spec-routing
issue-history-file: tmp/workflow-issues/0004.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-20T14:32:51+08:00
authorization-mode: authorized-to-repair
total-attempted: 1
total-succeeded: 1
total-failed: 0
total-skipped: 2
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-20-workflow-repair-2026-05-20-break-loop-update-spec-routing`
- Issue History File: `tmp/workflow-issues/0004.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-20T14:32:51+08:00`
- Authorization Mode: `authorized-to-repair`
- User Confirmation: `not-needed`

---

### WS-001: AGENTS.md references `/trellis:break-loop` and `/trellis:update-spec` as commands but no command carriers exist

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: installer-generated NL routing, delivery guidance, command mapping, and mindmap still advertised Claude/OpenCode `/trellis:break-loop` and `/trellis:update-spec`; brainstorm skill patch only matched a fully stale related-command block.
- **After State**: all user-facing workflow surfaces now route Claude/OpenCode users to `trellis-break-loop` / `trellis-update-spec` skills instead of nonexistent slash commands; brainstorm skill patch now also fixes partially updated stale blocks.
- **Related Variants Covered**: same dead-entry class across AGENTS NL routing generation, command mapping, delivery next-step guidance, workflow mindmap, and platform brainstorm skill patch/test
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/命令映射.md`, `docs/workflows/新项目开发工作流/commands/delivery.md`, `docs/workflows/新项目开发工作流/工作流思维导图.html`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.claude/skills/trellis-break-loop/SKILL.md`, `/tmp/trellis-0.5.17-2/.claude/skills/trellis-update-spec/SKILL.md`, `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-break-loop/SKILL.md`, `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-update-spec/SKILL.md`
- **Rationale**: the installed workflow already provides skill carriers for these capabilities; the failure was the documentation/routing contract falsely promising slash-command carriers that are never deployed.

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
| WS-002 | ignored | skipped | n/a |
| WS-003 | ignored | skipped | n/a |

### Unresolved Issues

- none requiring workflow-source repair; WS-002 and WS-003 were rechecked and recorded as ignored

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to confirm the repaired routing text in installed artifacts.
2. If broader workflow regression coverage is needed, run `workflow-audit`.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0004.md`

---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-ws001-ws004-boundaries
issue-history-file: tmp/workflow-issues/0007.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T14:25:21+08:00
authorization-mode: authorized-to-repair
continuation-mode: auto-follow-through
total-attempted: 7
total-succeeded: 7
total-failed: 0
total-reverted: 0
total-skipped: 10
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-21-workflow-repair-ws001-ws004-boundaries`
- Issue History File: `tmp/workflow-issues/0007.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T14:25:21+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `auto-follow-through`
- Auto Follow-Through Outcome: `reached-task-close`
- User Confirmation: `not-needed`

---

### WS-001: Missing trellis-continue/finish-work/start skills in Claude and OpenCode skill trees

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/claude/README.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: Claude/OpenCode formal entry and shared-skill asymmetry were mentioned, but the docs did not explicitly say that `.claude/skills/` does not need to mirror `trellis-start` / `trellis-continue` / `trellis-finish-work`.
- **After State**: The Claude README now states that those Trellis baseline entries stay in the command carrier and that missing mirrors in `.claude/skills/` are expected.
- **Related Variants Covered**: `commands/opencode/README.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Updated**: `commands/claude/README.md`, `commands/opencode/README.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.claude/commands/trellis/continue.md`, `/tmp/trellis-0.5.17-2/.opencode/commands/trellis/continue.md`, `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md`
- **Rationale**: The installed layout is intentional; the repair closes the documentation gap that kept making the same layout look like drift.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: Empty .codex/skills/ directory despite patched_codex_skills claim

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/codex/README.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: The Codex docs already described `.codex/skills/` as a secondary carrier, but the "empty is normal" rule was not stated bluntly enough.
- **After State**: The Codex README and boundary docs now say that `trellis-start` / `trellis-continue` / `trellis-finish-work` should be checked in `.agents/skills/` first and that an empty `.codex/skills/` directory is not a shared-workflow defect.
- **Related Variants Covered**: `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Updated**: `commands/codex/README.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Verified**: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `/tmp/trellis-0.5.17-2/.codex/skills/`
- **Rationale**: The install record already points to shared-skill semantics; the repair makes the same interpretation explicit to readers and auditors.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-003: Missing inject-subagent-context hook in Codex carrier

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/codex/README.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: Codex inline/no-subagent rules existed, but the docs did not explicitly say that Codex does not require a Claude-style `inject-subagent-context` hook carrier.
- **After State**: Codex and boundary docs now state that the main contract is `inline + turn hook`, and delegated/non-inline paths use agent/self-loading rather than a required `.codex/hooks/inject-subagent-context.py`.
- **Related Variants Covered**: `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Updated**: `commands/codex/README.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.codex/hooks.json`, `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py`, `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/local-architecture/context-injection.md`
- **Rationale**: The fix prevents platform-shape comparison from being mistaken for a missing runtime requirement.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-004: Codex hooks.json does not wire session-start hook

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/codex/README.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: The docs said not to hard-code a `SessionStart` dependency, but they did not clearly connect that rule to "start is hook-driven and turn-level hook is the normal Codex path".
- **After State**: The Codex docs and checklist now say that startup routing depends on the hook chain already wired by the current CLI; `session-start.py` is only a startup helper when a project explicitly wires it.
- **Related Variants Covered**: `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Updated**: `commands/codex/README.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.codex/hooks.json`, `/tmp/trellis-0.5.17-2/.codex/hooks/session-start.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Rationale**: The repair makes the optional startup surface explicit and aligns the reader model with the actual turn-hook-first contract.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-006: Execution card references four nonexistent documents

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: first-seen
- **Before State**: The card referenced source-repo file names that do not exist in an installed target project.
- **After State**: The card now points to target-project surfaces that do exist at runtime: `.trellis/workflow.md`, the current CLI's `continue`/`trellis-continue`, the current CLI's `delivery` entry, and `AGENTS.md`.
- **Related Variants Covered**: same file also corrected for stale numbered-section references
- **Contract Surfaces Updated**: `需求变更管理执行卡.md`, `commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.trellis/workflow-docs/需求变更管理执行卡.md`
- **Rationale**: The change separates source-authoring references from installed-target runtime references.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-007: Missing [workflow-state:needs-init] breadcrumb block

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: first-seen
- **Before State**: The task-mechanism contract mentioned `needs-init`, but the generated workflow patch had no matching breadcrumb block.
- **After State**: The workflow patch now includes a dedicated `[workflow-state:needs-init]` block, and installer regression tests assert that the deployed `.trellis/workflow.md` contains it.
- **Related Variants Covered**: `commands/test_workflow_installers.py`
- **Contract Surfaces Updated**: `commands/workflow-patch-projectization.md`, `commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`, `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- **Rationale**: The patch realigns a documented runtime route output with the actual injected prompt surface.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-008: Stale section references in 需求变更管理执行卡.md

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: first-seen
- **Before State**: The card still referred to old numbered sections such as `§2.4` and `§2.5`, plus the old `start`-style rollback wording.
- **After State**: The card now describes the current strong-gate workflow in stage terms: "需求冻结之后", "后续执行阶段", and `continue` / `trellis-continue` re-entry for implementation-only changes.
- **Related Variants Covered**: same file's runtime reference cleanup
- **Contract Surfaces Updated**: `需求变更管理执行卡.md`, `commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: `/tmp/trellis-0.5.17-2/.trellis/workflow-docs/需求变更管理执行卡.md`
- **Rationale**: Removing stale numbered anchors prevents readers from following a workflow shape that no longer exists.

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
| WS-004 | adopted | succeeded | yes |
| WS-006 | adopted | succeeded | yes |
| WS-007 | adopted | succeeded | yes |
| WS-008 | adopted | succeeded | yes |

### Unresolved Issues

- WS-005, WS-009, WS-010, WS-011, WS-012, WS-013, WS-014, WS-015, WS-016, WS-017: rechecked and recorded as ignored in this run because the temp-project symptom was either intentional, stale, Trellis-native, or based on a wrong runtime assumption rather than a safe workflow-source defect.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to confirm the clarified carrier boundaries stop retriggering `WS-001` to `WS-004`.
2. If execution-card-only issues still recur, inspect the installed `.trellis/workflow-docs/` copies before widening the repair scope.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0007.md`

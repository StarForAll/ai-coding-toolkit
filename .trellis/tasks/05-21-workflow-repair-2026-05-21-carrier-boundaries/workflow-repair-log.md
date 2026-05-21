---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-2026-05-21-carrier-boundaries
issue-history-file: tmp/workflow-issues/0008.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T15:54:44+08:00
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
- Repair Task: `.trellis/tasks/05-21-workflow-repair-2026-05-21-carrier-boundaries`
- Issue History File: `tmp/workflow-issues/0008.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T15:54:44+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-003: Skills asymmetric across carriers — 17 skills missing from .claude/skills/ and .opencode/skills/

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: multiple workflow docs under `docs/workflows/新项目开发工作流/`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: boundary docs and platform README files already described Claude/OpenCode formal-entry differences, but they did not state the availability-judgment order explicitly enough to stop future scans from treating command-carried stages as "missing skills".
- **After State**: maintainer docs and platform README files now say Claude/OpenCode availability must be judged from `commands/trellis/` first, then from platform/shared skill discovery surfaces, and that missing mirrored skill directories alone do not prove a workflow gap.
- **Related Variants Covered**: Claude/OpenCode command-carrier vs skill-carrier boundary across maintainer docs, walkthrough docs, and platform README files
- **Contract Surfaces Updated**:
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
- **Contract Surfaces Verified**: none
- **Rationale**: the temp project already exposes Claude/OpenCode stage capability mainly through `.claude/commands/trellis/` and `.opencode/commands/trellis/`; the missing closure was documentation of that judgment rule, not missing runtime assets.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-006: Backup-original artifacts remain across multiple carriers

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: multiple workflow docs under `docs/workflows/新项目开发工作流/`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: source docs mentioned backup and restore behavior in scattered places, but they did not say clearly enough that `.backup-original/` is an intentional restore surface whose presence alone is not a residual defect.
- **After State**: maintainer docs, workflow overviews, and platform README files now instruct reviewers to treat `.backup-original/` as a restore surface by default and only escalate when the active entry is missing, the restore pair is broken, or the backup is being mistaken for current behavior.
- **Related Variants Covered**: `.backup-original/` restore-surface semantics across shared maintainer docs, platform README files, and general workflow docs
- **Contract Surfaces Updated**:
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
- **Contract Surfaces Verified**: none
- **Rationale**: the temp project keeps `.backup-original/` across skills, commands, and `.trellis/` as a recovery surface; the recurrence came from missing explicit review guidance, not from an unsafe runtime residue.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-008: Codex carrier incomplete — no commands directory, empty skills directory

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: multiple workflow docs under `docs/workflows/新项目开发工作流/`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: docs already said `.agents/skills/` was the Codex shared primary carrier and `.codex/skills/` was secondary, but they did not state forcefully enough that `.codex/commands/` is not part of the formal Codex entry model and that an empty `.codex/skills/` is not a standalone defect.
- **After State**: maintainer docs, the Codex README, and general workflow docs now require Codex checks to evaluate `.agents/skills/` first, then hooks and agents, then `.codex/skills/` as a secondary carrier; they also say missing `.codex/commands/` is not an anomaly by itself.
- **Related Variants Covered**: Codex primary-vs-secondary carrier boundary across maintainer docs, Codex platform README, and general workflow docs
- **Contract Surfaces Updated**:
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
- **Contract Surfaces Verified**: none
- **Rationale**: the temp project already provides Codex workflow integration through `.agents/skills/`, `.codex/hooks*`, and `.codex/agents/*`; the recurring false positive came from an incomplete documentation rule, not from a missing Codex command directory.

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
| WS-003 | adopted | succeeded | yes |
| WS-006 | adopted | succeeded | yes |
| WS-008 | adopted | succeeded | yes |

### Unresolved Issues

- Other findings in `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` remained out of scope for this focused repair run.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify the repeated carrier-boundary findings stop recurring.
2. If broader runtime or version-drift assurance is needed, run `workflow-capability-audit`.
3. The current run's issue-history summary was written to: `tmp/workflow-issues/0008.md`

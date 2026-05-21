---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-21-workflow-repair-2026-05-21-codex-hooks-json
issue-history-file: tmp/workflow-issues/0011.md
trellis-version: 0.5.17
repair-timestamp: 2026-05-21T19:40:46+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 6
total-succeeded: 6
total-failed: 0
total-reverted: 0
total-skipped: 18
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-21-workflow-repair-2026-05-21-codex-hooks-json`
- Issue History File: `tmp/workflow-issues/0011.md`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-21T19:40:46+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-004: Execution cards not cross-referenced from workflow.md breadcrumb blocks

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: no-history-found
- **Before State**: strong-gate feasibility / brainstorm / plan / delivery breadcrumbs described stage flow but did not consistently surface the execution-card obligations that the installed workflow relies on.
- **After State**: the breadcrumb patch now explicitly carries ownership-proof and requirement-change obligations into feasibility, brainstorm, plan, and delivery stage guidance.
- **Related Variants Covered**: `workflow-state:feasibility`, `workflow-state:brainstorm`, `workflow-state:plan`, `workflow-state:delivery`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: installed `.trellis/workflow.md` rendering via installer regression
- **Rationale**: this closes the gap between no-task routing, stage breadcrumbs, and execution-card-driven stage obligations so agents do not miss them on re-entry.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-007: JS hook injection hardcodes PYTHON_CMD to "python3"

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
- **Change Type**: modify
- **Root Cause Class**: wrong runtime assumption
- **Recurrence Status**: no-history-found
- **Before State**: JS hook patch templates and related runtime-contract checks treated `python3` as a fixed interpreter string.
- **After State**: JS hook patch templates now prefer `process.env.TRELLIS_PYTHON || "python3"`, and the related validator/test surfaces were aligned to the same contract.
- **Related Variants Covered**: installer/runtime contract checks in `upgrade-compat.py`, `workflow-state.py`, `test_workflow_installers.py`, `test_workflow_state.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`, `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- **Contract Surfaces Verified**: injected OpenCode/Codex hook runtime content through installer/unit tests
- **Rationale**: this keeps the JS-side runtime path flexible without breaking existing fallback behavior, and removes the hardcoded interpreter assumption that diverged from the Python-side contract.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-010: check-quality.py uses shell=True in subprocess calls

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
- **Change Type**: modify
- **Root Cause Class**: unsafe fixed subprocess invocation
- **Recurrence Status**: no-history-found
- **Before State**: the script used `shell=True` even for fixed git inspection commands.
- **After State**: fixed git queries now go through list-form subprocess calls via `run_git_query()`, while user-confirmed free-form commands remain unchanged.
- **Related Variants Covered**: unit coverage in `test_check_quality.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`, `docs/workflows/新项目开发工作流/commands/shell/test_check_quality.py`
- **Contract Surfaces Verified**: direct unit test on `main()` with mocked `run_git_query()`
- **Rationale**: this removes unnecessary `shell=True` usage from the fixed git path without changing the script's project-confirmed command model.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-016: 需求变更管理执行卡 references non-existent docs/ path

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`
- **Change Type**: modify
- **Root Cause Class**: ambiguous runtime document assumption
- **Recurrence Status**: no-history-found
- **Before State**: the card referred to `docs/requirements/customer-facing-prd.md` as if it were always already present.
- **After State**: the card now states that the target project's formal requirements path may need to be created or backfilled at runtime before the change is synced.
- **Related Variants Covered**: none
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: deployed workflow-doc content through installer regression
- **Rationale**: this removes the misleading assumption that the path must already exist at project start while preserving the intended target-project document contract.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-017 / WS-018: brainstorm entry naming and watermark-field obligations drift

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- **Change Type**: modify
- **Root Cause Class**: partial cross-file update
- **Recurrence Status**: repeated-after-prior-repair
- **Before State**: no-task routing still used `trellis-brainstorm` wording while the strong-gate breadcrumb used `/trellis:brainstorm`, and the breadcrumb did not restate the personal-profile `source_watermark_*` / `ownership_proof_required` bootstrap obligation.
- **After State**: the no-task path now uses the same `/trellis:brainstorm` wording as the stage breadcrumb, and brainstorm guidance explicitly restates the watermark/ownership fields required before leaving the stage.
- **Related Variants Covered**: `workflow-state:no_task`, `workflow-state:brainstorm`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: installed `.trellis/workflow.md` rendering via installer regression
- **Rationale**: this closes a repeat-trigger path where agents entering through different route surfaces received inconsistent brainstorm instructions.

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: passed
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-020: Execution card script paths omit ./ prefix used in workflow.md

**Decision**: adopted
**Status**: succeeded

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md`
- **Change Type**: modify
- **Root Cause Class**: documentation path convention drift
- **Recurrence Status**: no-history-found
- **Before State**: the execution card used `.trellis/scripts/workflow/...` command examples while the workflow docs generally use `./.trellis/...`.
- **After State**: the execution card command examples now use the same `./.trellis/...` prefix as the main workflow docs.
- **Related Variants Covered**: none
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: deployed workflow-doc content through installer regression
- **Rationale**: this standardizes the target-project command examples with the prevailing workflow doc convention and removes a small but recurring authoring drift.

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
| WS-004 | adopted | succeeded | yes |
| WS-007 | adopted | succeeded | yes |
| WS-010 | adopted | succeeded | yes |
| WS-016 | adopted | succeeded | yes |
| WS-017 / WS-018 | adopted | succeeded | yes |
| WS-020 | adopted | succeeded | yes |

### Unresolved Issues

- WS-003: `trellis-spec-bootstarp` typo remains a broader naming / compatibility decision.
- WS-006: duplicated Codex TOML context sections still need Trellis-native renderer/source confirmation before safe repair.
- WS-011 / WS-012: shared lineage helper extraction and return-value unification remain broader script API cleanup, not minimal repair.
- WS-023: temp-project plugin reference observed, but no in-scope workflow source patch surface was confirmed in `docs/workflows/新项目开发工作流/`.

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to confirm the repaired breadcrumb/runtime/doc contracts stop recurring.
2. Run `workflow-audit` if you want a broader version-gated revalidation after this repair batch.
3. Manual review needed for: `WS-003`, `WS-006`, `WS-011`, `WS-012`
4. The current run's issue-history summary was written to: `tmp/workflow-issues/0011.md`

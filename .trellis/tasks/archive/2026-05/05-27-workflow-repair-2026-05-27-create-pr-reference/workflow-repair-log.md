---
repair-log-version: 1
protocol: workflow-scan-repair-v4
source-report: /tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md
repair-task: .trellis/tasks/05-27-workflow-repair-2026-05-27-create-pr-reference
issue-history-file: none
base-workflow-version: 0.1.2800
trellis-version: 0.5.17
repair-timestamp: 2026-05-27T17:08:41+08:00
authorization-mode: authorized-to-repair
continuation-mode: stop-after-summary
total-attempted: 4
total-succeeded: 4
total-failed: 0
total-reverted: 0
total-skipped: 0
---

# Workflow Repair Log

## Session Info

- Source Report: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- Repair Task: `.trellis/tasks/05-27-workflow-repair-2026-05-27-create-pr-reference`
- Issue History File: `none`
- Base Workflow Version: `0.1.2800`
- Trellis Version: `0.5.17`
- Repair Time: `2026-05-27T17:08:41+08:00`
- Authorization Mode: `authorized-to-repair`
- Continuation Mode: `stop-after-summary`
- Auto Follow-Through Outcome: `not-applicable`
- User Confirmation: `not-needed`

---

### WS-001: `.trellis/workflow.md` quick command list still advertises removed `task.py create-pr`

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: workflow doc projectization refresh only replaced the task-mechanism paragraph, so the baseline `# PR creation` quick reference survived into installed `.trellis/workflow.md`, and upgrade checks did not flag it
- **After State**: workflow doc refresh now strips the stale `task.py create-pr` quick-reference block while preserving the rest of the quick command list, and upgrade drift checks now classify the same stale line as a workflow doc contract issue
- **Related Variants Covered**: `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install `build_workflow_content()` output and installed `.trellis/workflow.md`
- **Rationale**: keeps the embedded workflow doc aligned with the real `task.py` runtime surface for the pinned Trellis baseline

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-002: OpenCode sub-agent gate still parses legacy route text instead of current JSON route output

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`
- **Change Type**: modify
- **Root Cause Class**: wrong runtime assumption
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: the injected OpenCode helper only parsed line-oriented `Stage:` / `Action:` / `Target:` text, so current JSON route output collapsed into empty metadata
- **After State**: the helper now parses JSON route output first, normalizes blocker/warning arrays, and falls back to the legacy line parser only when JSON is not available; `upgrade-compat --check` now also rejects the old marker-only line-parser variant instead of silently passing it
- **Related Variants Covered**: `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`, `docs/workflows/新项目开发工作流/commands/shell/test_patch_helpers.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- **Contract Surfaces Verified**: helper-level patch fixture, installed `.opencode/plugins/inject-subagent-context.js` output expectations, and `upgrade-compat --check` drift detection
- **Rationale**: matches the current `workflow-state.py route` contract without breaking older text-form route output

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-003: Claude/OpenCode `trellis-update-spec` skills point to `/trellis:update-spec` and `/trellis:break-loop` commands that are not installed

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- **Change Type**: modify
- **Root Cause Class**: incomplete installer patch
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: install/upgrade logic had no post-processing step for `trellis-update-spec` skill entry text, so platform-local and shared installed skills kept advertising removed command surfaces
- **After State**: install and upgrade now rewrite the `trellis-update-spec` relationship section to real skill entry surfaces for Claude and OpenCode, while opportunistically repairing the shared Codex-facing copy when that carrier exists; `upgrade-compat --check` now flags stale update-spec wording on any of those existing surfaces
- **Related Variants Covered**: installed `.claude/skills/trellis-update-spec/SKILL.md`, `.opencode/skills/trellis-update-spec/SKILL.md`, `.agents/skills/trellis-update-spec/SKILL.md`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/install-workflow.py`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install skill refresh tests, existing-workflow upgrade-merge skill refresh tests, and `upgrade-compat --check` stale-skill detection
- **Rationale**: aligns every installed CLI surface with the actual supported entry mechanism instead of reviving removed command carriers

#### Verification

- **Syntax Check**: passed
- **Cross-Reference Check**: passed
- **Workflow-Assets Consistency**: not-applicable
- **Variant Sweep Check**: passed
- **Contract-Surface Check**: passed
- **Repeat-Trigger Check**: passed
- **Overall**: verified

---

### WS-004: OpenCode hook-customization docs point to `.opencode/package.json` registration that the installed file does not expose

**Decision**: adopted
**Status**: succeeded
**Report Classification**: confirmed-defect

#### Change Detail

- **File**: `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/customize-local/change-hooks.md`
- **Change Type**: modify
- **Root Cause Class**: stale declaration drift
- **Recurrence Status**: no-prior-task-evidence
- **Before State**: trellis-meta change-hooks guidance told operators to treat `.opencode/package.json -> .opencode/plugins/session-start.js` as a direct registration path, which the installed package file does not actually expose
- **After State**: the source reference doc now separates OpenCode's dependency/config surface from the actual plugin carrier path, upgrade merge explicitly refreshes those distributed trellis-meta reference docs, and `upgrade-compat --check` now flags stale trellis-meta copies when those optional reference surfaces exist
- **Related Variants Covered**: distributed `change-hooks.md` copies under `.agents/skills/trellis-meta/`, `.claude/skills/trellis-meta/`, `.opencode/skills/trellis-meta/`
- **Contract Surfaces Updated**: `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/customize-local/change-hooks.md`, `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`, `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- **Contract Surfaces Verified**: fresh-install and existing-workflow reference-doc refresh tests, plus `upgrade-compat --check` stale-reference detection
- **Rationale**: preserves the documented troubleshooting flow while removing the false implication that `.opencode/package.json` contains a visible plugin-to-file map

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

### Unresolved Issues

- none

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project if you want a regenerated report against the repaired workflow output
2. Run `workflow-audit` if you want a broader version-gated audit after this focused repair
3. Manual review needed for: `none`
4. Closure round artifacts:
   - `closure-round-1.md`
5. Legacy issue-history shadow (not used for cross-version repair decisions): `none`
6. Bumped workflow version after converged repair: `0.1.2801`

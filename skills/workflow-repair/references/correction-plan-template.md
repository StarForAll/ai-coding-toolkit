# Correction Plan Template

This document defines the format for the correction plan that `workflow-repair` presents to the user before making any modifications.

---

## Document Purpose

The correction plan is the user-facing decision artifact. It must be presented to the user before any files are modified.

Normal rule: explicit confirmation is required.
Exception: if the current user instruction already explicitly requests repair of real confirmed issues, that standing instruction may count as execution authorization after the plan is echoed.

---

## Document Structure

### Header

```markdown
# Workflow Repair — Correction Plan

## Report Source

- Protocol: workflow-scan-repair-v2
- Trellis Version (at scan time): {trellis-version from WORKFLOW_QUESTIONS.md}
- Workflow Version: {workflow-version from WORKFLOW_QUESTIONS.md}
- Scan Timestamp: {scan-timestamp from WORKFLOW_QUESTIONS.md}
- Temp Project: {temp-project-root from WORKFLOW_QUESTIONS.md}
- Report File: {absolute path to WORKFLOW_QUESTIONS.md}
- Repair Task: {absolute or repo-relative path to the dedicated repair task directory}
- Prior Issue History Loaded: {N} document(s) from `tmp/workflow-issues/`

## Verification Summary

- Total findings in report: {N}
- Confirmed (adopted): {N}
- False alarms (ignored): {N}
- Needs manual decision: {N}
- Blocked: {N}
- Trellis-native (patch within workflow): {N}
- Authorization Mode: analysis-only | authorized-to-repair | post-plan-confirmation
```

### Per-Finding Decision Block

Each finding gets a decision block:

```markdown
---

### WS-NNN: {title from report}

**Decision**: adopted | ignored | blocked | manual-decision | trellis-native

**Verification Result**: {brief result of re-checking against the temp project and source project}

**Root Cause Class**: {stale declaration drift | incomplete installer patch | partial cross-file update | wrong runtime assumption | missing cleanup / residual artifact | other}

**Recurrence Status**: {first-seen | repeated-after-prior-repair | no-history-found}

#### {If adopted or trellis-native:}

**Proposed Fix**:
- **File**: {relative path within docs/workflows/新项目开发工作流/}
- **Before**: {description of current state}
- **After**: {description of intended state}
- **Change Type**: add | modify | remove
- **Related Variants Covered**: {other files/patterns fixed together, or `none`}
- **Contract Surfaces Covered**: {every must-update / must-verify-only surface, or `none`}
- **Side-Effect Analysis**: {what downstream references, other CLIs, or other scripts are affected and how}
- **Repeat-Trigger Prevention**: {why this fix should prevent the same report pattern from recurring}
- **History Match Summary**: {matching prior issue-history docs, or `none`}

#### {If ignored:}

**Reason for ignoring**: {why this finding is a false alarm, already fixed, or not actionable}

#### {If blocked:}

**Blocker**: {what prevents verification or repair}

#### {If manual-decision:}

**Question for user**: {the specific decision needed, with trade-off explanation}

---
```

### Confirmation Footer

```markdown
---

## Confirmation Required

The above plan will modify files ONLY within:

- `docs/workflows/新项目开发工作流/`
- the current repair task directory
- `tmp/workflow-issues/`

If the current user instruction already explicitly says to fix real confirmed issues, the skill may treat that instruction as standing authorization after this plan is echoed. Otherwise it must stop here and wait for a decision.

Options:
1. **Accept all** — apply all adopted and trellis-native fixes
2. **Accept partial** — specify which WS-NNN findings to apply
3. **Reject** — do not apply any changes
4. **Modify** — request adjustments to specific proposed fixes

Awaiting your decision.
```

---

## Decision State Semantics

| State | Meaning | Action |
|-------|---------|--------|
| `adopted` | Finding confirmed, fix is clear, minimal, and safe | Apply the fix after user confirms the plan |
| `ignored` | Finding is false alarm, already fixed in source, or not actionable | No action needed; document the reason |
| `blocked` | Verification or repair cannot proceed due to external constraint | Report blocker; no fix attempted |
| `manual-decision` | Finding is real but fix involves ambiguity, risk, or trade-off | Present the question to the user; do not auto-adopt |
| `trellis-native` | Issue is in trellis-installed artifact, not workflow source | Design a patch within the workflow so the installer can apply it |

---

## Rules

1. Every finding from WORKFLOW_QUESTIONS.md must appear in the correction plan with exactly one decision state.
2. No fix may be applied before the user explicitly confirms.
   Exception: an already-explicit repair request in the current instruction counts as confirmation after the plan is echoed.
3. Side-effect analysis is required for every `adopted` and `trellis-native` fix.
4. `manual-decision` items must include a concrete question, not a vague "needs review".
5. Files outside `docs/workflows/新项目开发工作流/` must never appear in the "File" field of a proposed fix.
6. Every `adopted` and `trellis-native` block must state whether a same-pattern variant sweep was performed.
7. Every `adopted` and `trellis-native` block must explain the root-cause class and why the plan is broad enough to avoid a repeated trigger.
8. The plan must name the dedicated repair task and report how many prior issue-history docs were loaded from `tmp/workflow-issues/`.

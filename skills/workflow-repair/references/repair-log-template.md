# Repair Log Template

This document defines the format for the execution log that `workflow-repair` writes after applying confirmed fixes.

---

## Document Purpose

The repair log records what was actually done: which fixes were applied, what the before/after states were, and whether post-repair verification passed. It is the audit trail for the repair session.

---

## Document Location

Written to the current task directory (`.trellis/tasks/{task-id}/`). If no task is active, write to a timestamped file at the project root: `workflow-repair-log-{timestamp}.md`.

---

## Document Structure

### Header

```markdown
---
repair-log-version: 1
protocol: workflow-scan-repair-v1
source-report: {absolute path to WORKFLOW_QUESTIONS.md}
trellis-version: {current trellis version}
repair-timestamp: {ISO 8601}
authorization-mode: analysis-only | authorized-to-repair | post-plan-confirmation
total-attempted: {N}
total-succeeded: {N}
total-failed: {N}
total-skipped: {N}
---

# Workflow Repair Log

## Session Info

- Source Report: {absolute path to WORKFLOW_QUESTIONS.md}
- Trellis Version: {current trellis version}
- Repair Time: {ISO 8601 timestamp}
- Authorization Mode: {analysis-only | authorized-to-repair | post-plan-confirmation}
- User Confirmation: {yes/partial/rejected/not-needed}
```

### Per-Fix Record

Each applied fix gets a record:

```markdown
---

### WS-NNN: {title}

**Decision**: adopted | trellis-native
**Status**: succeeded | failed | reverted

#### Change Detail

- **File**: {relative path within docs/workflows/新项目开发工作流/}
- **Change Type**: add | modify | remove
- **Root Cause Class**: {named class for this fix}
- **Recurrence Status**: {first-seen | repeated-after-prior-repair | no-history-found}
- **Before State**: {brief description or key excerpt of the state before the fix}
- **After State**: {brief description or key excerpt of the state after the fix}
- **Related Variants Covered**: {other files/patterns fixed together, or `none`}
- **Contract Surfaces Updated**: {files/surfaces updated in the same repair batch, or `none`}
- **Contract Surfaces Verified**: {files/surfaces checked but not changed, or `none`}
- **Rationale**: {why this specific change addresses the finding}

#### Verification

- **Syntax Check**: passed | failed | not-applicable
- **Cross-Reference Check**: passed | failed | not-applicable
- **Workflow-Assets Consistency**: passed | failed | not-applicable
- **Variant Sweep Check**: passed | failed | not-applicable
- **Contract-Surface Check**: passed | failed | not-applicable
- **Repeat-Trigger Check**: passed | failed | not-applicable
- **Overall**: verified | unverified

#### {If failed or reverted:}

**Error**: {what went wrong}
**Revert Action**: {what was done to restore the previous state, if applicable}
**Next Step**: {recommended remediation}

---
```

### Session Summary

```markdown
---

## Session Summary

| WS-NNN | Decision | Status | Verified |
|--------|----------|--------|----------|
| WS-001 | adopted | succeeded | yes |
| WS-002 | trellis-native | succeeded | yes |
| WS-003 | adopted | failed | no |

### Unresolved Issues

- WS-003: {brief description of what remains unresolved}

### Recommended Next Steps

1. Re-run `workflow-scan` on a fresh temp project to verify repairs
2. Or run `workflow-audit` for comprehensive validation
3. Manual review needed for: {list of manual-decision or blocked items}
```

---

## Rules

1. Every fix that was attempted must have a per-fix record, regardless of success or failure.
2. If a fix fails and is reverted, the revert action must be documented.
3. If post-repair verification fails for a fix, the fix status must be `failed` or `reverted`, never `succeeded`.
4. The "Before State" should capture enough context to reconstruct what changed, not the entire file content.
5. Task files are NOT deleted after completion — the repair log persists as a permanent record.
6. If a same-pattern sweep was performed, the log must record which sibling locations were covered.
7. Every attempted fix must record the root-cause class, recurrence status, and repeat-trigger check result.

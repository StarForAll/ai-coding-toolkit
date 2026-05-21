# Repair Log Template

This document defines the format for the execution log that `workflow-repair` writes after applying confirmed fixes.

---

## Document Purpose

The repair log records what was actually done: which fixes were applied, what the before/after states were, and whether post-repair verification passed. It is the audit trail for the repair session.

---

## Document Location

Written to the dedicated current repair task directory
(`.trellis/tasks/{task-id}/`). This skill must create/switch to a repair task
before it writes the log, so there is no project-root fallback.

---

## Document Structure

### Header

```markdown
---
repair-log-version: 1
protocol: workflow-scan-repair-v2
source-report: {absolute path to WORKFLOW_QUESTIONS.md}
repair-task: {absolute or repo-relative path to the dedicated repair task directory}
issue-history-file: {absolute or repo-relative path to tmp/workflow-issues/NNNN.md}
trellis-version: {current trellis version}
repair-timestamp: {ISO 8601}
authorization-mode: analysis-only | authorized-to-repair | post-plan-confirmation
continuation-mode: stop-after-summary | auto-follow-through
total-attempted: {N}
total-succeeded: {N}
total-failed: {N}
total-reverted: {N}
total-skipped: {N}
---

# Workflow Repair Log

## Session Info

- Source Report: {absolute path to WORKFLOW_QUESTIONS.md}
- Repair Task: {absolute or repo-relative path to the dedicated repair task directory}
- Issue History File: {absolute or repo-relative path to tmp/workflow-issues/NNNN.md}
- Trellis Version: {current trellis version}
- Repair Time: {ISO 8601 timestamp}
- Authorization Mode: {analysis-only | authorized-to-repair | post-plan-confirmation}
- Continuation Mode: {stop-after-summary | auto-follow-through}
- Auto Follow-Through Outcome: {not-applicable | pending | reached-finish-work | reached-task-close | stopped-with-blocker: <brief reason> | interrupted: session-did-not-complete}
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
4. The current run's issue-history summary was written to: {issue-history-file}
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
8. The log must record the dedicated repair task path and the `tmp/workflow-issues/NNNN.md` file generated by the run.
9. When later close-out rules need to prove that an out-of-directory file
   belongs to this run's commit scope, the log should provide that evidence by
   listing the file as changed, written, or output by this run.
10. If continuation mode = `auto-follow-through`, the log should also record
   whether post-repair continuation reached finish-work, reached normal task
   closure via `continue`, or stopped with a blocker.
11. If auto follow-through stops because a later commit-scope confirmation
    included non-task files or misleading repair-result wording, the blocker
    reason should state that explicitly rather than implying the prompt was
    safely accepted. This is the blocker-reason form of the broader honesty
    rule below.
12. If the blocker was instead caused by insufficient explicitness or failed
    independent scope proof, the blocker reason should state that explicitly
    rather than collapsing it into a generic `unreliable` label.
13. If multiple blocker causes apply at once, the blocker reason should report
    all triggered causes in one concise summary rather than choosing one and
    hiding the others.
14. Because Step 11 writes the log before Step 12 finishes, the log should use
    `pending` until the continuation result is known, then update the same log
    with the final outcome after Step 12 completes or blocks.
15. When continuation mode = `stop-after-summary`, set Auto Follow-Through
    Outcome to `not-applicable` and skip the pending-to-final update cycle.
16. If a later run resumes the same task and finds an older repair log still at
    `pending`, convert that stale value to
    `interrupted: session-did-not-complete` before recording the newer
    continuation outcome.
17. `total-attempted` counts every repair item that actually entered execution,
    regardless of final outcome. Define it as:
    `total-succeeded + total-failed + total-reverted`.
18. When documenting mixed succeeded/reverted work, partial acceptance, or
    `target_focus`, the log must not describe the later commit scope as if all
    attempted repairs or all report findings were verified. This is the
    document-level honesty rule that Rules 11-13 narrow to blocker wording.
19. When multiple repair logs exist under the same task, determine the
    "latest repair log" from the highest `repair-timestamp` value in
    frontmatter rather than from filename ordering alone.

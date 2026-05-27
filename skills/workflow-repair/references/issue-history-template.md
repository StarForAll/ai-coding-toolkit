# Workflow Issue History Template

This document defines the optional legacy-shadow issue-history summary that
`workflow-repair` may still write to `tmp/workflow-issues/`.

---

## Document Purpose

In `workflow-scan-repair-v4`, this file is no longer a primary repair decision
input. Same-version task-local repair logs and closure-round artifacts are the
real convergence memory surface.

---

## Document Location

Write exactly one file per repair execution to:

`tmp/workflow-issues/NNNN.md`

Rules:

- filename stem must be numeric only
- numbering must be monotonic increasing within the directory
- use four-digit zero padding: `0001.md`, `0002.md`, `0003.md`, ...

---

## Document Structure

### Header

```markdown
---
issue-history-version: 1
protocol: workflow-scan-repair-v4
temp-project-version: {trellis version or temp-project .trellis/.version value}
temp-project-root: {absolute temp project path}
report-path: {absolute path to WORKFLOW_QUESTIONS.md}
repair-task: {absolute or repo-relative path to the dedicated repair task directory}
continuation-mode: {stop-after-summary | auto-follow-through}
created-at: {ISO 8601}
total-issues: {N}
---

# Workflow Issue History

## Session Summary

- Temp Project Version: {temp-project-version}
- Temp Project Root: {temp-project-root}
- Report Path: {report-path}
- Repair Task: {repair-task}
- Continuation Mode: {stop-after-summary | auto-follow-through}
- Issue Count: {total-issues}
```

### Per-Issue Entry

```markdown
---

### {WS-ID}: {problem title}

- **Problem ID / Title**: {WS-ID and title, or another stable problem label if no WS-ID exists}
- **Report Classification**: confirmed-defect | design-debt | evidence-gap
- **Root Cause**: {named root-cause class}
- **Repaired Files**:
  - {relative path within docs/workflows/新项目开发工作流/}
  - {another file, if any}
- **Variant Sweep Scope**: {same-pattern or same-root-cause locations fixed together, or `none`}
- **Trellis-Native**: yes | no
- **Unresolved Items**:
  - {remaining risk, blocked sibling, or `none`}
```

### Rules

1. Every execution must write one document even when no fixes were applied.
2. The required per-issue fields are:
   - temp project version
   - report path
   - problem title/ID
   - report classification
   - root cause
   - repaired files
   - variant sweep scope
   - whether the issue was trellis-native
   - unresolved items
3. The session-level header/summary fields must include:
   - continuation mode
4. If no issue was repaired, the document must still record why:
   ignored, blocked, rejected, or no findings.
5. Later `v4` runs may keep this file as an audit shadow, but must not use it
   as their main cross-version repair memory surface.

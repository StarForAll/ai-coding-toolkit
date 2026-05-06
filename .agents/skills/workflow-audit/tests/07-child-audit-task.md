# 07 Child Audit Task

## Purpose

Verify that `workflow-audit` creates a dedicated child audit task when a non-audit active task already exists and the audit enters a task-based mode.

## Input

User input:

> While my current feature task is still active, run a full structured workflow audit for `docs/workflows/新项目开发工作流/` with task tracking.

## Expected Mode

Task-based audit with child audit task creation.

## Expected Key Behaviors

- execute A/B/C first, then decide the audit is task-based
- create a dedicated child audit task instead of mixing the audit into the parent task
- switch execution into the child audit task immediately
- enter the `trellis-brainstorm` mainline as the control container inside the child audit task
- initialize `prd.md` and `audit-report.md` inside the child task
- keep the audit conclusion and subsequent remediation inside the same child audit task until completion

## Must Not

- must not write the audit body directly into the parent non-audit task
- must not create a sibling free-floating note without switching task context
- must not return to the parent task merely because the first audit report exists

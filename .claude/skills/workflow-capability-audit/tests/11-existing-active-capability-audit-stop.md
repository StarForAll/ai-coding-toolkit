# 11 Existing Active Capability Audit Stop

## Purpose

Verify that `workflow-capability-audit` does not create a second full-audit task when a `workflow-capability-audit` task is already active.

## Input

User input:

> Run the Trellis capability compatibility audit for `docs/workflows/新项目开发工作流/` again while the previous capability audit task is still active.

## Expected Mode

Stop-and-resume boundary before any new full-audit task creation.

## Expected Key Behaviors

- detect that a `workflow-capability-audit` task is already active
- stop before creating another audit task
- ask the user to resume or complete the existing audit first
- avoid creating fresh A/B fixtures for the duplicate request

## Must Not

- must not create a second active `workflow-capability-audit` task
- must not split the audit state across multiple `capability-report.md` files
- must not allocate another fresh A/B pair for the duplicate full-audit request

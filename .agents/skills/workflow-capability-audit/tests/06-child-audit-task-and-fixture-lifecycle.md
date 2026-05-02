# 06 Child Audit Task And Fixture Lifecycle

## Purpose

Verify that `workflow-capability-audit` creates a dedicated child audit task when a non-audit active task exists, preserves A/B fixtures through the whole compatibility-fix lifecycle, and only destroys them after correction is complete plus explicit final confirmation.

## Input

User input:

> While my current task is active, run the Trellis compatibility audit for `docs/workflows/新项目开发工作流/`.

## Expected Mode

Child task-based compatibility audit.

## Expected Key Behaviors

- create a dedicated child audit task
- switch execution into it immediately
- keep A/B fixtures after audit conclusion
- keep A/B fixtures during confirmed compatibility-fix and post-fix revalidation
- require explicit final confirmation before destruction

## Must Not

- must not mix the audit directly into the parent non-audit task body
- must not destroy A/B immediately after audit conclusion
- must not destroy A/B immediately after correction without final confirmation

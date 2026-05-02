# 04 Structural Break Possible Stop

## Purpose

Verify that `workflow-capability-audit` stops when `Structural-Break Judgment = possible` and uses the dedicated stop-and-confirm template rather than continuing into normal adaptation recommendations.

## Input

User input:

> Audit the new Trellis version impact on `docs/workflows/新项目开发工作流/` and tell me whether normal adaptation is enough.

## Expected Mode

Task-based audit that stops at structural-break-possible confirmation.

## Expected Key Behaviors

- perform full audit after version gate passes
- reach `Structural-Break Judgment = possible`
- use `references/structural-break-possible-template.md`
- stop and require explicit user confirmation
- do not continue into ordinary adaptation recommendations

## Must Not

- must not bury `possible` inside generic notes
- must not recommend normal adaptation as if structural risk were resolved

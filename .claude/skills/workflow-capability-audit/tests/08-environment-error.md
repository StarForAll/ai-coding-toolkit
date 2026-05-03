# 08 Environment Error

## Purpose

Verify that `workflow-capability-audit` terminates immediately when `trellis -v` fails or returns empty output.

## Input

User input:

> Check whether `docs/workflows/新项目开发工作流/` needs a Trellis capability compatibility audit, but the current machine cannot return a valid `trellis -v` result.

## Expected Mode

Version-gate termination with environment-error classification.

## Expected Key Behaviors

- run `trellis -v` as part of the version gate before any task creation
- detect command failure or empty output
- classify the stop as `Blocked / Environment Error`
- stop before creating audit tasks, `prd.md`, `capability-report.md`, or A/B fixtures

## Must Not

- must not guess the current Trellis version from unrelated files
- must not continue into the audit path with missing version evidence
- must not create audit artifacts after the environment failure

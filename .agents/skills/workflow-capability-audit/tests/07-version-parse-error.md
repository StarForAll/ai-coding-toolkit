# 07 Version Parse Error

## Purpose

Verify that `workflow-capability-audit` terminates immediately when version parsing fails during the version gate.

## Input

User input:

> Run the Trellis capability compatibility audit for `docs/workflows/新项目开发工作流/`, but the current environment returns a malformed Trellis version string.

## Expected Mode

Version-gate termination with parse-error classification.

## Expected Key Behaviors

- run version gating before task creation
- detect that semantic-version parsing failed
- classify the stop as `Blocked / Version Parse Error`
- stop before creating `prd.md`, `capability-report.md`, or A/B fixtures

## Must Not

- must not downgrade the parse failure into a normal equal-version stop
- must not continue into the full audit path
- must not create audit artifacts after parse failure

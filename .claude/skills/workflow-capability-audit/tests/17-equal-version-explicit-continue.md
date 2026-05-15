# 17 Equal-version Explicit Continue

## Purpose

Verify that `workflow-capability-audit` continues into the full audit path when the current Trellis version equals `COMPATIBLE_TRELLIS_VERSION` and the caller explicitly enables same-version continuation.

## Input

User input:

> Even if the current Trellis version already matches the compatibility anchor, continue into the full compatibility audit for `docs/workflows/新项目开发工作流/`.

## Expected Mode

Task-based full compatibility audit with explicit same-version continuation.

## Expected Key Behaviors

- run version gating before task creation
- detect that `current == compatible`
- continue only because explicit same-version continuation was requested
- create the audit task, fresh A/B fixtures, and `capability-report.md`

## Must Not

- must not auto-continue same-version audits without the explicit continuation input
- must not emit `equal-version-stop` once explicit continuation is enabled
- must not skip the normal full-audit evidence flow

# 16 Codex Inline Main-Session Analysis

## Purpose

Verify that `workflow-capability-audit` stays in the main Codex session for
Step B analysis when this repository keeps `codex.dispatch_mode: inline`.

## Input

User input:

> In Codex, audit whether the latest Trellis version is still compatible with `docs/workflows/新项目开发工作流/`, and compare the native CLI adaptation evidence.

## Expected Mode

Task-based full compatibility audit, with Step B analysis kept inline in the
main Codex session.

## Expected Key Behaviors

- keep the audit analysis in the main Codex session
- do not manually spawn subagents for Step B read-only analysis or official-doc comparison
- still apply the separate Codex runtime boundary if fresh `trellis init` fails only inside the current Codex runtime
- continue to record native CLI evidence in `capability-report.md`

## Must Not

- must not bypass the repo-local Codex inline rule just because the audit is "only analysis"
- must not conflate the inline execution constraint with the separate Codex runtime boundary rule

# 13 Codex Runtime Boundary Recheck

## Purpose

Verify that `workflow-capability-audit` does not treat a `trellis init` failure observed only under Codex runtime validation as sufficient proof that the user's actual machine environment is broken.

## Input

User input:

> Run the Trellis capability compatibility audit for `docs/workflows/新项目开发工作流/` in Codex, but `trellis init` fails only inside the current Codex runtime while the same machine can still run it from a real shell.

## Expected Mode

Codex runtime boundary stop with non-Codex recheck required.

## Expected Key Behaviors

- distinguish Codex-local runtime failure from actual machine-environment failure
- avoid classifying the user's machine as `Blocked / Environment Error` based only on Codex-local `trellis init` evidence
- require rechecking the same step in shell, Claude Code, or OpenCode on the same machine
- if such a recheck succeeds, treat the shell/non-Codex result as the environment truth source

## Must Not

- must not claim the user's actual machine environment is broken based only on Codex-local `trellis init` failure
- must not collapse Codex sandbox/runtime evidence into confirmed target-machine environment evidence
- must not skip the non-Codex recheck requirement

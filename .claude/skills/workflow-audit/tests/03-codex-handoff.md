# 03 Codex Handoff

## Purpose

Verify that `workflow-audit` stops correctly and emits a handoff block when the formal temporary-project embed step is reached under Codex, rather than continuing execution.

## Input

User input:

> We are currently in Codex. Audit the formal embed step for `docs/workflows/新项目开发工作流/`, and confirm what handoff should happen if a real temporary-project embed must be executed.

## Expected Mode

Non-trivial audit mode, with Codex handoff triggered before the formal embed execution.

## Expected Key Behaviors

- recognize that the current CLI is Codex (either explicitly supplied or safely inferred from runtime)
- stop before continuing the formal temporary-project embed execution
- emit the `Codex Handoff` template block
- use default takeover order `Claude Code -> OpenCode`
- provide command-level handoff instructions
- include `detect-embed-state.py`, `install-workflow.py --dry-run`, formal install with `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1`, and post-install `upgrade-compat.py --check`
- explicitly require the return of state-detection output, installer output, post-install verification, and anomalies

## Must Not

- must not allow Codex to continue leading the first formal embed execution
- must not output only “switch to another CLI” without concrete handoff commands
- must not treat handoff as if validation were already completed

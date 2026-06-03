# 19 Current CLI Inference Failure

## Purpose

Verify that `workflow-audit` asks the user to clarify `current_cli` only when a CLI-sensitive path is reached and the runtime still cannot be determined safely.

## Input

User input:

> Audit the formal embed human-terminal boundary behavior for `docs/workflows/新项目开发工作流/`, but imagine the current execution surface is ambiguous and you cannot reliably infer which CLI is running.

## Expected Mode

CLI-sensitive clarification stop after the relevant audit branch is reached.

## Expected Key Behaviors

- do not ask for `current_cli` at the initial input-parsing step if the audit can still proceed safely
- once a CLI-sensitive branch is reached and the runtime still cannot be inferred safely, ask the user to clarify `current_cli`
- stop and wait for that clarification before continuing the CLI-sensitive branch
- until the executor identity is clarified, do not fabricate official-doc / repo-local / practical-use adaptation conclusions for a CLI-specific branch

## Must Not

- must not guess the current CLI
- must not ask for `current_cli` prematurely before the audit reaches a CLI-sensitive path
- must not continue a CLI-sensitive branch with an unresolved executor identity

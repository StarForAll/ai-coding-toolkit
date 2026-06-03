# 14 Human Confirmation Required

## Purpose

Verify that `workflow-audit` stops cleanly when runtime validation reaches the formal embed boundary but no human terminal transcript is available yet.

## Input

User input:

> We are in Codex. Audit the formal embed step for `docs/workflows/新项目开发工作流/` and tell me what happens if runtime validation must continue, but no human operator terminal transcript is available yet.

## Expected Mode

Task-based runtime mode blocked at the formal embed boundary.

## Expected Key Behaviors

- reach the formal embed boundary through the normal A/B/C -> D path
- recognize that no human terminal transcript is available
- stop as `Blocked / Human Confirmation Required`
- explain that the formal embed step remains unverified until a human operator runs the remaining commands in an interactive system terminal

## Must Not

- must not continue the formal embed step inside Codex
- must not invent an AI CLI takeover path
- must not suggest an agent/sub-agent workaround once the human-terminal path is required
- must not claim that runtime validation already completed

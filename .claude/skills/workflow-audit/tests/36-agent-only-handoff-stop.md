# 36 Agent-only Continuation Is Insufficient

## Purpose

Verify that `workflow-audit` treats any agent-only continuation path as insufficient once the formal embed step requires a human terminal transcript.

## Input

User input:

> We are in Codex. Claude Code is only available through agents in this environment, and OpenCode would also have to run as an agent. Audit the formal embed step for `docs/workflows/新项目开发工作流/` and tell me what happens if runtime validation must continue.

## Expected Mode

Task-based runtime mode blocked at the formal embed boundary.

## Expected Key Behaviors

- reach the formal embed boundary through the normal A/B/C -> D path
- recognize that the current contract allows only a human-operated interactive system terminal for the remaining formal embed commands
- treat agent-only continuation as insufficient for this skill
- stop as `Blocked / Human Confirmation Required`
- explain that the formal embed step remains unverified because agent-based continuation is intentionally disallowed at the current stage

## Must Not

- must not suggest using a Claude Code or OpenCode agent/sub-agent as a substitute executor
- must not treat agent-only availability as a sufficient continuation path
- must not continue the formal embed step inside Codex

# 36 Agent-only Handoff Stop

## Purpose

Verify that `workflow-audit` treats agent-only Claude Code/OpenCode availability
as no usable non-Codex handoff target for the formal embed step.

## Input

User input:

> We are in Codex. Claude Code is only available through agents in this environment, and OpenCode would also have to run as an agent. Audit the formal embed step for `docs/workflows/新项目开发工作流/` and tell me what happens if runtime validation must continue.

## Expected Mode

Task-based runtime mode blocked at the Codex handoff boundary.

## Expected Key Behaviors

- reach the Codex handoff boundary through the normal A/B/C -> D path
- recognize that the current contract allows only a main interactive Claude Code or OpenCode session for takeover
- treat agent-only Claude Code/OpenCode availability as no usable non-Codex handoff target for this skill
- stop as `Blocked / No Handoff Target`
- explain that the formal embed step remains unverified because agent-based continuation is intentionally disallowed at the current stage

## Must Not

- must not suggest using a Claude Code or OpenCode agent/sub-agent as the takeover executor
- must not treat agent-only availability as a sufficient handoff path
- must not continue the formal embed step inside Codex

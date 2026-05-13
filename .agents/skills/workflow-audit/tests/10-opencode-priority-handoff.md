# 10 OpenCode-priority Handoff Override

## Purpose

Verify that `workflow-audit` overrides the default Codex handoff order when the user has already established that Claude Code is unavailable and OpenCode is the only usable non-Codex CLI.

## Input

User input:

> We are in Codex, and Claude Code is unavailable in this environment. Audit the formal embed step for `docs/workflows/新项目开发工作流/` and tell me what handoff should happen if runtime validation must continue.

## Expected Mode

Task-based runtime mode with Codex handoff override.

## Expected Key Behaviors

- reach the Codex handoff boundary through the normal A/B/C -> D path
- recognize that the user already ruled out Claude Code
- override the default takeover order and prioritize OpenCode
- explain why the default `Claude Code -> OpenCode` order was overridden
- still provide the full command-level handoff instructions and required return evidence
- if CLI adaptation conclusions are already in scope, preserve the evidence-trio reporting rule for in-scope CLIs while treating the takeover-order override itself as an execution constraint rather than a defect

## Must Not

- must not present Claude Code as the default takeover CLI after the user ruled it out
- must not drop the explanation for the override
- must not continue the formal embed step inside Codex
- must not convert the override into a confirmed compatibility defect without evidence of real behavioral breakage

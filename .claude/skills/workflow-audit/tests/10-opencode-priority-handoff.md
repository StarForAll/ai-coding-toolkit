# 10 No AI CLI Takeover

## Purpose

Verify that `workflow-audit` no longer offers any AI-CLI takeover path once the formal embed boundary is reached, even if the user mentions Claude Code / OpenCode availability constraints.

## Input

User input:

> We are in Codex, and Claude Code is unavailable in this environment. Audit the formal embed step for `docs/workflows/新项目开发工作流/` and tell me what should happen if runtime validation must continue.

## Expected Mode

Task-based runtime mode with human-terminal-required stop.

## Expected Key Behaviors

- reach the formal embed boundary through the normal A/B/C -> D path
- recognize that Claude Code / OpenCode availability does not reopen an AI-CLI continuation path
- provide the full human-terminal command sequence and required return evidence
- if CLI adaptation conclusions are already in scope, preserve the evidence-trio reporting rule for in-scope CLIs while treating the human-terminal boundary itself as an execution constraint rather than a defect

## Must Not

- must not present Claude Code or OpenCode as the new executor of formal embed
- must not suggest an OpenCode agent/sub-agent as a fallback continuation path
- must not continue the formal embed step inside Codex
- must not convert the human-terminal boundary into a confirmed compatibility defect without evidence of real behavioral breakage

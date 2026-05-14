# 35 Main-session-only Execution

## Purpose

Verify that `workflow-audit` stays in the invoking Claude Code or OpenCode main
interactive session even when agent/sub-agent delegation is available.

## Input

User input:

> We are running `workflow-audit` from a Claude Code or OpenCode main session, and agent delegation is available in this environment. Audit `docs/workflows/新项目开发工作流/` for static structural issues only.

## Expected Mode

Lightweight static mode in the invoking main session.

## Expected Key Behaviors

- execute the audit in the current main interactive session
- do not dispatch Claude Code or OpenCode agents/sub-agents to perform audit steps
- keep the normal A/B/C -> E evidence mainline behavior unchanged
- treat the no-agent rule as a maintainer-side execution constraint rather than as a CLI compatibility defect

## Must Not

- must not delegate the audit to a Claude Code agent/sub-agent
- must not delegate the audit to an OpenCode agent/sub-agent
- must not reinterpret the no-agent rule as removal of Claude Code or OpenCode from the supported audit surface

# 03 Agent Mode Unsupported

## Purpose

Verify that `workflow-scan --agent` blocks conservatively when the current
session is not truly agent-capable.

## Input

User input:

> Run `/workflow-scan --agent` here. The broader product family supports agents, but this current session cannot safely invoke helper agents with bounded ownership, or a stronger local rule still requires inline execution.

## Expected Mode

Blocked before helper dispatch with `Blocked / Agent Mode Unsupported`.

## Expected Key Behaviors

- evaluate capability from the current runtime/session, not from the product
  family name alone
- treat stronger local execution rules as a valid reason to block `--agent`
- stop before helper dispatch if bounded helper execution cannot be guaranteed
- explain that the safe next step is inline scan or a different main session
  that is actually agent-capable

## Must Not

- must not silently fall back to inline while pretending `--agent` was honored
- must not assume that any Claude/OpenCode/Codex environment is agent-capable
  just because the platform supports agents somewhere
- must not classify unsupported helper execution as a scan finding

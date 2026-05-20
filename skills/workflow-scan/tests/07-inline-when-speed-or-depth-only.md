# 07 Inline When Speed Or Depth Only

## Purpose

Verify that requests for speed, depth, or thoroughness alone do not implicitly
enable helper-agent mode.

## Input

User input:

> Run `/workflow-scan` and scan deeper for anything suspicious. If possible, do it faster too.

## Expected Mode

Inline scan in the current CLI session.

## Expected Key Behaviors

- interpret the request as a stronger inline scan request, not as an
  agent-assisted request
- keep helper-agent mode disabled because the user did not explicitly ask for
  helper-agent use
- still perform the normal workflow surface inventory and verification inline

## Must Not

- must not infer `--agent` mode from "deeper", "faster", or "more thorough"
  wording alone
- must not silently escalate to helper-agent use for performance reasons

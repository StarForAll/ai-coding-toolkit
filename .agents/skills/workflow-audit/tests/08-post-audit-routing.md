# 08 Post-audit Routing

## Purpose

Verify that `workflow-audit` routes only to the trusted post-audit whitelist and always includes the full recommendation contract.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/` and tell me what the next step should be after you stop.

## Expected Mode

Any completed audit mode, followed by controlled post-audit routing.

## Expected Key Behaviors

- stop after presenting findings instead of auto-executing the next phase
- recommend only from the trusted whitelist: `brainstorm`, `start`, `check`, `update-spec`, or a plain-language action if none fit
- exclude `grill-me` from post-audit recommendation targets
- include all four recommendation elements:
  - chosen next action
  - trigger condition
  - brief reason
  - why stronger alternatives were not selected

## Must Not

- must not recommend a non-whitelist skill as if it were trusted post-audit routing
- must not auto-enter the recommended next phase
- must not omit the stronger-alternatives explanation

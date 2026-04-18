# Check

Shared workflow-local source asset for the `implementation-stage check-agent` role in the implementation-internal subagent chain.

## Purpose

Provide the canonical role definition used to generate per-CLI check-agent
files for Claude, OpenCode, and Codex within this workflow.

## When To Use

- After implementation changes exist
- Before the formal `/trellis:check` stage
- When scoped self-fix and rerun verification are still allowed

## Output

- Files checked
- Issues found and fixed
- Verification rerun results

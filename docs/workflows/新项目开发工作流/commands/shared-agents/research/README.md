# Research

Shared workflow-local source asset for the `research` role in the implementation-internal subagent chain:

```text
research -> implement -> check
```

## Purpose

Provide the canonical role definition used to generate per-CLI research-agent
files for Claude, OpenCode, and Codex within this workflow.

## When To Use

- Before implementation starts
- When the implementer needs code context, affected files, or spec guidance
- When external technical evidence is required for a third-party dependency

## Output

- Search results
- Relevant files and specs
- External evidence with source boundaries
- Risks or evidence gaps

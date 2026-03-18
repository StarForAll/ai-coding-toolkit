# Agent Specification Guidelines

> How to create and organize AI agent configurations in this project.

---

## Overview

This project stores AI agent configurations that define system prompts, tools, and workflows for various AI coding assistants (Claude Code, Codex, Cursor, etc.).

---

## Directory Structure

```
agents/
  <agent-id>/
    README.md        # Purpose, use cases, examples
    SYSTEM.md        # System prompt
    TOOLS.md         # Tools/permissions/constraints (optional)
    EXAMPLES/        # Input/output examples (optional)
```

---

## Naming Conventions

- **Agent IDs**: Use kebab-case: `feature-planner`, `bug-fixer`, `release-helper`
- **Focus**: Name by task/role, avoid binding to specific projects
- **Prefix**: Use tool-specific prefixes when needed: `claude-`, `codex-`, `cursor-`

---

## Required Files

### README.md (Required)

Must include:
- **Purpose**: What problem this agent solves
- **Use Cases**: When to invoke this agent
- **Input**: What the agent expects
- **Output**: What the agent produces

### SYSTEM.md (Required)

Contains the system prompt that defines:
- Agent's role and expertise
- Behavioral constraints
- Output format expectations
- Tool usage guidelines

### TOOLS.md (Optional)

Documents:
- Available tools and their purposes
- Permission boundaries
- Rate limits or quotas
- Tool-specific conventions

---

## Quality Standards

### Must Have

- [ ] Clear README with use cases
- [ ] Well-structured SYSTEM.md
- [ ] Appropriate scope (not too narrow/broad)

### Should Have

- [ ] TOOLS.md if agent uses tools
- [ ] Examples in README
- [ ] Version history in SYSTEM.md

### Anti-Patterns

- **Overly generic prompts**: "You are a helpful assistant"
- **Missing boundaries**: No constraints on dangerous operations
- **Tool-specific in generic agents**: Don't embed Claude-specific tools in Codex agent
- **Monolithic agents**: Split complex workflows into focused sub-agents

---

## Examples

### Good Agent Structure

```
bug-fixer/
  README.md       # "Fixes bugs by analyzing error messages and code"
  SYSTEM.md       # Role: debugging expert, outputs reproducible test cases
  TOOLS.md        # Allowed: read, grep, bash (read-only)
  EXAMPLES/
    input-1.md    # Error trace → fix plan
```

### Anti-Pattern

```
catch-all/
  SYSTEM.md       # "You can do anything" ← Too broad!
```

---

## Cross-Platform Considerations

When creating agents that work across multiple AI tools:

- Keep SYSTEM.md tool-agnostic
- Create tool-specific variants in subdirectories: `claude/`, `codex/`, etc.
- Document tool compatibility in README

---

## Versioning

For agents that evolve:
- Add version notes at top of SYSTEM.md
- Use semantic versioning in comments: `<!-- v1.2.0 -->`
- Document breaking changes

---

**Language**: English

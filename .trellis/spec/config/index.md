# Configuration Specification Guidelines

> How to create and organize configuration files in this project.

---

## Overview

This project uses various configuration files for AI coding assistants (Claude Code, Codex, Cursor, etc.). This guide documents how to structure and organize these configurations.

---

## Configuration Types

| Type | Location | Purpose |
|------|----------|---------|
| Agent configs | `.claude/`, `.codex/`, `.cursor/`, `.windsurf/` | AI assistant behavior |
| Project settings | `.github/`, `.vscode/` | Editor and CI/CD settings |
| Custom configs | `.*rc`, `.*config.*` | Tool-specific settings |
| Templates | `.trellis/`, `marketplace/` | Project scaffolding |

---

## Directory Structure

```
.claude/                 # Claude Code configuration
  agents/                # Agent definitions
    <agent-id>/
      SYSTEM.md
      TOOLS.md
  commands/              # Custom slash commands
    trellis/
      <command>.md
  settings.json          # Claude Code settings

.codex/                  # Codex CLI configuration
  commands/              # Custom commands
  prompts/               # Custom prompts

.cursor/                 # Cursor IDE configuration
  rules/                 # Project rules
    *.mdc

.github/                # GitHub configuration
  workflows/             # CI/CD pipelines
  copilot-instructions.md

.vscode/                 # VS Code settings
  settings.json
  extensions.json
```

---

## Naming Conventions

### Configuration Files

- **Dotfiles**: `.claude`, `.github`, `.vscode`
- **Config files**: `*.config.js`, `*.config.json`, `*.config.yaml`
- **Rule files**: `*.rules`, `*.mdc` (Cursor rules)

### Directories

- **Tool-specific**: `.claude/`, `.codex/`, `.cursor/`
- **Platform-specific**: `commands/codex/`, `commands/claude/`

---

## Required Files

### For Claude Code Projects

```
.claude/
  SETTINGS.md            # Project-specific settings (optional)
```

### For Multi-Tool Projects

Maintain parallel structures:
```
.claude/agents/debug.md
.codex/agents/debug.md   # Same agent, different tool
.cursor/rules/debug.mdc  # Same agent, Cursor format
```

---

## Quality Standards

### Must Have

- [ ] Clear organization by tool/platform
- [ ] README in each config directory explaining structure
- [ ] Tool-specific configs in dedicated directories
- [ ] Git-ignored sensitive files (tokens, keys)

### Should Have

- [ ] Version comments in config files
- [ ] Schema validation where possible
- [ ] Documentation of non-obvious settings

### Anti-Patterns

- **Mixed configs**: Don't mix different tool configs in one directory
- **No documentation**: Config directories need README
- **Sensitive data**: Never commit API keys, tokens
- **Duplicate configs**: Share common patterns, don't repeat

---

## Configuration Patterns

### Agent Configuration Pattern

```markdown
# Agent Name
## Purpose
Brief description of what this agent does.

## System Prompt
<detailed system prompt>

## Tools
- `read`: Read files
- `grep`: Search code

## Constraints
- Cannot execute destructive commands
- Must confirm before git push
```

### Command Configuration Pattern

```markdown
# Command: /my-command

## Purpose
Brief description

## Usage
`/my-command [options]`

## Parameters
- `--option1`: Description

## Example
`/my-command --option1 value`
```

---

## Git Ignore Patterns

Ensure these are gitignored:
```
# Sensitive
*.env
.env.local
*.pem
*.key

# IDE
.vscode/launch.json
.idea/

# Logs
*.log
npm-debug.log*

# OS
.DS_Store
Thumbs.db
```

---

## Cross-Tool Consistency

When supporting multiple AI tools:

1. **Core logic in one place**: Define once, adapt per tool
2. **Tool-specific wrappers**: Convert core to tool format
3. **Document mapping**: Show how configs map between tools
4. **Test each tool**: Verify configs work for each platform

Example mapping:
| Concept | Claude | Codex | Cursor |
|---------|--------|-------|--------|
| Agent | `.claude/agents/` | `.codex/agents/` | `.cursor/rules/` |
| Command | `/command` | `/command` | `/command` |
| Rules | `CLAUDE.md` | `.clinerules` | `.cursorrules` |

---

## Best Practices

1. **Modular**: Split large configs into focused files
2. **Documented**: README for each config directory
3. **Validated**: Use JSON schemas where available
4. **Versioned**: Track changes in configs
5. **Tested**: Verify configs work in each tool
6. **Organized**: Consistent directory structure

---

## Common Mistakes

- Not gitignoring sensitive files
- Mixing tool configs in same directory
- No documentation of config purpose
- Duplicate patterns across tools
- Hardcoded values that should be configurable

---

**Language**: English

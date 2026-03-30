# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

This is a **meta-project** — an AI coding toolkit that maintains reusable assets for AI-assisted programming workflows. It is NOT a runnable application but rather a collection of:

- **Markdown** specs, templates, checklists, examples
- **YAML** configuration (`manifest.yaml`, schemas)
- **Python** automation scripts (`cli.py`, validation, assembly, sync)
- **Shell** validation scripts
- **SKILL.md** skill definitions (YAML frontmatter + markdown)
- **Agent/Command** assets deployed to multiple AI tool configurations (Claude Code, OpenCode, iFlow, Codex CLI, Qoder)

## Architecture

### Source Assets → Tool Deployments

```
Source Assets (source of truth)          Tool Deployments (derived)
─────────────────────────────────        ───────────────────────────
trellis-library/specs/            ──→    .trellis/spec/ (project-local)
agents/<id>/SYSTEM.md             ──→    .claude/agents/<role>.md
                                  ──→    .opencode/agents/<role>.md
                                  ──→    .iflow/agents/<role>.md
commands/<tool>/                  ──→    .<tool>/commands/<ns>/<name>.md
skills/<id>/SKILL.md              ──→    .qoder/skills/, .agents/skills/
```

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `trellis-library/` | **Core asset library**: specs, templates, checklists managed via `manifest.yaml` |
| `.trellis/spec/` | **Project live specs**: 11 spec layers defining how to author/maintain assets |
| `.trellis/scripts/` | Workflow automation: task management, session recording, context gathering |
| `skills/` | Skills CLI-compatible skill definitions |
| `.claude/`, `.opencode/`, `.iflow/`, `.codex/`, `.qoder/` | Tool-specific deployments |

## Common Commands

### Validation

```bash
# Validate trellis-library manifest and asset sync (REQUIRED before committing changes)
python3 trellis-library/cli.py validate --strict-warnings

# Validate skills structure (YAML frontmatter check)
./scripts/validate-skills.sh

# Run CLI unit tests
python3 -m unittest trellis-library/tests/test_cli.py
```

### Workflow Scripts

```bash
# Get full session context (run at start of session)
python3 ./.trellis/scripts/get_context.py

# Task management
python3 ./.trellis/scripts/task.py list
python3 ./.trellis/scripts/task.py create "<title>" --slug <name>

# Record session after completing work
python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
```

### Trellis Library CLI

```bash
# Validate library
python3 trellis-library/cli.py validate --strict-warnings

# Assemble pack to target project (dry-run)
python3 trellis-library/cli.py assemble --target /tmp/test --pack <pack-id> --dry-run

# Sync workflows
python3 trellis-library/cli.py sync --mode downstream --target /tmp/test --dry-run
python3 trellis-library/cli.py sync --mode diff --target /tmp/test
```

## Pre-Development Requirements

**MUST read before writing ANY code:**

1. `cat .trellis/spec/index.md` — Master spec index
2. Task-specific specs from the index's "Quick Start by Task Type" table
3. `cat .trellis/spec/guides/index.md` — Always read shared guides

**Key spec layers:**
- `library-assets/` — Authoring specs, templates, checklists for `trellis-library`
- `scripts/` — Python and Shell script conventions
- `agents/`, `commands/`, `skills/` — Asset definition patterns

## Commit Convention

```bash
git commit -m "type(scope): description"
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Language Policy

- `trellis-library/` assets: **English** (enforced by manifest `default_language`)
- Project documentation: Chinese or English per context

## Critical Constraints

1. **Do not execute `git commit`** — AI should not commit code
2. **Max 2000 lines per journal document** in `.trellis/workspace/`
3. **Run validation before any commit**: `python3 trellis-library/cli.py validate --strict-warnings`
4. **No `frontend/` or `backend/` directories** — This is not a traditional application

## Slash Commands

When available, use these commands:
- `/trellis:start` — Initialize developer identity, understand context
- `/trellis:finish-work` — Pre-commit checklist
- `/trellis:break-loop` — Post-debug analysis
- `/trellis:check-cross-layer` — Cross-layer verification

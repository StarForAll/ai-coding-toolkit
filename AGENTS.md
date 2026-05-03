# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

This is a **meta-project** — an AI coding toolkit that maintains reusable assets for AI-assisted programming workflows. It is NOT a runnable application but rather a collection of:

- **Markdown** specs, templates, checklists, examples
- **YAML** configuration (`manifest.yaml`, schemas)
- **Python** automation scripts (`cli.py`, validation, assembly, sync)
- **Shell** validation scripts
- **SKILL.md** skill definitions (YAML frontmatter + markdown)
- **Agent/Command** assets deployed to multiple AI tool configurations (Claude Code, OpenCode, Codex CLI, Qoder)

## Architecture

### Source Assets → Tool Deployments

```
Source Assets (source of truth)          Tool Deployments (derived)
─────────────────────────────────        ───────────────────────────
trellis-library/specs/            ──→    .trellis/spec/ (project-local)
agents/<id>/SYSTEM.md             ──→    .claude/agents/<role>.md
                                  ──→    .opencode/agents/<role>.md
                                  ──→    .codex/agents/<role>.toml
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
| `.claude/`, `.opencode/`, `.codex/`, `.qoder/` | Tool-specific deployments |

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
- `/trellis:finish-work` — Post-commit close-out
- `/trellis:break-loop` — Post-debug analysis
- `/trellis:check` — Cross-layer and quality verification

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

## Subagents

- ALWAYS wait for all subagents to complete before yielding.
- Spawn subagents automatically when:
  - Parallelizable work (e.g., install + verify, npm test + typecheck, multiple tasks from plan)
  - Long-running or blocking tasks where a worker can run independently.
  - Isolation for risky changes or checks

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

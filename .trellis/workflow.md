# Development Workflow

> Based on [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

---

## Table of Contents

1. [Quick Start (Do This First)](#quick-start-do-this-first)
2. [Workflow Overview](#workflow-overview)
3. [Session Start Process](#session-start-process)
4. [Development Process](#development-process)
5. [Session End](#session-end)
6. [File Descriptions](#file-descriptions)
7. [Best Practices](#best-practices)
8. [Phase Index](#phase-index)

---

## Quick Start (Do This First)

### Step 0: Initialize Developer Identity (First Time Only)

> **Multi-developer support**: Each developer/Agent needs to initialize their identity first

```bash
# Check if already initialized
python3 ./.trellis/scripts/get_developer.py

# If not initialized, run:
python3 ./.trellis/scripts/init_developer.py <your-name>
# Example: python3 ./.trellis/scripts/init_developer.py cursor-agent
```

This creates:
- `.trellis/.developer` - Your identity file (gitignored, not committed)
- `.trellis/workspace/<your-name>/` - Your personal workspace directory

**Naming suggestions**:
- Human developers: Use your name, e.g., `john-doe`
- Cursor AI: `cursor-agent` or `cursor-<task>`
- Claude Code: `claude-agent` or `claude-<task>`

### Step 1: Understand Current Context

```bash
# Get full context in one command
python3 ./.trellis/scripts/get_context.py

# Or check manually:
python3 ./.trellis/scripts/get_developer.py      # Your identity
python3 ./.trellis/scripts/task.py list          # Active tasks
git status && git log --oneline -10              # Git state
```

### Step 2: Read Project Guidelines [MANDATORY]

**CRITICAL**: Read guidelines before writing any code:

```bash
# Read the master spec index to see all available guidelines
cat .trellis/spec/index.md

# Then read the specific guidelines relevant to your task:
cat .trellis/spec/library-assets/index.md   # If working on trellis-library assets
cat .trellis/spec/scripts/index.md          # If writing scripts
cat .trellis/spec/agents/index.md           # If defining agents
cat .trellis/spec/skills/index.md           # If defining skills

# Always read shared guides
cat .trellis/spec/guides/index.md
```

**Why this matters?**
- Understand which spec layers apply to your task
- Know coding standards for the packages you'll modify
- Learn the overall code quality requirements

### Step 3: Before Coding - Read Specific Guidelines (Required)

Based on your task, read the **detailed** guideline files listed in each spec index's **Pre-Development Checklist**:

```bash
# The index points to specific files — read those, not just the index
cat .trellis/spec/library-assets/spec-authoring.md
cat .trellis/spec/scripts/python-conventions.md
# etc. — based on what the Pre-Development Checklist lists
```

---

## Workflow Overview

### Core Principles

1. **Read Before Write** - Understand context before starting
2. **Follow Standards** - [!] **MUST read `.trellis/spec/` guidelines before coding**
3. **Incremental Development** - Complete one task at a time
4. **Record Promptly** - Update tracking files immediately after completion
5. **Document Limits** - [!] **Max 2000 lines per journal document**

### File System

```
.trellis/
|-- .developer           # Developer identity (gitignored)
|-- config.yaml          # Project-level configuration
|-- .runtime/            # Session-scoped active task runtime state
|-- scripts/
|   |-- __init__.py          # Python package init
|   |-- common/              # Shared utilities (Python)
|   |   |-- __init__.py
|   |   |-- paths.py         # Path utilities
|   |   |-- developer.py     # Developer management
|   |   |-- active_task.py   # Session-scoped active task resolver
|   |   +-- workflow_phase.py # Phase Index / step extraction
|   |   +-- git_context.py   # Git context implementation
|   |-- init_developer.py    # Initialize developer identity
|   |-- get_developer.py     # Get current developer name
|   |-- task.py              # Manage tasks
|   |-- get_context.py       # Get session context
|   +-- add_session.py       # One-click session recording
|-- workspace/           # Developer workspaces
|   |-- index.md         # Workspace index + Session template
|   +-- {developer}/     # Per-developer directories
|       |-- index.md     # Personal index (with @@@auto markers)
|       +-- journal-N.md # Journal files (sequential numbering)
|-- tasks/               # Task tracking
|   +-- {MM}-{DD}-{name}/
|       +-- task.json
|-- spec/                # [!] MUST READ before coding
|   |-- index.md                      # Master index
|   |-- library-assets/               # trellis-library asset authoring
|   |   |-- index.md
|   |   |-- spec-authoring.md
|   |   |-- template-authoring.md
|   |   |-- checklist-authoring.md
|   |   +-- manifest-maintenance.md
|   |-- scripts/                      # Script conventions
|   |   |-- index.md
|   |   |-- python-conventions.md
|   |   +-- shell-conventions.md
|   |-- agents/                       # Agent source asset definitions (multi-tool deployment)
|   |   +-- index.md
|   |-- commands/                     # Command workflows
|   |   +-- index.md
|   |-- skills/                       # Skill definitions
|   |   +-- index.md
|   |-- docs/                         # Documentation conventions
|   |   +-- index.md
|   |-- guides/                       # Thinking guides
|   |   |-- index.md
|   |   |-- cross-layer-thinking-guide.md
|   |   +-- *.md
|   |-- universal-domains/            # Cross-cutting workflow domain specs
|   |   +-- (ai-execution, context-engineering, agent-collaboration, ...)
|   |-- checklists/                   # Workflow gate checklists
|   |-- templates/                    # PRD, handoff, readiness templates
|   |-- examples/                     # Example artifacts
|   +-- platforms/                    # Platform-specific specs (e.g., cli/)
+-- workflow.md             # This document
```

---

## Session Start Process

> Steps 1–3 mirror the Quick Start above. This section adds session-specific details.

### Step 1: Get Session Context

Use the unified context script:

```bash
# Get all context in one command
python3 ./.trellis/scripts/get_context.py

# Or get JSON format
python3 ./.trellis/scripts/get_context.py --json
```

### Step 2: Read Development Guidelines [!] REQUIRED

**[!] CRITICAL: MUST read guidelines before writing any code**

Based on what you'll develop, read the corresponding guidelines:

```bash
# Read the master spec index
cat .trellis/spec/index.md

# Read specific guidelines based on task type:
cat .trellis/spec/library-assets/spec-authoring.md   # If authoring specs
cat .trellis/spec/scripts/python-conventions.md      # If writing Python
cat .trellis/spec/agents/index.md                    # If defining agents
cat .trellis/spec/commands/index.md                  # If defining commands

# Always read shared guides
cat .trellis/spec/guides/index.md
```

### Step 3: Select Task to Develop

Use the task management script:

```bash
# List active tasks
python3 ./.trellis/scripts/task.py list

# Create new task (creates directory with task.json)
python3 ./.trellis/scripts/task.py create "<title>" --slug <task-name>
```

---

## Development Process

### Task Development Flow

Follow the **Phase Index** below for the canonical workflow. This section provides a quick summary only.

```
Plan (Phase 1)     → Brainstorm, produce PRD, curate context, activate task
Execute (Phase 2)  → Dispatch sub-agents to implement, check, update spec
Finish (Phase 3)   → Commit code, then archive + record session via /finish-work
```

See the [Phase Index](#phase-index) for step-by-step instructions and routing rules.

### Code Quality Checklist

**Must pass before commit**:
- [OK] Lint checks pass (project-specific command)
- [OK] Type checks pass (if applicable)
- [OK] Library/spec validation passes (if this is a docs/spec project)
- [OK] Manual feature testing passes

**Project-specific checks**:
- For `trellis-library` asset changes: `python3 trellis-library/cli.py validate --strict-warnings`
- For skills: `./scripts/validate-skills.sh`
- See `.trellis/spec/index.md` for full list of applicable guidelines

---

## Session End

### One-Click Session Recording

After the human has tested and committed the code, use `/trellis:finish-work` to archive first and then record the session journal:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"
python3 ./.trellis/scripts/task.py current --source
```

This automatically:
1. Detects current journal file
2. Creates new file if 2000-line limit exceeded
3. Appends session content
4. Updates index.md (sessions count, history table)
5. Runs metadata closure checks before and after session write
6. Auto-commits `.trellis/workspace` and `.trellis/tasks` metadata changes

### Pre-end Checklist

Use `/trellis:finish-work` command to run through:
1. [OK] All code committed, commit message follows convention
2. [OK] Session recorded via `record-session-helper.py` after archive
3. [OK] No lint/test errors
4. [OK] `task.py archive` completed before `record-session-helper.py`
5. [OK] `.trellis/tasks` clean and active task pointer cleared after archive
6. [OK] Spec docs updated if needed

---

## File Descriptions

### 1. workspace/ - Developer Workspaces

**Purpose**: Record each AI Agent session's work content

**Structure** (Multi-developer support):
```
workspace/
|-- index.md              # Main index (Active Developers table)
+-- {developer}/          # Per-developer directory
    |-- index.md          # Personal index (with @@@auto markers)
    +-- journal-N.md      # Journal files (sequential: 1, 2, 3...)
```

**When to update**:
- [OK] End of each session
- [OK] Complete important task
- [OK] Fix important bug

### 2. spec/ - Development Guidelines

**Purpose**: Documented standards for consistent development

**Structure** (Meta-project adapted):
```
spec/
|-- index.md                  # Master index (start here)
|-- library-assets/           # trellis-library asset authoring
|   |-- index.md
|   |-- spec-authoring.md
|   |-- template-authoring.md
|   |-- checklist-authoring.md
|   +-- manifest-maintenance.md
|-- scripts/                  # Python/Shell script conventions
|   |-- index.md
|   |-- python-conventions.md
|   +-- shell-conventions.md
|-- agents/                   # Agent source asset definitions (multi-tool deployment)
|   +-- index.md
|-- commands/                 # Trellis command workflows
|   +-- index.md
|-- skills/                   # Skill definition patterns
|   +-- index.md
|-- docs/                     # Documentation conventions
|   +-- index.md
|-- guides/                   # Thinking guides
|   |-- index.md
|   +-- *.md
|-- universal-domains/        # Cross-cutting workflow domain specs
|-- checklists/               # Workflow gate checklists
|-- templates/                # PRD, handoff, readiness templates
|-- examples/                 # Example artifacts
+-- platforms/                # Platform-specific specs (e.g., cli/)
```

**When to update**:
- [OK] New pattern discovered
- [OK] Bug fixed that reveals missing guidance
- [OK] New convention established

### 3. Tasks - Task Tracking

Each task is a directory containing `task.json`:

```
tasks/
|-- 01-21-my-task/
|   +-- task.json
+-- archive/
    +-- 2026-01/
        +-- 01-15-old-task/
            +-- task.json
```

**Commands**:
```bash
python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>]   # Create task directory
python3 ./.trellis/scripts/task.py archive <name>  # Archive to archive/{year-month}/
python3 ./.trellis/scripts/task.py list            # List active tasks
python3 ./.trellis/scripts/task.py list-archive    # List archived tasks
```

---

## Best Practices

### [OK] DO - Should Do

1. **Before session start**:
   - Run `python3 ./.trellis/scripts/get_context.py` for full context
   - [!] **MUST read** relevant `.trellis/spec/` docs

2. **During development**:
   - [!] **Follow** `.trellis/spec/` guidelines
   - For cross-layer features, use `/trellis:check`
   - Develop only one task at a time
   - Run lint and tests frequently

3. **After development complete**:
   - Use `/trellis:finish-work` for completion checklist
   - After fix bug, use `/trellis:break-loop` for deep analysis
   - Main session proposes the commit plan after testing passes (Phase 3.1); user confirms before execution
   - Use `/trellis:finish-work` for archive + journal close-out

### [X] DON'T - Should Not Do

1. [!] **Don't** skip reading `.trellis/spec/` guidelines
2. [!] **Don't** let journal single file exceed 2000 lines
3. **Don't** develop multiple unrelated tasks simultaneously
4. **Don't** commit code with lint/test errors
5. **Don't** forget to update spec docs after learning something
6. **Don't** commit code with `sub-agent` sessions — only the main session may propose commits, and only after explicit user confirmation (per Phase 3.1)

---

## Quick Reference

### Must-read Before Development

| Task Type | Must-read Document |
|-----------|-------------------|
| Author a spec (trellis-library) | `library-assets/spec-authoring.md` + `manifest-maintenance.md` |
| Author a template/checklist | `library-assets/template-authoring.md` or `checklist-authoring.md` |
| Modify manifest.yaml | `library-assets/manifest-maintenance.md` |
| Write/modify Python scripts | `scripts/python-conventions.md` |
| Write/modify Shell scripts | `scripts/shell-conventions.md` |
| Define an agent | `agents/index.md` |
| Define a command | `commands/index.md` |
| Define a skill | `skills/index.md` |
| Any task | `guides/index.md` (always) |

### Commit Convention

```bash
git commit -m "type(scope): description"
```

**Type**: feat, fix, docs, refactor, test, chore
**Scope**: Module name (e.g., auth, api, ui)

### Common Commands

```bash
# Session management
python3 ./.trellis/scripts/get_context.py    # Get full context
python3 ./.trellis/scripts/get_context.py --mode phase --step 1.2 --platform codex

# Task management
python3 ./.trellis/scripts/task.py list      # List tasks
python3 ./.trellis/scripts/task.py create "<title>" # Create task
python3 ./.trellis/scripts/task.py current --source # Show active task source

# Slash commands
/trellis:finish-work          # Post-commit close-out
/trellis:break-loop           # Post-debug analysis
/trellis:check                # Cross-layer + quality verification
```

---

## Summary

Following this workflow ensures:
- [OK] Continuity across multiple sessions
- [OK] Consistent code quality
- [OK] Trackable progress
- [OK] Knowledge accumulation in spec docs
- [OK] Transparent team collaboration

**Core Philosophy**: Read before write, follow standards, record promptly, capture learnings

## Phase Index

### Plan

#### 1.1 Brainstorm / PRD

- Create the task if none exists.
- Use `trellis-brainstorm` to clarify requirements with the user.
- Produce or refine `prd.md`.

#### 1.2 Curate JSONL Context

- Curate `implement.jsonl` and `check.jsonl`.
- Include only spec and research files.
- Do not include code paths.
- Research-heavy work should persist findings into `research/*.md` first.

#### 1.3 Enter Execute Phase

- Run `python3 ./.trellis/scripts/task.py start <task-dir>`.
- This activates session-scoped task state and moves the task into `in_progress`.

### Execute

#### 2.1 Implement

- Default path: dispatch `trellis-implement`.
- Main session edits code only when the user's current message explicitly opts out of sub-agents.

#### 2.2 Check

- Dispatch `trellis-check`.
- Fix issues directly, re-run checks, and ensure spec sync is considered.

#### 2.3 Update Spec

- If implementation or debugging revealed durable knowledge, update `.trellis/spec/`.
- Prefer concrete contracts and conventions over abstract notes.

### Finish

#### 3.1 Commit & Verify

1. After implementation is verifiably complete, the main session **proposes the commit plan** — state which files will be committed, the commit message, and the rationale.
2. Wait for **explicit user confirmation**.
3. Execute `git add` + `git commit` only after confirmation.
4. Verify the working tree is clean (paths outside `.trellis/workspace/` and `.trellis/tasks/` must have no uncommitted changes).
5. `finish-work` is not the place to make the code commit — it only archives and journals.

#### 3.2 Close-Out

- Run `/trellis:finish-work` after code commits are done.
- Archive completed task(s).
- Record the session journal.

[workflow-state:no_task]
No active task. **A Direct answer** — pure Q&A / explanation / lookup / chat; no file writes + one-line answer + repo reads ≤ 2 files → AI judges, no override needed.
**B Create a task** — any implementation / code change / build / refactor work. Entry sequence: (1) `python3 ./.trellis/scripts/task.py create "<title>"` to create the task (status=planning, breadcrumb switches to [workflow-state:planning] for brainstorm + jsonl phase guidance) → (2) load `trellis-brainstorm` skill to discuss requirements with the user and iterate on prd.md → (3) once prd is done and jsonl is curated, run `task.py start <task-dir>` to enter [workflow-state:in_progress] for the implementation skeleton. For research-heavy work, dispatch `trellis-research` sub-agents — main agent must NOT do 3+ inline WebFetch / WebSearch / `gh api` calls. **"It looks small" is NOT grounds for downgrading B to A or C**.
**C Inline change** (per-turn only, escape hatch for B) — the user's CURRENT message MUST contain one of: "skip trellis" / "no task" / "just do it" / "don't create a task" / "跳过 trellis" / "别走流程" / "小修一下" / "直接改" / "先别建任务" → briefly acknowledge ("ok, skipping trellis flow this turn"), then inline. **Without seeing one of these phrases you must NOT inline on your own**; do not invent an override the user never said.
[/workflow-state:no_task]

[workflow-state:planning]
Load the `trellis-brainstorm` skill and iterate on prd.md with the user.
Phase 1.2 (required, once): before `task.py start`, you MUST curate `implement.jsonl` and `check.jsonl` — list the spec / research files sub-agents need so they get the right context injected. You may skip only if the jsonl already has agent-curated entries (the seed `_example` row alone doesn't count).
Then run `task.py start <task-dir>` to flip status to in_progress.
Research output **must** land in `{task_dir}/research/*.md`, written by `trellis-research` sub-agents. The main agent should not inline WebFetch / WebSearch — the PRD only links to research files.
[/workflow-state:planning]

[workflow-state:in_progress]
**Flow**: trellis-implement → trellis-check → trellis-update-spec → commit (Phase 3.1) → `/trellis:finish-work`.
**Default (no override)**: dispatch the `trellis-implement` / `trellis-check` sub-agents — the main agent does NOT edit code by default. Phase 3.1 commit (required, once): after trellis-update-spec, or whenever implementation is verifiably complete, the main agent **proposes the commit plan** — state the commit plan in user-facing text, then run `git commit` after user confirmation — BEFORE suggesting `/trellis:finish-work`. `/finish-work` refuses to run on a dirty working tree (paths outside `.trellis/workspace/` and `.trellis/tasks/`).
**Inline override** (per-turn only, escape hatch for sub-agent dispatch): the user's CURRENT message MUST explicitly contain one of: "do it inline" / "no sub-agent" / "你直接改" / "别派 sub-agent" / "main session 写就行" / "不用 sub-agent". **Without seeing one of these phrases you must NOT inline on your own**; do not invent an override the user never said.
[/workflow-state:in_progress]

[workflow-state:completed]
Code committed via Phase 3.1; run `/trellis:finish-work` to wrap up (archive the task + record session).
If you reach this state with uncommitted code, return to Phase 3.1 first — propose the commit plan and get user confirmation before `/finish-work`. `/finish-work` refuses to run on a dirty working tree.
`task.py archive` deletes any runtime session files that still point at the archived task.
[/workflow-state:completed]

[workflow-state:my-status]
your per-turn prompt text
[/workflow-state:my-status]

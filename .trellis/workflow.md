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
- iFlow cli: `iflow-agent` or `iflow-<task>`

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
|-- scripts/
|   |-- __init__.py          # Python package init
|   |-- common/              # Shared utilities (Python)
|   |   |-- __init__.py
|   |   |-- paths.py         # Path utilities
|   |   |-- developer.py     # Developer management
|   |   +-- git_context.py   # Git context implementation
|   |-- multi_agent/         # Multi-agent pipeline scripts
|   |   |-- __init__.py
|   |   |-- start.py         # Start worktree agent
|   |   |-- status.py        # Monitor agent status
|   |   |-- create_pr.py     # Create PR
|   |   +-- cleanup.py       # Cleanup worktree
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
|   |-- agents/                       # Agent definitions
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
+-- workflow.md             # This document
```

---

## Session Start Process

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

```
1. Create or select task
   --> python3 ./.trellis/scripts/task.py create "<title>" --slug <name> or list

2. Write code according to guidelines
   --> Read .trellis/spec/ docs relevant to your task
   --> For cross-layer: read .trellis/spec/guides/

3. Self-test
   --> Run project's lint/test commands (see spec docs)
   --> Manual feature testing

4. Commit code
   --> git add <files>
   --> git commit -m "type(scope): description"
       Format: feat/fix/docs/refactor/test/chore

5. Final close-out
   --> python3 ./.trellis/scripts/workflow/record-session-helper.py --title "Title" --commit "hash"
   --> python3 ./.trellis/scripts/task.py archive <task-name>
   --> git status --short .trellis/tasks .trellis/.current-task
```

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

After the human has tested and committed the code, record the session first and archive second:

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

python3 ./.trellis/scripts/task.py archive <task-name>
git status --short .trellis/tasks .trellis/.current-task
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
2. [OK] Session recorded via `record-session-helper.py`
3. [OK] No lint/test errors
4. [OK] `record-session-helper.py` completed before `task.py archive`
5. [OK] `.trellis/tasks` and `.trellis/.current-task` clean after archive
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
|-- agents/                   # OpenCode agent definitions
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
   - For cross-layer features, use `/trellis:check-cross-layer`
   - Develop only one task at a time
   - Run lint and tests frequently

3. **After development complete**:
   - Use `/trellis:finish-work` for completion checklist
   - After fix bug, use `/trellis:break-loop` for deep analysis
   - Human commits after testing passes
   - Use `record-session-helper.py`, then archive the completed task

### [X] DON'T - Should Not Do

1. [!] **Don't** skip reading `.trellis/spec/` guidelines
2. [!] **Don't** let journal single file exceed 2000 lines
3. **Don't** develop multiple unrelated tasks simultaneously
4. **Don't** commit code with lint/test errors
5. **Don't** forget to update spec docs after learning something
6. [!] **Don't** execute `git commit` - AI should not commit code

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
python3 ./.trellis/scripts/workflow/record-session-helper.py    # Record session with metadata closure

# Task management
python3 ./.trellis/scripts/task.py list      # List tasks
python3 ./.trellis/scripts/task.py create "<title>" # Create task

# Slash commands
/trellis:finish-work          # Pre-commit checklist
/trellis:break-loop           # Post-debug analysis
/trellis:check-cross-layer    # Cross-layer verification
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

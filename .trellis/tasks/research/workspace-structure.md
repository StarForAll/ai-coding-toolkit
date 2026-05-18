# Research: Trellis Workspace Structure

- **Query**: Workspace directory layout, journal system, runtime directory, developer identity, task storage
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/workspace/xzc/index.md` | Workspace index for developer xzc (286 lines) |
| `.trellis/workspace/xzc/journal-5.md` | Active journal file (~1906/2000 lines) |
| `.trellis/.developer` | Developer identity file |
| `.trellis/.runtime/` | Runtime state directory |
| `.trellis/.runtime/sessions/` | Session-scoped active task pointers |
| `.trellis/tasks/` | Active task directories |
| `.trellis/tasks/archive/` | Archived task directories |
| `.trellis/scripts/common/session_context.py` | Session context generation (26,056 bytes) |

### Workspace Directory Layout

```
.trellis/
  .version                    # Trellis version (0.5.17)
  .developer                  # Developer identity
  .template-hashes.json       # Template hash tracking
  config.yaml                 # Main configuration
  workflow.md                 # Single source of truth for workflow

  workspace/
    xzc/
      index.md                # Workspace index with session history
      journal-1.md            # Archived journal (~1987 lines)
      journal-2.md            # Archived journal (~2000 lines)
      journal-3.md            # Archived journal (~1984 lines)
      journal-4.md            # Archived journal (~1969 lines)
      journal-5.md            # Active journal (~1906 lines)

  .runtime/
    sessions/                 # Per-session active task pointers
    update-check-*            # Version check marker files per session

  tasks/
    03-19-implement-agents-source/   # Active task (planning)
    03-19-implement-commands-source/ # Active task (planning)
    archive/                         # Archived tasks
    research/                        # Research output directory
    _research/                       # Another research directory

  spec/
    index.md                  # Master spec index
    <package>/                # Per-package spec directories
      <layer>/                # Per-layer spec files

  scripts/
    task.py                   # Main task CLI
    common/
      active_task.py          # Active task resolution
      task_store.py           # Task CRUD operations
      task_context.py         # JSONL context management
      workflow_phase.py       # Workflow phase extraction
      paths.py                # Path constants
      session_context.py      # Session context generation
```

### Journal System

- Workspace index (`index.md`) tracks all sessions with `@@@auto` markers:
  - `@@@auto:current-status` — Active file, total sessions, last active date
  - `@@@auto:active-documents` — Journal file table with line counts
  - `@@@auto:session-history` — Full session history with dates, titles, commits, branches
- New journal file created when current exceeds 2000 lines (configurable via `config.yaml`)
- 242 total sessions recorded; currently on journal-5
- Sessions recorded via `add_session.py` or `record-session` mechanism
- Auto-commit on session recording (configurable)

### Runtime Directory

- `.trellis/.runtime/sessions/` — Per-session active task pointers
  - Files: `<context-key>.json` containing active task reference
  - Context key derived from session/conversation/transcript ID
  - Empty when no sessions are active
- `.trellis/.runtime/degraded-active-task.json` — Fallback when no session identity
- `.trellis/.runtime/update-check-*` — Version check markers per session

### Task Storage

- Active tasks live in `.trellis/tasks/<MM-DD-slug>/`
- Each task directory contains:
  - `task.json` — Task metadata (id, title, status, priority, assignee, phases, subtasks)
  - `implement.jsonl` — Spec/research context for implement sub-agent
  - `check.jsonl` — Spec/research context for check sub-agent
  - `prd.md` — Product requirements document (if created during brainstorm)
  - `research/` — Research output directory
- Archived tasks moved to `.trellis/tasks/archive/`

### task.json Structure

```json
{
  "id": "implement-commands-source",
  "name": "implement-commands-source",
  "title": "实现 commands/ 源资产层，完善 spec/commands 规范",
  "status": "planning",
  "priority": "P2",
  "creator": "xzc",
  "assignee": "xzc",
  "createdAt": "2026-03-19",
  "base_branch": "main",
  "current_phase": 0,
  "next_action": [
    {"phase": 1, "action": "implement"},
    {"phase": 2, "action": "check"},
    {"phase": 3, "action": "finish"},
    {"phase": 4, "action": "create-pr"}
  ],
  "subtasks": [],
  "children": [],
  "parent": null
}
```

### Session Context Generation

`session_context.py` (26,056 bytes):
- Produces context JSON/text for AI agents
- Default mode: git info, recent commits, active tasks, spec indexes
- Record mode: session recording context for journal entries
- Used by the SessionStart hook to inject initial context

### Connections

- Workspace journals connect to the session recording mechanism (Phase 3.3)
- Runtime sessions connect to the hook system (active task resolution per turn)
- Task storage connects to the task CLI (`task.py`) and the state machine
- The `.developer` file provides identity for session recording and attribution
- Template hashes connect to the upgrade system for drift detection
- The spec directory is read by skills (trellis-before-dev) and referenced in JSONL

## Caveats / Not Found

- The exact format of runtime session pointer files was not inspected (directory was empty)
- How journal auto-commit interacts with git was not traced in detail
- The relationship between `tasks/research/` and `tasks/_research/` (two separate directories) is unclear

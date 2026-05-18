# Research: Trellis Phase Workflow

- **Query**: Phase workflow structure, step numbering, state machine, and phase transitions
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/workflow.md` | Single source of truth for entire workflow definition (701 lines) |
| `.trellis/scripts/common/workflow_phase.py` | Extracts step-level content from workflow.md (6,878 bytes) |
| `.trellis/scripts/task.py` | Task CLI entry point driving phase transitions (522 lines) |
| `.trellis/scripts/common/paths.py` | Path constants for tasks, spec, archive directories (12,422 bytes) |

### Phase Structure

The workflow has 3 phases with numbered sub-steps:

**Phase 1 — Plan** (lines 145-175 in workflow.md):
- Step 1.0: Ensure Task Exists (`task create` or use existing)
- Step 1.1: Auto-Context (load spec index, PRD if exists)
- Step 1.2: Classify Complexity (trivial / small / medium / large)
- Step 1.3: Research & PRD (delegate to `trellis-research`, curate JSONL)
- Step 1.4: Design Plan (architectural decisions, test strategy)
- Step 1.5: Review Gate (self-review or peer-review before implementation)

**Phase 2 — Execute** (lines 177-215 in workflow.md):
- Step 2.1: Implement (dispatch `trellis-implement` sub-agent, or inline for Codex)
- Step 2.2: Self-Check (dispatch `trellis-check` sub-agent, or inline)
- Step 2.3: Iterate (fix issues found by check, re-run until clean)

**Phase 3 — Finish** (lines 217-245 in workflow.md):
- Step 3.1: Update Specs (capture new patterns/conventions via `trellis-update-spec`)
- Step 3.2: Update Docs (README, changelog if applicable)
- Step 3.3: Record Session (journal entry via `record-session`)
- Step 3.4: Final Review (ensure all checks pass)
- Step 3.5: Finish Work (`task finish`, archive if complete)

### State Machine

Task status transitions:
```
no_task --> planning (task create)
planning --> in_progress (task start)
in_progress --> completed (task archive after finish)
```

`stale` is a pseudo-status detected by `inject-workflow-state.py` when the active task pointer exists but the task's actual status has changed.

Breadcrumb tags in workflow.md (lines 155-244):
- `[workflow-state:no_task]` — no active task
- `[workflow-state:stale]` — active task pointer out of sync
- `[workflow-state:planning]` — Phase 1, sub-agent dispatch mode
- `[workflow-state:planning-inline]` — Phase 1, Codex inline mode
- `[workflow-state:in_progress]` — Phase 2, sub-agent dispatch mode
- `[workflow-state:in_progress-inline]` — Phase 2, Codex inline mode
- `[workflow-state:completed]` — Phase 3

### Platform-Specific Conditional Blocks

workflow.md uses bracket markers for platform-specific instructions:
- `[Claude Code, Cursor, ...]` ... `[/Claude Code, Cursor, ...]` — show only on those platforms
- `workflow_phase.py:filter_platform()` strips blocks not matching the current platform

### Code Patterns

- `workflow_phase.py:get_phase_index()` returns Phase Index + step bodies
- `workflow_phase.py:get_step(step_number)` extracts a single step section
- `task.py:cmd_start()` (line 72) flips status planning -> in_progress and sets active task
- `task.py:cmd_finish()` (line 164) clears active task, triggers after_finish hooks
- `task.py:cmd_archive()` moves task dir to archive/

### Connections

- Phase transitions are driven by `task.py` CLI commands called by the AI agent during workflow execution
- The hook system (`inject-workflow-state.py`) reads the active task status to select the correct breadcrumb tag
- JSONL files are curated during Phase 1.3 (research step) and consumed during Phase 2 (implement/check)
- Skills are routed based on Phase and user intent (see skill routing table in workflow.md lines 253-305)

## Caveats / Not Found

- The `current_phase` field in task.json appears to be informational; actual phase is inferred from task status + breadcrumb
- Phase numbering is 1-based in workflow.md but `current_phase: 0` in task.json seems to mean "not started yet"

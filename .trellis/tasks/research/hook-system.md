# Research: Trellis Hook System

- **Query**: Hook lifecycle, inject-workflow-state.py internals, platform detection, breadcrumb resolution
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.claude/hooks/inject-workflow-state.py` | Per-turn breadcrumb hook (404 lines) |
| `.trellis/workflow.md` | Breadcrumb tag blocks (lines 155-244) |
| `.trellis/scripts/common/active_task.py` | Active task resolution used by hook (24,740 bytes) |
| `.trellis/config.yaml` | Hook configuration and event settings |

### Hook Architecture

**inject-workflow-state.py** runs on every user prompt submission:
- Event name: `UserPromptSubmit` (all platforms except Gemini)
- Gemini uses `BeforeAgent` event name
- Input: JSON on stdin with session/conversation context
- Output: JSON with `hookSpecificOutput.additionalContext` containing the breadcrumb

### Key Functions

**`find_trellis_root()`** (line 106):
- CWD-robust root discovery
- Walks up from current directory to find directory containing `.trellis/`
- Ensures hook works regardless of CWD

**`_detect_platform()`** (line 124):
- Detects AI platform from:
  1. Environment variables (platform-specific env keys)
  2. Script path (infers platform from which config dir the hook lives in)
- Returns platform name string used for breadcrumb selection

**`get_active_task()`** (line 169):
- Resolves current active task
- Returns tuple: (task_id, status, source)
- Delegates to `active_task.py` for session-scoped resolution
- Falls back to degraded mode when no session identity available

**`load_breadcrumbs()`** (line 207):
- Parses `[workflow-state:STATUS]` blocks from workflow.md
- Uses regex `_TAG_RE` to find tag markers
- Returns dict mapping status keys to their content blocks

**`resolve_breadcrumb_key()`** (line 273):
- Picks the correct breadcrumb tag based on:
  1. Active task status (planning/in_progress/completed/no_task/stale)
  2. Platform dispatch mode (appends `-inline` suffix for inline mode)
- Returns the key used to look up breadcrumb content

**`build_breadcrumb()`** (line 298):
- Assembles `<workflow-state>` XML block
- Contains header (task info, phase, status) + body (step instructions from breadcrumb)
- Includes `<!-- trellis-hook-injected -->` marker that sub-agents check for

**`main()`** (line 344):
- Entry point
- Reads stdin JSON, resolves task, emits breadcrumb JSON
- Output format: `{"hookSpecificOutput": {"additionalContext": "<breadcrumb-xml>"}}`

### Session Identity Resolution

From `active_task.py`:
- `_ENV_SESSION_KEYS`: Environment variables for session ID per platform
- `_ENV_CONVERSATION_KEYS`: Conversation ID env vars
- `_ENV_TRANSCRIPT_KEYS`: Transcript ID env vars
- Context key generated from whichever ID is available
- Active task pointer stored per session under `.trellis/.runtime/sessions/<context-key>.json`
- Degraded fallback: `.trellis/.runtime/degraded-active-task.json` (used when no session identity)

### Breadcrumb Content

Each breadcrumb block in workflow.md contains:
- Step-by-step instructions for the current workflow state
- Platform-specific conditional blocks (filtered at runtime)
- Skill routing recommendations
- Phase-appropriate actions

### Connections

- Hook reads workflow.md (single source of truth) and active_task.py (task resolution)
- Output breadcrumb is injected into every AI agent turn, ensuring workflow state awareness
- Sub-agents check for `<!-- trellis-hook-injected -->` marker as context injection indicator
- Breadcrumb key depends on dispatch mode (from config.yaml), connecting hook to config system
- Hook uses the same platform detection logic as task_store.py for consistency

## Caveats / Not Found

- Other platform hooks (`.cursor/hooks/`, `.codex/hooks/`, etc.) were not read but follow the same pattern
- The exact JSON format of the hook input (stdin) was not inspected in detail
- Gemini's `BeforeAgent` event difference was noted but the behavioral impact was not fully traced

# Research: Trellis Agent Dispatch System

- **Query**: How main session dispatches sub-agents, agent definitions, dispatch modes, platform differences
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.claude/agents/trellis-implement.md` | Implement sub-agent definition (110 lines) |
| `.claude/agents/trellis-check.md` | Check sub-agent definition (110 lines) |
| `.claude/agents/trellis-research.md` | Research sub-agent definition (153 lines) |
| `.trellis/workflow.md` | Skill routing table and dispatch logic (lines 253-305) |
| `.trellis/config.yaml` | Codex dispatch_mode setting |

### Sub-Agent Definitions

**trellis-implement** (`.claude/agents/trellis-implement.md`):
- Purpose: Code implementation agent
- Recursion guard: Does NOT spawn another implement/check agent
- Context Loading Protocol: Checks for `<!-- trellis-hook-injected -->` marker; falls back to manual JSONL reading
- Forbidden: git commit, push, merge
- Reads `implement.jsonl` for spec/research context

**trellis-check** (`.claude/agents/trellis-check.md`):
- Purpose: Quality verification and self-fix agent
- Reviews code against specs and auto-fixes issues
- Same recursion guard and context loading protocol as implement
- Reads `check.jsonl` for spec/research context

**trellis-research** (`.claude/agents/trellis-research.md`):
- Purpose: Find, explain, and PERSIST information
- Core principle: write ONLY to `{TASK_DIR}/research/*.md`
- Forbidden: code files, spec files, scripts, git operations
- Workflow: resolve task -> understand search request -> execute search -> persist -> report
- Reports file paths + one-line summaries, not full content

### Dispatch Modes

**Sub-Agent Mode** (default on Claude, Cursor, Codex with sub-agent support):
- Main session dispatches `trellis-implement`, `trellis-check`, `trellis-research` as separate agent sessions
- Each sub-agent gets its own context window with JSONL-injected specs
- Sub-agents return results to the main session

**Inline Mode** (Codex default, also Kiro/Windsurf):
- Main session edits code directly without spawning sub-agents
- Loads `trellis-before-dev` skill instead of dispatching implement agent
- Uses `trellis-check` skill inline instead of dispatching check agent
- Configurable via `config.yaml:codex.dispatch_mode` (values: `inline` or `sub-agent`)

### Skill Routing Table

From workflow.md lines 253-305, the routing table maps user intents to skills per platform type:

| User Intent | Sub-Agent Platform | Inline Platform |
|---|---|---|
| Implement | Dispatch trellis-implement | Load trellis-before-dev skill |
| Check | Dispatch trellis-check | Load trellis-check skill inline |
| Research | Dispatch trellis-research | Dispatch trellis-research |
| Brainstorm | trellis-brainstorm skill | trellis-brainstorm skill |
| Update Spec | trellis-update-spec skill | trellis-update-spec skill |
| Break Loop | trellis-break-loop skill | trellis-break-loop skill |

### Breadcrumb Key Selection

`inject-workflow-state.py:resolve_breadcrumb_key()` (line 273):
- For Codex with `dispatch_mode=inline`, appends `-inline` suffix to breadcrumb key
- e.g., `planning` becomes `planning-inline`, `in_progress` becomes `in_progress-inline`
- Inline breadcrumbs contain different instructions (no sub-agent dispatch, direct editing)

### Connections

- Dispatch mode affects breadcrumb content (inline vs sub-agent instructions)
- JSONL files are only relevant for sub-agent dispatch (inline mode loads specs via skill)
- The hook system provides context to sub-agents via JSONL injection
- Task status transitions still work the same regardless of dispatch mode
- `task_store.py:_SUBAGENT_CONFIG_DIRS` controls which platforms get JSONL files

## Caveats / Not Found

- Other platform agent definitions (`.cursor/agents/`, `.codex/agents/`, etc.) were not read in detail but follow the same pattern
- The exact mechanism of how Claude Code spawns a sub-agent session from an agent .md file was not traced

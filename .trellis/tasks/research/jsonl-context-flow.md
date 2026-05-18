# Research: Trellis JSONL-Driven Context Flow

- **Query**: JSONL file lifecycle, seeding, curation, injection, and how specs/research reach sub-agents
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/scripts/common/task_context.py` | JSONL context management (7,042 bytes) |
| `.trellis/scripts/common/task_store.py` | Task CRUD including JSONL auto-seeding (24,263 bytes) |
| `.claude/agents/trellis-implement.md` | Implement sub-agent that reads JSONL (110 lines) |
| `.claude/agents/trellis-check.md` | Check sub-agent that reads JSONL (110 lines) |
| `.claude/hooks/inject-workflow-state.py` | Hook that injects JSONL content into sub-agent prompts (404 lines) |

### JSONL Lifecycle

1. **Seeding** (task creation):
   - `task_store.py:cmd_create()` (line 145) auto-seeds `implement.jsonl` and `check.jsonl` on sub-agent platforms
   - `_SUBAGENT_CONFIG_DIRS` (line 95) lists platform dirs that consume JSONL: `.claude`, `.cursor`, `.codex`, `.kiro`, `.gemini`, `.opencode`, `.qoder`, `.codebuddy`, `.factory`, `.github/copilot`, `.pi`
   - Each JSONL starts with `_SEED_EXAMPLE` (line 109) — a self-describing row explaining the format

2. **Curation** (Phase 1.3 — Research):
   - `task_context.py:cmd_add_context()` appends `{"file": "<path>", "reason": "<why>"}` entries
   - The AI agent adds spec files, research outputs, and PRD references during the research step
   - `task_context.py:cmd_validate()` checks JSONL syntax validity
   - `task_context.py:cmd_list_context()` lists current entries

3. **Injection** (Phase 2 — Execute):
   - The platform hook (e.g., `inject-workflow-state.py` for Claude) reads JSONL files at the start of each sub-agent session
   - Each JSONL entry's `file` path is resolved relative to the repo root
   - The hook reads each referenced file and injects its content into the sub-agent's prompt as additional context

4. **Fallback** (sub-agent context loading):
   - Sub-agents check for `<!-- trellis-hook-injected -->` marker in their prompt
   - If marker is absent (hook didn't inject), they fall back to manually reading prd.md + implement.jsonl
   - This fallback ensures sub-agents work even when hooks are misconfigured

### JSONL Entry Format

```json
{"file": ".trellis/spec/python/style.md", "reason": "Python coding style guidelines"}
```

- `file`: Relative path from repo root to a spec/research/PRD document
- `reason`: Human-readable explanation of why this file is relevant

### Code Patterns

- `task_store.py:_SUBAGENT_CONFIG_DIRS` determines which platforms get JSONL files seeded
- `task_context.py:cmd_add_context()` accepts `--type implement|check` to target specific JSONL files
- The hook reads JSONL from the task directory under `.trellis/tasks/<task-id>/`
- Implement sub-agent uses `implement.jsonl`; check sub-agent uses `check.jsonl`

### Connections

- JSONL files bridge Phase 1 (planning/research) and Phase 2 (execution)
- They ensure sub-agents receive curated context without the main agent having to repeat everything
- The spec system populates JSONL entries (spec file paths from `.trellis/spec/`)
- Research outputs (`{TASK_DIR}/research/*.md`) are also added as JSONL entries
- The fallback mechanism in sub-agents connects to the hook system

## Caveats / Not Found

- Did not find explicit documentation on how the hook parses and injects JSONL content at the code level — the hook likely reads the JSONL file, then reads each referenced file and concatenates content
- The exact injection format (how content appears in the sub-agent prompt) was not traced in detail

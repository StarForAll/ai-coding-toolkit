# Research: Reference Project Hooks, Skills, Commands, and Infrastructure (v0.5.16-2)

- **Query**: Hook files, skill directories, continue command, agent definitions
- **Scope**: internal (reference project at /tmp/trellis-0.5.16-2/)
- **Date**: 2026-05-16

## Findings

### .claude/hooks/ (3 files)

| File | Size | Description |
|---|---|---|
| `inject-workflow-state.py` | 14955 bytes | Per-turn breadcrumb hook for UserPromptSubmit |
| `inject-subagent-context.py` | 23690 bytes | Sub-agent context injection for PreToolUse (Task/Agent matcher) |
| `session-start.py` | 30670 bytes | Session initialization hook for SessionStart (startup/clear/compact) |

### .codex/hooks/ (2 files)

| File | Size | Description |
|---|---|---|
| `inject-workflow-state.py` | 14955 bytes | Identical to Claude version (shared via writeSharedHooks) |
| `session-start.py` | 18194 bytes | Codex-specific session start |

### .claude/settings.json Hook Wiring

```json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "startup", "command": "python3 .claude/hooks/session-start.py", "timeout": 30},
      {"matcher": "clear", "command": "python3 .claude/hooks/session-start.py", "timeout": 30},
      {"matcher": "compact", "command": "python3 .claude/hooks/session-start.py", "timeout": 30}
    ],
    "PreToolUse": [
      {"matcher": "Task", "command": "python3 .claude/hooks/inject-subagent-context.py", "timeout": 30},
      {"matcher": "Agent", "command": "python3 .claude/hooks/inject-subagent-context.py", "timeout": 30}
    ],
    "UserPromptSubmit": [
      {"command": "python3 .claude/hooks/inject-workflow-state.py", "timeout": 15}
    ]
  }
}
```

### .codex/hooks.json Hook Wiring

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"command": "python3 -X utf8 .codex/hooks/inject-workflow-state.py", "timeout": 15}
    ]
  }
}
```

Note: Codex only has UserPromptSubmit hook (no SessionStart or PreToolUse).

### inject-workflow-state.py Key Implementation Details

The Claude and Codex versions are IDENTICAL (same 14955 bytes, same content). Key aspects:

1. **Platform detection** (`_detect_platform`): Checks env vars (CLAUDE_PROJECT_DIR, CURSOR_PROJECT_DIR, etc.) and script path parts
2. **Active task resolution** (`get_active_task`): Uses `common.active_task.resolve_active_task` from .trellis/scripts/
3. **Breadcrumb loading** (`load_breadcrumbs`): Parses workflow.md with regex `_TAG_RE` for `[workflow-state:STATUS]` blocks
4. **Codex-specific behavior**:
   - `CODEX_SUB_AGENT_NOTICE` — tells sub-agents to ignore workflow guidance
   - `CODEX_NO_TASK_BOOTSTRAP_NOTICE` — nudges main Codex session to read `trellis-start` skill
   - `_codex_mode_banner` — emits `<codex-mode>inline</codex-mode>` or `<codex-mode>sub-agent</codex-mode>`
5. **Breadcrumb key resolution** (`resolve_breadcrumb_key`): For Codex inline mode, appends `-inline` suffix to status key (e.g., `planning-inline`, `in_progress-inline`)
6. **Breadcrumb fallback**: When tag missing, emits "Refer to workflow.md for current step."

### .agents/skills/ (20 directories)

| Directory | Description |
|---|---|
| brainstorm | Brainstorm skill (cross-platform) |
| check | Quality check skill |
| delivery | Delivery skill |
| design | Design skill |
| feasibility | Feasibility assessment skill |
| plan | Task planning skill |
| project-audit | Project-level audit skill |
| review-gate | Supplementary review skill |
| test-first | TDD skill |
| trellis-before-dev | Before-dev context loading |
| trellis-brainstorm | Trellis-specific brainstorm |
| trellis-break-loop | Debug loop breaker |
| trellis-check | Trellis quality check |
| trellis-continue | Phase router / continue |
| trellis-finish-work | Finish work / close-out |
| trellis-meta | Meta information |
| trellis-start | Session start context (legacy) |
| trellis-update-spec | Spec update skill |

Each directory contains a `SKILL.md` file.

### .claude/skills/ (6 directories)

| Directory |
|---|
| trellis-before-dev |
| trellis-brainstorm |
| trellis-break-loop |
| trellis-check |
| trellis-meta |
| trellis-update-spec |

### .claude/commands/trellis/ (12 files)

| File | Size |
|---|---|
| brainstorm.md | 23088 bytes |
| check.md | 8977 bytes |
| continue.md | 3800 bytes |
| delivery.md | 16699 bytes |
| design.md | 25442 bytes |
| feasibility.md | 24003 bytes |
| finish-work.md | 6088 bytes |
| plan.md | 26453 bytes |
| project-audit.md | 13515 bytes |
| review-gate.md | 13941 bytes |
| test-first.md | 6060 bytes |

### .claude/agents/ (3 files)

| File | Description |
|---|---|
| trellis-check.md | Check sub-agent definition |
| trellis-implement.md | Implement sub-agent definition |
| trellis-research.md | Research sub-agent definition |

### .codex/agents/ (3 files)

| File | Description |
|---|---|
| trellis-check.toml | Check sub-agent definition (TOML format) |
| trellis-implement.toml | Implement sub-agent definition (TOML format) |
| trellis-research.toml | Research sub-agent definition (TOML format) |

### .claude/commands/trellis/continue.md — Full Content

The continue command (3800 bytes) implements the Phase Router with these key aspects:

1. **Core purpose**: Resume work on current task, identify and re-enter the correct phase/step. Only re-enters current confirmed phase, no auto-advance.

2. **Execution steps**:
   - Step 1: `python3 ./.trellis/scripts/get_context.py`
   - Step 2: `python3 .trellis/scripts/workflow/workflow-state.py route [--project-root]`
   - Step 3: Route based on JSON `action` field

3. **Action routing table**:

| action | Meaning | Execution |
|---|---|---|
| `first_entry` | No active task, no resumable tasks | Route to `/trellis:feasibility` |
| `reenter` | Re-enter current phase | Route to `/trellis:<target>` |
| `awaiting_confirmation` | Phase complete, awaiting user confirm | Show completed/incomplete/missing items |
| `blocked` | Execution blocked | Show blockers, do not advance |
| `recovery_needed` | Cannot determine active task | Ask user to specify task |
| `repair_needed` | State files missing/corrupt | Run `workflow-state.py repair` |
| `embed_invalid` | Embedded state invalid | Stop, prompt user to check install |

4. **Implementation constraints**:
   - One concrete leaf task at a time
   - Auto-execute before-dev on entering implementation
   - Serial, not auto-continue; must re-enter `/trellis:continue` after each task
   - Frontend visual first-version tasks cannot use Codex as primary executor

5. **Next-step recommendation output**: AI must output a recommendation table at the end with columns for intent, Claude/OpenCode entry, Codex entry, and description.

## Caveats / Not Found

- The Codex hooks only have UserPromptSubmit (no session start or sub-agent injection hooks)
- Both Claude and Codex inject-workflow-state.py are identical — shared implementation
- The `workflow-state.py route` command referenced in continue.md is a separate script not inspected here
- No `trellis-start` skill directory exists in `.claude/skills/` — it only exists in `.agents/skills/`

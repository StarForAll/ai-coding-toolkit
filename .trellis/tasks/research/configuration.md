# Research: Trellis Configuration System

- **Query**: config.yaml structure, platform detection, dispatch modes, session recording, task lifecycle hooks
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/config.yaml` | Main configuration file (91 lines) |
| `.trellis/.version` | Version identifier (`0.5.17`) |
| `.trellis/.developer` | Developer identity (`name=xzc`) |
| `.trellis/.template-hashes.json` | Template hash tracking for upgrade drift detection |

### config.yaml Structure

Key configuration sections (91 lines total):

**Session Recording**:
- `session_recording.commit_message`: Template for auto-commit messages
- `session_recording.max_journal_lines`: 2000 (triggers new journal file)

**Task Lifecycle Hooks**:
- `task_lifecycle.hooks`: Hooks triggered on task state transitions
- `task_lifecycle.auto_commit`: Whether to auto-commit on state changes

**Monorepo/Packages**:
- Package detection and scope configuration
- Single-repo mode for this project (no monorepo structure)

**Codex Dispatch Mode**:
- `codex.dispatch_mode`: `inline` or `sub-agent`
- Affects breadcrumb key selection and skill routing
- Default for Codex is `inline`; other platforms use sub-agent dispatch

### Platform Detection

From `inject-workflow-state.py:_detect_platform()` (line 124):
- Primary: Environment variables specific to each platform
- Secondary: Script path inference (which config dir the hook lives in)
- Supported platforms: Claude, Cursor, Codex, OpenCode, Gemini, Kiro, Qoder, CodeBuddy, Droid, Copilot, Pi

From `active_task.py`:
- `_ENV_SESSION_KEYS`: Platform-specific env vars for session ID
- `_ENV_CONVERSATION_KEYS`: Platform-specific env vars for conversation ID
- `_ENV_TRANSCRIPT_KEYS`: Platform-specific env vars for transcript ID

### Version and Template Management

- `.trellis/.version`: Current Trellis version (`0.5.17`)
- `.trellis/.template-hashes.json`: Tracks expected hashes of template files
  - Used during upgrade to detect drift between local files and upstream templates
  - When Trellis is upgraded, template hashes change and `.new` files are created for conflicts
- `.trellis/.developer`: Developer identity for session recording and attribution

### Platform Config Directories

Each supported platform has its own config directory containing:
- `agents/` — Agent definition files (mirroring `.claude/agents/`)
- `hooks/` — Hook scripts (mirroring `.claude/hooks/`)
- `skills/` — Skill directories (mirroring `.claude/skills/`)
- `config.*` — Platform-specific configuration (e.g., `.codex/config.toml`)

From `task_store.py:_SUBAGENT_CONFIG_DIRS` (line 95):
`.claude`, `.cursor`, `.codex`, `.kiro`, `.gemini`, `.opencode`, `.qoder`, `.codebuddy`, `.factory`, `.github/copilot`, `.pi`

### Connections

- config.yaml dispatch_mode affects breadcrumb key resolution in the hook
- Platform detection connects config to hook behavior and JSONL seeding
- Template hashes connect to the upgrade system (detecting drift)
- Developer identity flows into session recording and journal attribution
- Task lifecycle hooks connect to `task.py` commands (after_finish triggers)

## Caveats / Not Found

- The full config.yaml was not re-read in this session; details are from the previous session's analysis
- How `.new` files are resolved during upgrade was not traced in detail
- The interaction between platform config directories and the central `.trellis/` directory was not fully mapped

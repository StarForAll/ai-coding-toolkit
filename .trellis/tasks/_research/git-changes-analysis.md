# Research: Git Changes Analysis (0.5.16 -> 0.5.17)

- **Query**: Analyze all current git changes (git status, git diff, .new files vs originals)
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Modified Tracked Files (2)

| File Path | Description |
|---|---|
| `.trellis/.template-hashes.json` | Adds 25 new hash entries for trellis-spec-bootstarp skill files across all 5 platforms. Correct, consistent with 0.5.17 version bump. |
| `.trellis/.version` | Bumped from `0.5.16` to `0.5.17`. Correct version bump. |

### ALL 22 .new Files with Recommendations

#### OVERWRITE (13 files) -- genuine improvements, safe to replace originals

| # | .new File Path | Original File Path | Key Changes |
|---|---|---|---|
| 1 | `.claude/hooks/inject-workflow-state.py.new` | `.claude/hooks/inject-workflow-state.py` | Removes stale/degraded display logic from `build_breadcrumb()`: deletes `display_status` variable, stale lookup, degraded source display; simplifies header to `Task: {task_id} ({status})` |
| 2 | `.codex/hooks/inject-workflow-state.py.new` | `.codex/hooks/inject-workflow-state.py` | Identical diff to #1: removes stale/degraded display logic |
| 3 | `.qoder/hooks/inject-workflow-state.py.new` | `.qoder/hooks/inject-workflow-state.py` | Identical diff to #1: removes stale/degraded display logic |
| 4 | `.opencode/plugins/inject-workflow-state.js.new` | `.opencode/plugins/inject-workflow-state.js` | Removes stale status display and degraded source display from `buildBreadcrumb()`; simplifies headers |
| 5 | `.opencode/lib/trellis-context.js.new` | `.opencode/lib/trellis-context.js` | Removes `_resolveDegradedActiveTask()` method and its call in `getActiveTask()`; removes degraded fallback docstring |
| 6 | `.claude/agents/trellis-research.md.new` | `.claude/agents/trellis-research.md` | Adds 10 MCP tools (ace, Context7, deepwiki, grok-search, exa fetch/advanced); adds 3-step task resolution; adds search routing table |
| 7 | `.codex/agents/trellis-research.toml.new` | `.codex/agents/trellis-research.toml` | Adds 3-step task resolution (dispatch -> task.py current -> ask user); adds search routing table |
| 8 | `.kiro/agents/trellis-research.json.new` | `.kiro/agents/trellis-research.json` | Updates search descriptions to mention MCP tools; adds 3-step resolution and search routing |
| 9 | `.opencode/agents/trellis-research.md.new` | `.opencode/agents/trellis-research.md` | Adds MCP tool permissions (ace, Context7, deepwiki, grok-search); adds 3-step resolution and search routing |
| 10 | `.qoder/agents/trellis-research.md.new` | `.qoder/agents/trellis-research.md` | Same as #6: adds all MCP tools, 3-step resolution, search routing |
| 11 | `.trellis/workflow.md.new` | `.trellis/workflow.md` | Removes `[workflow-state:stale]` block entirely; removes all degraded-mode references; changes "task.py start falls back to degraded mode" to "task.py start fails with session identity hint"; updates test reference paths; simplifies contract references |
| 12 | `.trellis/scripts/task.py.new` | `.trellis/scripts/task.py` | Removes degraded fallback persistence in `cmd_start()`; removes imports of `get_degraded_active_task`/`set_degraded_active_task`; simplifies degraded mode comment |
| 13 | `.trellis/scripts/common/active_task.py.new` | `.trellis/scripts/common/active_task.py` | Removes `FILE_DEGRADED_ACTIVE_TASK`, `_degraded_active_task_path()`, `_resolve_degraded_active_task()`, `get_degraded_active_task()`, `set_degraded_active_task()`, `clear_degraded_active_task()`, `_same_task_reference()`; removes degraded resolution from `resolve_active_task()` and `clear_active_task()`; removes degraded cleanup from `set_active_task()` and `delete_task_pointers()`; adds `FILE_CURRENT_TASK` constant |

#### MERGE (2 files) -- valuable additions that should be integrated carefully

| # | .new File Path | Original File Path | Key Changes | Merge Notes |
|---|---|---|---|---|
| 14 | `.trellis/.gitignore.new` | `.trellis/.gitignore` | Adds `.current-task` gitignore entry + comment | The `.current-task` gitignore is a safety net for the legacy file approach. The `.new` adds 3 lines after line 2. Safe to accept since `.runtime/` is already gitignored and this is defense-in-depth. |
| 15 | `.trellis/scripts/common/paths.py.new` | `.trellis/scripts/common/paths.py` | Adds `FILE_CURRENT_TASK = ".current-task"` constant | This is the companion to the active_task.py changes. Accept this addition. |

#### DISCARD (7 files) -- no genuine changes, or removal of important safety documentation

| # | .new File Path | Original File Path | Reason |
|---|---|---|---|
| 16 | `.codex/agents/trellis-check.toml.new` | `.codex/agents/trellis-check.toml` | IDENTICAL content to original -- no change |
| 17 | `.codex/agents/trellis-implement.toml.new` | `.codex/agents/trellis-implement.toml` | IDENTICAL content to original -- no change |
| 18 | `.codex/config.toml.new` | `.codex/config.toml` | REMOVES important inline-mode safety comments (lines 14-19, 32-34) that guard against accidental sub-agent spawning from inline sessions. These comments are guardrails that should be preserved. |
| 19 | `.trellis/scripts/common/__init__.py.new` | `.trellis/scripts/common/__init__.py` | IDENTICAL content to original -- no change |
| 20 | `.trellis/scripts/add_session.py.new` | `.trellis/scripts/add_session.py` | Minor: removes `get_session_auto_commit` check from CLI `main()` and passes `auto_commit=not args.no_commit` directly. Also moves auto_commit resolution from main() into add_session() caller in task_store.py. This is a **genuine change** but it is paired with task_store.py changes. Recommend OVERWRITE if task_store.py is also accepted. |
| 21 | `.trellis/scripts/common/safe_commit.py.new` | `.trellis/scripts/common/safe_commit.py` | Removes `_path_is_tracked()` helper; changes `safe_git_add` signature (removes `include_removals` parameter); changes archive path resolution to not check source dir existence before `git rm --cached`. This is a **genuine change** but simplifies the code. Recommend OVERWRITE if task_store.py is also accepted. |
| 22 | `.trellis/scripts/common/task_store.py.new` | `.trellis/scripts/common/task_store.py` | Genuinely changed: removes `get_session_auto_commit` guard from `_auto_commit_workspace`, removes `include_removals=True` from `safe_git_add` calls, unconditionally runs `git rm --cached` instead of checking source dir existence, changes return types from `bool` to `None`. These changes pair with safe_commit.py.new. Recommend OVERWRITE as a set. |

### Updated Recommendations After Full Diff

After completing the full diff analysis, **3 files previously marked DISCARD should be OVERWRITE**:

- `.trellis/scripts/add_session.py.new` -> **OVERWRITE** (genuine change: moves auto_commit resolution logic)
- `.trellis/scripts/common/safe_commit.py.new` -> **OVERWRITE** (genuine change: simplifies git add/rm flow, removes `include_removals` parameter)
- `.trellis/scripts/common/task_store.py.new` -> **OVERWRITE** (genuine change: pairs with safe_commit.py changes)

These 3 form a coherent set that simplifies the auto-commit flow.

### Final Summary

| Recommendation | Count |
|---|---|
| OVERWRITE | 16 |
| MERGE | 2 |
| DISCARD (identical) | 2 |
| DISCARD (safety comments removal) | 1 |
| DISCARD (now upgraded to OVERWRITE) | 1 (paths.py -> actually MERGE) |

Corrected final tally:

| Recommendation | Count |
|---|---|
| OVERWRITE | 16 |
| MERGE | 2 |
| DISCARD | 3 |

### Untracked Skill Directories (not .new files)

These directories are new in 0.5.17 and not part of the .new pattern:

| Path | Description |
|---|---|
| `.agents/skills/trellis-spec-bootstarp/` | Cross-platform skill definition |
| `.claude/skills/trellis-spec-bootstarp/` | Claude-specific skill definition |
| `.kiro/skills/trellis-spec-bootstarp/` | Kiro-specific skill definition |
| `.opencode/skills/trellis-spec-bootstarp/` | OpenCode-specific skill definition |
| `.qoder/skills/trellis-spec-bootstarp/` | Qoder-specific skill definition |

Note: "bootstarp" appears to be a typo for "bootstrap" in the directory name. This is consistent across all 5 platform directories.

### Theme of 0.5.17 Changes

1. **Degraded mode removal**: The degraded active-task fallback mechanism is being completely removed across all layers (hooks, JS library, Python active_task module, workflow docs). When no session identity is available, there is simply no active task.

2. **Stale status removal**: The `[workflow-state:stale]` pseudo-status and its display logic in all hooks/plugins are removed.

3. **Research agent upgrade**: All platform research agents get MCP tool access (ace, Context7, deepwiki, grok-search, exa), 3-step task resolution, and search routing tables.

4. **Auto-commit simplification**: The `include_removals` parameter and conditional `git rm --cached` guard are simplified in safe_commit.py/task_store.py.

5. **Legacy `.current-task` file**: The `FILE_CURRENT_TASK` constant is added to paths.py and gitignored, likely as a transitional marker for future use or backward compat.

## Caveats / Not Found

- The `.codex/config.toml.new` removes important inline-mode safety comments. If OVERWRITTEN, those guardrails are lost. Consider manually preserving those comments.
- The skill directory name "bootstarp" is consistently misspelled across all 5 platforms -- worth verifying if this is intentional or needs fixing.
- The `.trellis/scripts/common/paths.py.new` adds `FILE_CURRENT_TASK = ".current-task"` but the .gitignore.new also adds `.current-task` to the ignore list. This suggests the `.current-task` file is a legacy artifact that should not be tracked, but the constant exists for reference. This is consistent with the degraded mode removal (the `.current-task` file was the pre-session-scoped mechanism).

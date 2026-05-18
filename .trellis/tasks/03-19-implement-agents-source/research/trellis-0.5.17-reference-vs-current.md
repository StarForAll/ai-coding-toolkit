# Research: Trellis 0.5.17 Reference vs Current Project Comparison

- **Query**: Compare fresh Trellis 0.5.17 reference install at /tmp/trellis-0.5.17 with current project at /ops/projects/personal/ai-coding-toolkit
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Version

Both projects report **0.5.17** in `.trellis/.version` — IDENTICAL.

### Summary Table

| File / Area | Status | Key Differences |
|---|---|---|
| `.trellis/.version` | IDENTICAL | Both: `0.5.17` |
| `.trellis/workflow.md` | DIFFERS | Current adds `[workflow-state:stale]` block, changes breadcrumb contract comment, changes test reference path, adds stale status to TAG-PHASE table, changes `task.py start` failure to degraded fallback, changes full contract reference path |
| `.trellis/.gitignore` | DIFFERS | Current removes `# Current task pointer` comment and `.current-task` line that exist in reference |
| `.claude/settings.json` | DIFFERS | Current adds `statusLine` block (statusline.py hook); reference lacks it |
| `.codex/config.toml` | DIFFERS | Current adds 6-line inline-mode rule comments and 3-line inline-mode override rule; reference lacks these |
| `.codex/hooks.json` | IDENTICAL | — |
| `.qoder/settings.json` | IDENTICAL | — |
| `.opencode/package.json` | IDENTICAL | — |
| `.claude/hooks/inject-workflow-state.py` | DIFFERS | Current adds stale/degraded status handling in `build_breadcrumb()` (display_status logic); 388→404 lines |
| `.codex/hooks/inject-workflow-state.py` | DIFFERS | Same stale/degraded additions as Claude hook |
| `.qoder/hooks/inject-workflow-state.py` | DIFFERS | Same stale/degraded additions as Claude hook |
| `.opencode/plugins/inject-workflow-state.js` | DIFFERS | Current adds stale/degraded status handling parallel to Python hooks |
| `.opencode/lib/trellis-context.js` | DIFFERS | Current adds `_resolveDegradedActiveTask()` method and degraded fallback resolution |
| `.claude/agents/trellis-research.md` | DIFFERS | Current has ENRICHED version with MCP tools (ace, exa, Context7, deepwiki, grok-search), tool routing table, 3-step task resolution |
| `.claude/agents/trellis-check.md` | IDENTICAL | — |
| `.claude/agents/trellis-implement.md` | IDENTICAL | — |
| `.codex/agents/trellis-research.toml` | DIFFERS | Current adds carrier comment prefix + enriched developer_instructions with MCP tool routing |
| `.codex/agents/trellis-implement.toml` | DIFFERS | Current adds 4-line carrier comment prefix; content after is IDENTICAL |
| `.codex/agents/trellis-check.toml` | DIFFERS | Current adds 4-line carrier comment prefix |
| `.qoder/agents/trellis-research.md` | DIFFERS | Current enriched with MCP tool routing + 3-step task resolution |
| `.opencode/agents/trellis-research.md` | DIFFERS | Current enriched with MCP tool routing + 3-step task resolution |
| `.kiro/agents/trellis-research.json` | CURRENT-ONLY | Does not exist in reference; current has enriched version with MCP tools |
| All shared skills (trellis-start, finish-work, continue, update-spec, spec-bootstarp, before-dev, brainstorm, break-loop, check, meta) | IDENTICAL | — |
| All session-start.py / inject-subagent-context.py hooks | IDENTICAL | — |
| `.trellis/scripts/task.py` | DIFFERS | Current adds degraded active task imports and fallback in `cmd_start` |
| `.trellis/scripts/add_session.py` | DIFFERS | Current adds `get_session_auto_commit` check |
| `.trellis/scripts/get_context.py` | IDENTICAL | — |
| `.trellis/scripts/common/active_task.py` | DIFFERS (major) | Current adds ~130 lines: degraded active task file, resolve/get/set/clear functions, modified resolve_active_task/set_active_task/clear_active_task/delete_runtime_task_pointers |
| `.trellis/scripts/common/__init__.py` | DIFFERS | Current removes `FILE_CURRENT_TASK` export |
| `.trellis/scripts/common/paths.py` | DIFFERS | Current removes `FILE_CURRENT_TASK = ".current-task"` constant |
| `.trellis/scripts/common/safe_commit.py` | DIFFERS | Current: only adds current active task path (not all), adds `include_removals` param, adds `_path_is_tracked()` helper, adds source_dir existence guard |
| `.trellis/scripts/common/task_store.py` | DIFFERS | Current: adds `get_session_auto_commit` check, archive returns True/False, uses `include_removals=True`, adds source_dir existence guard |

### .new Files Verification

ALL `.new` files match the reference 0.5.17 project exactly. This means applying any `.new` file would REVERT the corresponding current file to baseline 0.5.17, UNDOING local enhancements:

| .new File | Matches Reference? |
|---|---|
| `.trellis/workflow.md.new` | YES — reverts stale status additions |
| `.claude/hooks/inject-workflow-state.py.new` | YES — reverts stale/degraded handling |
| `.codex/hooks/inject-workflow-state.py.new` | YES — reverts stale/degraded handling |
| `.qoder/hooks/inject-workflow-state.py.new` | YES — reverts stale/degraded handling |
| `.opencode/plugins/inject-workflow-state.js.new` | YES — reverts stale/degraded handling |
| `.opencode/lib/trellis-context.js.new` | YES — reverts degraded fallback |
| `.claude/agents/trellis-research.md.new` | YES — reverts enriched MCP tools |
| `.codex/agents/trellis-research.toml.new` | YES — reverts carrier comment + enriched MCP |
| `.codex/agents/trellis-implement.toml.new` | YES — reverts carrier comment |
| `.codex/agents/trellis-check.toml.new` | YES — reverts carrier comment |
| `.qoder/agents/trellis-research.md.new` | YES — reverts enriched MCP |
| `.opencode/agents/trellis-research.md.new` | YES — reverts enriched MCP |
| `.kiro/agents/trellis-research.json.new` | YES — reverts to reference (but reference has no Kiro at all) |
| `.trellis/scripts/task.py.new` | YES — reverts degraded fallback |
| `.trellis/scripts/add_session.py.new` | YES — reverts auto_commit check |
| `.trellis/scripts/common/active_task.py.new` | YES — reverts degraded active task system |
| `.trellis/scripts/common/__init__.py.new` | YES — reverts FILE_CURRENT_TASK export |
| `.trellis/scripts/common/paths.py.new` | YES — reverts FILE_CURRENT_TASK constant |
| `.trellis/.gitignore.new` | YES — reverts to include `.current-task` line |
| `.claude/settings.json.new` | (not present) |
| `.codex/config.toml.new` | YES — reverts inline-mode comments |
| `.codex/hooks.json.new` | (not present, already identical) |
| `.trellis/scripts/common/safe_commit.py.new` | YES — reverts to baseline |
| `.trellis/scripts/common/task_store.py.new` | YES — reverts to baseline |

### Local Enhancement Categories

The current project has four categories of local enhancements over reference 0.5.17:

**A. Degraded Active-Task Fallback** (cohesive feature)
- New `degraded-active-task.json` mechanism in `common/active_task.py`
- Stale status support in `workflow.md` (`[workflow-state:stale]` block)
- Stale/degraded display logic in all inject-workflow-state hooks (Python + JS)
- Degraded fallback resolution in `trellis-context.js`
- `task.py start` falls back to degraded mode instead of failing
- Removal of `.current-task` file concept (moved to degraded JSON)
- Modified `safe_commit.py` and `task_store.py` for safer git operations

**B. Enriched Research Agents**
- All platform research agent definitions (Claude, Codex, Qoder, OpenCode, Kiro) enriched with:
  - MCP tool routing table (ace, exa, Context7, deepwiki, grok-search)
  - 3-step task resolution workflow
  - Additional tool permissions

**C. Inline-Mode Guard Comments** (Codex-specific)
- Carrier comment prefix on Codex agent definitions (implement, check, research)
- Inline-mode rule comments in `.codex/config.toml`
- Explains that agents should not be manually spawned in inline dispatch mode

**D. Project-Specific Additions** (not in reference at all)
- `.trellis/library-lock.yaml` — library asset lock file
- `.trellis/scripts/write-library-lock.py`, `assemble-init-set.py`, `apply-library-sync.py`, `analyze-library-pull.py`, `diff-library-assets.py`, `sync-library-assets.py`, `verify-upstream-contribution.py`, `propose-library-sync.py` — library sync scripts
- `.trellis/scripts/common/registry.py`, `worktree.py` — utility modules
- `.trellis/scripts/common/tests/` — test directory
- `.trellis/scripts/multi_agent/`, `validation/`, `workflow/` — additional script directories
- `.claude/hooks/statusline.py` — status line hook
- `.claude/settings.local.json` — local settings override
- `.claude/skills/workflow-audit/` — workflow audit skill (with tests/ and references/)
- `.claude/skills/workflow-capability-audit/` — capability audit skill
- `.kiro/` — entire Kiro platform directory (agents, hooks, skills)
- `.qoder/skills/record-session/` — session recording skill
- `.qoder/skills/trellis-finish-work/` — finish work skill
- `.opencode/bun.lock`, `.gitignore`, `package-lock.json` — OpenCode artifacts
- `.trellis/docs/DRIFT-MIGRATION-PLAN.md` — migration plan document
- `.trellis/.backup-*` directories (14+) — backup directories from updates

### Code Patterns

**Stale/degraded breadcrumb pattern** (in all inject-workflow-state hooks):
```python
# Current project adds this in build_breadcrumb():
display_status = status
if "stale" in templates and (
    status == "stale" or status.startswith("stale_")
    or lookup_key == "stale" or lookup_key.startswith("stale_")
    or lookup_key.startswith("stale-")
):
    lookup_key = "stale"
    display_status = "stale"
elif source == "degraded":
    display_status = f"{display_status} · degraded"
```
Reference has none of this — just uses `status` directly for both lookup and display.

**Degraded active task resolution** (in `common/active_task.py`):
- Current project adds `FILE_DEGRADED_ACTIVE_TASK = "degraded-active-task.json"`
- `_degraded_active_task_path()`, `_resolve_degraded_active_task()`, `get_degraded_active_task()`, `_same_task_reference()`, `clear_degraded_active_task()`, `set_degraded_active_task()`
- `resolve_active_task()` now consults degraded fallback when no context key found
- `set_active_task()` clears degraded fallback when session pointer is authoritative
- `clear_active_task()` also clears degraded fallback
- Reference has none of these functions or the degraded file concept.

**Carrier comment pattern** (Codex agent definitions):
```toml
# This agent definition is a carrier for explicit delegated/non-inline Codex
# paths. When `.trellis/config.yaml` keeps `codex.dispatch_mode = "inline"`,
# the main Codex session must not manually spawn this agent ad hoc.
```

### Related Specs

- `.trellis/spec/cli/backend/workflow-state-contract.md` — referenced by reference workflow.md (current references parser implementations instead)

## Caveats / Not Found

- The comparison did not deeply inspect the `.trellis/scripts/multi_agent/`, `validation/`, `workflow/` directories or the `.trellis/docs/DRIFT-MIGRATION-PLAN.md` file content.
- The `.trellis/.backup-*` directories were not inspected in detail.
- The library sync scripts were not inspected in detail.
- The `.kiro/` platform directory exists only in current project; its `.new` file would revert to reference but reference has no Kiro support at all — this needs special handling.
- The `spec-bootstarp` skill name (typo of "bootstrap") exists in both projects identically.
- The `.current-task` file removal from `.gitignore` in current project correlates with the degraded active task system replacing the `.current-task` file mechanism entirely.

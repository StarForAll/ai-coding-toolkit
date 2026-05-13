# Research: trellis live runtime upgrade

- Query: Analyze the current live Trellis runtime used in this repository and judge whether the current minor-version upgrade residue in the working tree is correct, incomplete, or regressive. Include `.new` handling guidance.
- Scope: internal
- Date: 2026-05-13

## Findings

### Files Found

| File Path | Description |
| --- | --- |
| `.trellis/workflow.md` | Live workflow contract, phase numbering, per-turn breadcrumb source-of-truth. |
| `.trellis/scripts/common/active_task.py` | Session-scoped active-task resolver and single-session fallback logic. |
| `.trellis/scripts/task.py` | `start/current/finish` task lifecycle entrypoints. |
| `.trellis/scripts/common/task_store.py` | `create/archive` task storage, JSONL seeding, archive auto-commit path. |
| `.trellis/scripts/common/safe_commit.py` | Narrow git staging rules for archive/journal auto-commit. |
| `.trellis/scripts/common/session_context.py` | SessionStart context builder and git/package context collection. |
| `.codex/hooks/inject-workflow-state.py` | Codex live per-turn breadcrumb injection and `dispatch_mode` handling. |
| `.codex/hooks.json` | Codex live hook wiring. |
| `.codex/config.toml` | Codex live project config surface. |
| `.claude/settings.json` | Claude live hook wiring plus repo-local statusline overlay. |
| `.qoder/settings.json` | Qoder live hook wiring. |
| `.opencode/lib/trellis-context.js` | OpenCode active-task/context resolver. |
| `.opencode/plugins/inject-subagent-context.js` | OpenCode sub-agent context injection and bash session bridging. |
| `.opencode/plugins/session-start.js` | OpenCode SessionStart-equivalent injection. |
| `.opencode/plugins/inject-workflow-state.js` | OpenCode per-turn breadcrumb injection. |
| `.claude/agents/trellis-research.md` | Claude research-agent live body and tool list. |
| `.qoder/agents/trellis-research.md` | Qoder research-agent live body and tool list. |
| `.opencode/agents/trellis-research.md` | OpenCode research-agent live body and permission set. |
| `.codex/agents/trellis-research.toml` | Codex research-agent live body. |
| `.trellis/spec/agents/index.md` | Repo-local live agent contract, including research capability expectations. |
| `.trellis/spec/platforms/codex-workflow-behavior.md` | Repo-local Codex inline-mode contract. |
| `.agents/skills/trellis-meta/references/customize-local/change-workflow.md` | Live meta guidance that now shows resume-step drift. |
| `.agents/skills/trellis-finish-work/SKILL.md` | Live finish-work wording. |

### Runtime Mechanism Map

1. Active task state is session-scoped, not stored in a global current-task file. The runtime resolves a context key from hook input, env vars, transcript paths, or Cursor shell tickets, then reads `.trellis/.runtime/sessions/<context>.json` (`.trellis/scripts/common/active_task.py:48-78`, `.trellis/scripts/common/active_task.py:380-415`, `.trellis/scripts/common/active_task.py:468-519`).
2. `task.py create` seeds `implement.jsonl` and `check.jsonl` whenever an agent-capable platform directory exists, and tries to auto-point the new task at the current session (`.trellis/scripts/common/task_store.py:90-138`, `.trellis/scripts/common/task_store.py:236-246`). `task.py start` flips `planning -> in_progress` even in degraded mode when no session identity is available (`.trellis/scripts/task.py:70-140`).
3. Per-turn workflow guidance comes from `[workflow-state:*]` blocks embedded in `.trellis/workflow.md`; hook code is parser-only and does not own fallback workflow text (`.trellis/workflow.md:99-139`, `.trellis/workflow.md:152-235`, `.codex/hooks/inject-workflow-state.py:185-360`).
4. The live workflow numbering in this repo is `Phase 1.3 = Configure context`, `Phase 1.4 = Activate task`, `Phase 3.4 = Commit changes`, `Phase 3.5 = Wrap-up reminder` (`.trellis/workflow.md:158-221`). The `in_progress` breadcrumb explicitly says the main flow is `trellis-implement -> trellis-check -> trellis-update-spec -> commit -> finish-work` and that every sub-agent dispatch prompt must start with `Active task: ...` (`.trellis/workflow.md:197-213`).
5. Codex is now running a lightweight live model: `.codex/hooks.json` wires only `UserPromptSubmit -> inject-workflow-state.py`, while `inject-workflow-state.py` emits a Codex bootstrap notice plus `<codex-mode>` derived from `.trellis/config.yaml` (`.codex/hooks.json:1-15`, `.codex/hooks/inject-workflow-state.py:56-77`, `.codex/hooks/inject-workflow-state.py:230-345`). The separate `session-start.py` file still exists, but it is not wired in this repo's live Codex hook config.
6. Claude and Qoder still use SessionStart hooks plus per-turn breadcrumb hooks, with upstream 0.5.14 timeout values now at `30s` for SessionStart and `15s` for per-turn breadcrumb (`.claude/settings.json:5-76`, `.qoder/settings.json:1-46`).
7. OpenCode's live runtime now mirrors the Python active-task fallback model and adds explicit defenses against sub-agent context pollution: it skips SessionStart/breadcrumb reinjection inside Trellis sub-agent turns, resolves task context by exact session -> `Active task:` prompt hint -> single-session fallback, and injects `TRELLIS_CONTEXT_ID` into bash commands with Windows shell detection (`.opencode/lib/trellis-context.js:66-79`, `.opencode/lib/trellis-context.js:132-200`, `.opencode/plugins/session-start.js:38-99`, `.opencode/plugins/inject-workflow-state.js:104-160`, `.opencode/plugins/inject-subagent-context.js:17-26`, `.opencode/plugins/inject-subagent-context.js:297-315`, `.opencode/plugins/inject-subagent-context.js:398-457`).
8. Archive/record close-out has moved to the Trellis-native path. `safe_commit.py` now refuses force-add and narrows archive staging scope; `task_store.py` explicitly stages source-side deletions with `git rm --cached`; finish-work guidance points at `task.py archive` plus `add_session.py` (`.trellis/scripts/common/safe_commit.py:114-202`, `.trellis/scripts/common/task_store.py:338-469`, `.agents/skills/trellis-finish-work/SKILL.md:32-69`).

### Current Working-Tree Upgrade Review

#### 1. Changes that look correct and mostly complete

- Upstream 0.5.14 runtime adoption is real, not imagined. `trellis --version` returned `0.5.14`, and a fresh baseline generated with `trellis init --codex --claude --opencode --qoder -u xzc -y` at `/tmp/trellis-live-runtime-sxc8p7` matched the current working-tree copies for:
  - `.codex/hooks.json`
  - `.codex/config.toml`
  - `.codex/agents/trellis-{implement,check,research}.toml`
  - `.qoder/settings.json`
  - `.opencode/lib/trellis-context.js`
  - `.opencode/plugins/{inject-subagent-context,inject-workflow-state,session-start}.js`
  - `.trellis/scripts/common/{safe_commit,task_store,session_context}.py`
- The timeout bumps in `.claude/settings.json`, `.qoder/settings.json`, and `.codex/hooks.json` are therefore upstream-aligned rather than accidental local drift (`.claude/settings.json:5-76`, `.qoder/settings.json:1-46`, `.codex/hooks.json:1-15`).
- The OpenCode runtime changes are especially important and appear correct: they close real context-injection gaps instead of changing repo policy. The new code explicitly preserves sub-agent isolation and carries `Active task:` fallback logic that the Python workflow contract already requires (`.opencode/plugins/inject-subagent-context.js:398-457`).
- The archive auto-commit changes in `safe_commit.py` and `task_store.py` also look correct. They reduce archive commit scope and fix the source-side deletion staging problem without reintroducing forbidden `git add -f` behavior (`.trellis/scripts/common/safe_commit.py:121-202`, `.trellis/scripts/common/task_store.py:395-469`).

#### 2. Changes that preserve a repo-local overlay correctly

- `.claude/settings.json` still carries a repo-local `statusLine` command that is not present in the fresh 0.5.14 baseline. This is the only baseline/runtime difference I found in the main live hook-config surfaces, and it looks intentionally preserved rather than stale (`.claude/settings.json:72-76`).

#### 3. Regressions or incomplete residue still present

- The strongest regression is the research-agent carrier simplification. Current live Claude/Qoder/OpenCode research agents now expose only Exa plus chrome-devtools and instruct the agent to rely solely on `task.py current --source` (`.claude/agents/trellis-research.md:1-60`, `.qoder/agents/trellis-research.md:1-60`, `.opencode/agents/trellis-research.md:1-68`, `.codex/agents/trellis-research.toml:1-30`). That conflicts with the repo-local live contract in `.trellis/spec/agents/index.md`, which still says Claude/Qoder/OpenCode research agents were capability-enhanced on 2026-05-06 to include `ace.search_context`, Context7, deepwiki, grok-search, Exa advanced fetch, and prompt-or-`task.py current` task resolution (`.trellis/spec/agents/index.md:279-344`).
- The same research-agent simplification also removed the explicit `Active task:` dispatch-prompt fallback from the research-agent bodies. That is dangerous in this repo because:
  - the workflow contract says **all** `trellis-implement / trellis-check / trellis-research` dispatch prompts must start with `Active task: ...` (`.trellis/workflow.md:197-202`);
  - my shell invocation of `python3 ./.trellis/scripts/task.py current --source` returned `Current task: (none)` in this session because no session identity was inherited;
  - the current runtime has `12` session files under `.trellis/.runtime/sessions/`, so single-session fallback is unavailable right now and class-2 platforms cannot safely guess.
  Together this means the removed prompt-hint fallback is not a theoretical nicety; it is still needed for Codex/Qoder and for hook-failure fallback on class-1 platforms.
- The `change-workflow.md` route-table edit is incomplete across all five live copies (`.agents`, `.claude`, `.kiro`, `.opencode`, `.qoder`). The row for `in_progress + check passed` now ends at `Phase 3.1 (verify quality + spec update)` instead of carrying the user toward the required `Phase 3.4` commit and `Phase 3.5` wrap-up (`.agents/skills/trellis-meta/references/customize-local/change-workflow.md:46-60`). That contradicts the actual workflow contract, where `Phase 3.4` commit is mandatory before finish-work (`.trellis/workflow.md:197-213`, `.trellis/workflow.md:216-235`).
- `.trellis/workflow.md` still points twice at a missing spec file, `.trellis/spec/cli/backend/workflow-state-contract.md` (`.trellis/workflow.md:139`; also referenced again later in the same file). This does not break runtime parsing, but it is live contract documentation drift and makes the breadcrumb contract harder to audit.

### `.new` Handling Strategy

- Current on-disk `.new` count is `0`. There are no unresolved `.new` files left in the live runtime tree. For the current working tree, `.new` handling is therefore a historical classification problem, not an active filesystem cleanup problem.
- For the file groups implicated by the current diff, the correct treatment is:
  - Replace / already settled: upstream 0.5.14 baseline runtime copies that now match fresh init output. This includes the Codex hook/config carrier, Qoder settings timeouts, OpenCode runtime helpers/plugins, and Trellis core script changes listed above.
  - Merge / keep local overlay: `.claude/settings.json` because the repo-local `statusLine` survives baseline adoption and does not conflict with 0.5.14 hook wiring.
  - Merge selectively, do **not** wholesale replace: all `trellis-research` carrier files. The current baseline simplification should not be treated as the final answer for this repo because it drops repo-local capability enhancements and the required `Active task:` fallback contract.
  - Merge selectively, current state incomplete: the five `change-workflow.md` copies. Their phase-number wording is no longer wrong, but the new row is still too short and should be repaired to include the required commit/wrap-up path.

### Version / Baseline References

- Local Trellis CLI version used for comparison: `trellis --version -> 0.5.14`
- Fresh comparison baseline created on 2026-05-13: `/tmp/trellis-live-runtime-sxc8p7`
- Baseline command: `trellis init --codex --claude --opencode --qoder -u xzc -y`

### Related Specs

- `.trellis/spec/agents/index.md` — live platform agent contract and research-agent capability notes.
- `.trellis/spec/platforms/codex-workflow-behavior.md` — repo-local rule that inline Codex sessions should not manually spawn sub-agents.
- `.trellis/spec/docs/index.md` — repo-local doc maintenance boundary.
- `.trellis/spec/scripts/index.md` — repo-local script maintenance boundary.

## Caveats / Not Found

- Confidence is high for the baseline-adoption findings because almost every touched runtime file now byte-matches a fresh 0.5.14 init output. Confidence is medium-high, not absolute, for the research-agent regression call because upstream 0.5.14 itself now ships the simplified carriers; the reason I still classify it as a regression is that this repository's own live spec, archived upgrade decisions, and current task constraints all continue to require the richer research contract.
- I did not modify or validate target-project workflow product assets under `docs/workflows/新项目开发工作流/` except when needed to separate them from the live runtime boundary.
- The missing `workflow-state-contract.md` path may reflect a moved or never-checked-in spec rather than a recent runtime regression; I only confirmed that the reference is broken in the current tree.

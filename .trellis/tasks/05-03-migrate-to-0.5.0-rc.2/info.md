# Trellis Root Runtime Migration To 0.5.0-rc.2

## Why This Document Lives Here

This repository is currently acting as a **Trellis-managed root project**, not as a workflow target fixture.
The task-specific implementation and migration document therefore belongs under the active task directory:

- `.trellis/tasks/05-03-migrate-to-0.5.0-rc.2/`

The previous plan was incorrectly written to a repo-global planning path under:

- `docs/superpowers/plans/`

That happened because a generic planning skill defaulted to `docs/superpowers/plans/...`, while this project's task workflow uses `.trellis/tasks/<task>/` as the task-local documentation root.

## Root Cause Analysis

### Direct cause

I applied the generic `writing-plans` skill mechanically. Its default instruction says:

- save plans to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

That default is not aligned with this repository's Trellis task model.

### Why that default was wrong in this repo

The current project already defines a task-local documentation model:

- task directories live under `.trellis/tasks/<task>/`
- task-local docs include `prd.md`
- optional task-local technical/supporting docs include `info.md`
- task-local execution context includes `implement.jsonl`, `check.jsonl`, and `research/`

This means the correct place for a task-specific migration/implementation document is the active task directory, not a repo-global planning folder.

### Priority mistake

The real mistake was not the content of the plan, but instruction prioritization:

1. I should have prioritized the **project-local Trellis task system**
2. Then chosen a task-local doc path under `.trellis/tasks/05-03-migrate-to-0.5.0-rc.2/`
3. Instead, I followed the generic external planning skill's default storage location

## Correction Decision

This plan is normalized into the active task's `info.md`.

Reason:

- `info.md` is already a recognized task-local companion document in this repo's Trellis model
- agent/runtime flows are expected to read `prd.md` and `info.md`
- keeping the migration plan here makes later implementation and checking easier

The old file under `docs/superpowers/plans/` should be treated as a misplaced draft copy and removed after this corrected task-local version is accepted.

---

## Implementation Plan

**Goal:** Converge this repository root's live Trellis runtime (`.trellis/`, `.claude/`, `.codex/`, `.opencode/`, `.agents/skills/`, `AGENTS.md`) onto `0.5.0-rc.2` semantics without regressing the repo's project-specific metadata-closure behavior.

**Architecture:** Replace the old `0.4.x` runtime contract (`.current-task`, `current_phase`, `next_action`, `multi_agent`, `ralph-loop`, `check-cross-layer`, standalone `record-session`) with the `0.5.0-rc.2` contract (session-scoped active task state under `.trellis/.runtime/`, `trellis-*` subagents, `workflow-state` per-turn breadcrumb injection, `finish-work` close-out flow). Preserve this repo's useful local customizations only where they still fit the new contract: `record-session-helper.py`, metadata-closure guards, and meta-project validation rules.

**Tech Stack:** Python runtime scripts/hooks, JSON/TOML settings, Markdown command/skill docs, JavaScript OpenCode plugins.

## Scope Boundary

Included:

- `.trellis/` runtime scripts and root workflow
- `.claude/`, `.codex/`, `.opencode/` live runtime files
- `.agents/skills/` live skill entrypoints
- root `AGENTS.md`
- removal of stale `.iflow/` runtime residue

Explicitly excluded:

- `docs/workflows/新项目开发工作流/` product-source compatibility work
- rewriting archived task artifacts under `.trellis/tasks/archive/`

## File Responsibility Map

- `.trellis/scripts/common/active_task.py`: session-scoped active task source of truth
- `.trellis/scripts/common/workflow_phase.py`: `workflow.md` Phase Index / step extraction
- `.trellis/scripts/common/git_context.py`: exposes `get_context.py --mode phase`
- `.trellis/scripts/task.py`: task CLI entrypoint, active-task UX
- `.trellis/scripts/common/task_store.py`: task creation, archive behavior, JSONL seeding
- `.trellis/scripts/common/types.py`: canonical task JSON schema
- `.trellis/workflow.md`: root workflow authority for current project runtime
- `AGENTS.md`: root project instructions + Trellis managed block
- `.claude/settings.json`, `.claude/hooks/*.py`: Claude runtime injection pipeline
- `.codex/hooks.json`, `.codex/hooks/*.py`, `.codex/config.toml`: Codex runtime injection pipeline
- `.opencode/plugins/*.js`, `.opencode/lib/*.js`, `.opencode/package.json`: OpenCode runtime injection pipeline
- `.agents/skills/trellis-*.md`, `.claude/agents/trellis-*.md`, `.opencode/agents/trellis-*.md`, `.codex/agents/trellis-*.toml`: live `trellis-*` skill/agent surfaces
- `.claude/commands/trellis/*.md`, `.opencode/commands/trellis/*.md`, `.agents/skills/record-session/SKILL.md`: close-out and legacy-entry docs

## Key Decisions Locked In

1. `.iflow/` is removed completely from the root runtime surface.
2. `record-session-helper.py` stays, but no longer as the primary public close-out entry.
3. Old `current_phase` / `next_action` / `multi_agent` / `ralph-loop` semantics are not preserved.
4. OpenCode adopts the new `.opencode/plugins/` runtime shape, but does not blindly downgrade `@opencode-ai/plugin` from `1.4.10` to `1.1.40` unless compatibility testing proves it necessary.
5. Project-specific pre-commit rigor from old `finish-work` is preserved by moving it into `trellis-check` / check-agent surfaces, not by reviving old `finish-work` semantics.

## Repair Batches

### Batch 1: `.trellis/` runtime convergence

- Merge `get_context.py --mode phase` support into `.trellis/scripts/common/git_context.py`
- Remove `current_phase` / `next_action` from task schema
- Switch `task.py` to session-scoped active-task APIs
- Seed `implement.jsonl` / `check.jsonl` only for subagent-capable platforms
- Add `.trellis/.runtime/` to `.trellis/.gitignore`

### Batch 2: root workflow + AGENTS convergence

- Merge `[workflow-state:*]` blocks into `.trellis/workflow.md`
- Remove old runtime references to `check-cross-layer`, `multi_agent`, standalone mainline `record-session`
- Add Trellis managed block to root `AGENTS.md`
- Repair `.agents/skills/trellis-continue/SKILL.md`

### Batch 3: Claude runtime convergence

- Merge `.claude/settings.json.new`
- Merge `.claude/hooks/session-start.py.new`
- Merge `.claude/hooks/inject-subagent-context.py.new`
- Keep `.claude/hooks/inject-workflow-state.py`
- Remove `ralph-loop` wiring

### Batch 4: Codex runtime convergence

- Merge `.codex/hooks.json.new`
- Merge `.codex/hooks/session-start.py.new`
- Materialize `.codex/config.toml` from `.new` if missing

### Batch 5: OpenCode runtime convergence

- Merge new active-task/session logic into `.opencode/lib/trellis-context.js`
- Standardize on `.opencode/plugins/`
- Do not blindly downgrade `@opencode-ai/plugin`
- Retire `.opencode/plugin/*` only after verification

### Batch 6: skills / agents / close-out semantics

- Keep renamed `trellis-*` surfaces
- Move meta-project validation rigor into `trellis-check`
- Rewrite platform `finish-work` docs to post-commit close-out semantics
- Keep `record-session-helper.py`, but demote `record-session` to legacy/manual fallback if retained

### Batch 7: `.iflow` removal

- Delete `.iflow/settings.json`
- Remove root-runtime `.iflow` references from root docs/spec indexes

### Batch 8: verification

- `py_compile` all affected Python runtime files
- `node --check` OpenCode JS runtime files
- grep sweep for:
  - `current_phase`
  - `next_action`
  - `multi_agent`
  - `ralph-loop`
  - `check-cross-layer`
  - `/trellis:record-session`
  - `.iflow/`
- smoke-test session-scoped task flow with `TRELLIS_CONTEXT_ID=...`

## Acceptance Criteria

- `python3 ./.trellis/scripts/get_context.py --mode phase` works
- `task.py current --source` works with session-scoped state
- no live Claude runtime references to `ralph-loop`
- Codex has `UserPromptSubmit -> inject-workflow-state.py`
- OpenCode runtime no longer depends on old plugin fallback logic
- root main-flow docs no longer advertise `check-cross-layer` or standalone `/trellis:record-session`
- `.iflow/settings.json` is gone

## `.new` File Handling Matrix

Per the current `0.5.0-rc.2` upgrade task, `.new` files are **candidate updated templates**, not long-lived files.
Each one must end in one of four states:

- **Adopt `.new`**: replace the live file with `.new`, then delete `.new`
- **Merge (new-biased)**: merge the required `0.5` contract from `.new` into the live file, then delete `.new`
- **Keep current, drop `.new`**: current file stays; `.new` is discarded
- **Update current file from `.new`**: when the base file already exists and `.new` is mainly documentation/comments, update in place and delete `.new`

### A. Adopt `.new`

These files define the new runtime contract directly. The old local variant is either obsolete or explicitly blocked by this task's locked decisions.

| `.new` file | Base file | Strategy | Why |
| --- | --- | --- | --- |
| `.claude/settings.json.new` | `.claude/settings.json` | Adopt `.new` | Required to wire `UserPromptSubmit -> inject-workflow-state.py` and remove `ralph-loop` wiring |
| `.claude/hooks/session-start.py.new` | `.claude/hooks/session-start.py` | Adopt `.new` | Session-start contract must switch to session-scoped active task + workflow overview injection |
| `.claude/hooks/inject-subagent-context.py.new` | `.claude/hooks/inject-subagent-context.py` | Adopt `.new` | Old file is tied to `implement/check/debug/research` and `current_phase`; task locks those old semantics out |
| `.codex/hooks.json.new` | `.codex/hooks.json` | Adopt `.new` | Required to add `UserPromptSubmit -> inject-workflow-state.py` |
| `.codex/hooks/session-start.py.new` | `.codex/hooks/session-start.py` | Adopt `.new` | Must move to `trellis-*` / active-task runtime semantics |
| `.trellis/.gitignore.new` | `.trellis/.gitignore` | Adopt `.new` | Must ignore `.runtime/` once session-scoped task state is live |
| `.trellis/scripts/common/__init__.py.new` | `.trellis/scripts/common/__init__.py` | Adopt `.new` | Exposes `active_task` APIs used by the new runtime |
| `.trellis/scripts/common/git_context.py.new` | `.trellis/scripts/common/git_context.py` | Adopt `.new` | Restores `get_context.py --mode phase` required by current task flow |
| `.trellis/scripts/common/types.py.new` | `.trellis/scripts/common/types.py` | Adopt `.new` | Removes old `current_phase / next_action` task schema |
| `.trellis/scripts/common/task_context.py.new` | `.trellis/scripts/common/task_context.py` | Adopt `.new` | Removes deprecated `init-context` contract |
| `.trellis/scripts/common/session_context.py.new` | `.trellis/scripts/common/session_context.py` | Adopt `.new` | Adds active-task `source/contextKey` reporting that matches new runtime |
| `.trellis/scripts/common/tasks.py.new` | `.trellis/scripts/common/tasks.py` | Adopt `.new` | Fixes archived-child progress accounting for the new archive flow |

### B. Merge (new-biased)

These files need the `0.5` contract from `.new`, but the current file may still contain repo-specific behavior worth preserving if it remains compatible.

| `.new` file | Base file | Strategy | Merge rule |
| --- | --- | --- | --- |
| `.claude/commands/trellis/finish-work.md.new` | `.claude/commands/trellis/finish-work.md` | Merge (new-biased) | New close-out flow wins; preserve only repo-specific guidance that still fits post-commit `finish-work` |
| `.opencode/commands/trellis/finish-work.md.new` | `.opencode/commands/trellis/finish-work.md` | Merge (new-biased) | Same as Claude |
| `.opencode/lib/trellis-context.js.new` | `.opencode/lib/trellis-context.js` | Merge (new-biased) | New session/runtime model wins; preserve only valid helper behavior that still applies |
| `.trellis/scripts/common/cli_adapter.py.new` | `.trellis/scripts/common/cli_adapter.py` | Merge (new-biased) | Keep `trellis-` skill path updates; review platform additions case-by-case |
| `.trellis/scripts/common/paths.py.new` | `.trellis/scripts/common/paths.py` | Merge (new-biased) | Move path APIs to `active_task`-aware wrappers without breaking existing callers |
| `.trellis/scripts/common/task_store.py.new` | `.trellis/scripts/common/task_store.py` | Merge (new-biased) | Remove old phase fields, adopt JSONL seed + archive/session cleanup, preserve any repo-safe archive behavior |
| `.trellis/scripts/task.py.new` | `.trellis/scripts/task.py` | Merge (new-biased) | `0.5` CLI contract wins; preserve only clearly valid repo-specific UX |
| `.trellis/workflow.md.new` | `.trellis/workflow.md` | Merge (new-biased) | Add `[workflow-state:*]` blocks and remove old runtime guidance without blindly replacing the full file |
| `AGENTS.md.new` | `AGENTS.md` | Merge (new-biased) | Add Trellis managed block; keep project-specific content outside the managed block |

### C. Keep current, drop `.new`

These `.new` files should not be accepted as-is under the current migration task rules.

| `.new` file | Base file | Strategy | Why |
| --- | --- | --- | --- |
| `.opencode/package.json.new` | `.opencode/package.json` | Keep current, drop `.new` | `.new` downgrades `@opencode-ai/plugin` from `1.4.10` to `1.1.40`; current task explicitly forbids blind downgrade |
| `.trellis/config.yaml.new` | `.trellis/config.yaml` | Keep current, drop `.new` | The delta is non-blocking commentary/example text, not a required runtime contract change for this migration |
| `.trellis/scripts/common/config.py.new` | `.trellis/scripts/common/config.py` | Keep current, drop `.new` | The parser refactor is not required to complete the root runtime migration and current config behavior remains valid |

### D. Update current file from `.new`

These are safe in-place updates where the current file already exists and `.new` mainly adds comments/documentation rather than a conflicting runtime fork.

| `.new` file | Base file | Strategy | Why |
| --- | --- | --- | --- |
| `.codex/config.toml.new` | `.codex/config.toml` | Update current file from `.new` | Base file already exists; `.new` only adds explanatory hook comments, not a conflicting config model |

## Additional Files / Surfaces That Were Previously Under-Specified

The `.new` matrix is not enough by itself. The following concrete files or file groups also need explicit handling.

### 1. New runtime files that are **not** `.new`

These must be incorporated into the migration scope, not left as accidental untracked files:

- `.trellis/scripts/common/active_task.py`
- `.trellis/scripts/common/workflow_phase.py`
- `.claude/hooks/inject-workflow-state.py`
- `.codex/hooks/inject-workflow-state.py`
- `.opencode/plugins/inject-subagent-context.js`
- `.opencode/plugins/session-start.js`
- `.opencode/plugins/inject-workflow-state.js`
- `.opencode/lib/session-utils.js`
- `.claude/commands/trellis/continue.md`
- `.opencode/commands/trellis/continue.md`

Handling:

- treat them as **required new runtime files**
- verify they are the intended active implementation
- include them in Batch 2/3/4/5, not as optional leftovers

### 2. Old files that should be explicitly deleted once the new runtime is live

These are not `.new`, but their deletion is part of the same migration decision surface:

- `.claude/hooks/ralph-loop.py`
- `.trellis/scripts/common/phase.py`
- `.trellis/scripts/create_bootstrap.py`
- `.trellis/scripts/multi_agent/**`
- `.trellis/worktree.yaml`
- `.opencode/plugin/inject-subagent-context.js`
- `.opencode/plugin/session-start.js`
- `.iflow/settings.json`
- remaining `.iflow/**` runtime residue

Handling:

- do **not** preserve these for compatibility
- delete only after the replacement path has been verified

### 3. Runtime docs that still advertise removed behavior

These are concrete files whose content must be changed alongside the runtime merge:

- `AGENTS.md`
- `.trellis/workflow.md`
- `.claude/commands/trellis/finish-work.md`
- `.opencode/commands/trellis/finish-work.md`
- `.claude/commands/trellis/record-session.md`
- `.opencode/commands/trellis/record-session.md`
- `.agents/skills/record-session/SKILL.md`

Handling:

- remove mainline references to `/trellis:check-cross-layer`
- remove mainline references to standalone `/trellis:record-session`
- keep `record-session-helper.py` only as internal helper / legacy-manual fallback if needed

### 4. New/renamed live surfaces already produced by migrate that need acceptance, not re-analysis

These are not `.new`, but they are part of the same migration output and should be treated as adopted live surfaces unless a specific incompatibility is found:

- `.agents/skills/trellis-before-dev/`
- `.agents/skills/trellis-brainstorm/`
- `.agents/skills/trellis-break-loop/`
- `.agents/skills/trellis-check/`
- `.agents/skills/trellis-continue/`
- `.agents/skills/trellis-finish-work/`
- `.agents/skills/trellis-meta/`
- `.agents/skills/trellis-update-spec/`
- `.claude/agents/trellis-*.md`
- `.opencode/agents/trellis-*.md`
- `.codex/agents/trellis-*.toml`

Handling:

- treat them as the **new canonical live surfaces**
- adjust content if needed, but do not revert back to old non-prefixed names

### 5. `.backup` files produced by migration

Currently visible examples include:

- `.claude/agents/trellis-*.md.backup`
- `.opencode/agents/trellis-*.md.backup`
- `.codex/agents/trellis-*.toml.backup`
- `.agents/skills/trellis-*.backup`

Handling:

- keep temporarily while merge/verification is in progress
- once final runtime behavior is accepted and verified, remove them from the working tree unless the project explicitly wants to keep them as human-audit artifacts

## Expanded Verification Sweep

Beyond the original grep list, final verification should also sweep for:

- `.opencode/plugin/` old runtime references
- missing adoption of `.opencode/plugins/`
- presence of `.claude/hooks/inject-workflow-state.py` and `.codex/hooks/inject-workflow-state.py` in settings/hook configs
- stale `continue.md` / `record-session` / `finish-work` flow mismatches
- stray `.backup` and `.new` files after migration is complete

## Follow-up Cleanup

The misplaced repo-global draft copy has already been removed. This task-local
`info.md` is now the authoritative migration note for this task.

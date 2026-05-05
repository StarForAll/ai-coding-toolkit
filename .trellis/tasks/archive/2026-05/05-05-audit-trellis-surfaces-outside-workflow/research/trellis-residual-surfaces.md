# Research: trellis residual surfaces

- Query: 审计当前仓库中与 Trellis 相关、但不属于 `workflow-audit` / `workflow-capability-audit` / `docs/workflows/新项目开发工作流` 的残留面，重点判断 `.new`、backup、runtime 状态文件是否需要修正
- Scope: internal
- Date: 2026-05-05

## Findings

### Runtime mechanism surfaces

| File Path | Description |
| --- | --- |
| `.trellis/workflow.md` | Trellis 工作流源头，包含 Phase Index 和 `[workflow-state:*]` 段 |
| `.trellis/config.yaml` | 项目级 Trellis 配置 |
| `.trellis/scripts/common/active_task.py` | session-scoped active task 解析与持久化 |
| `.trellis/scripts/common/session_context.py` | SessionStart / get_context 共用上下文组装 |
| `.trellis/scripts/common/workflow_phase.py` | workflow Phase Index 与 step 片段抽取 |
| `.trellis/scripts/common/task_store.py` | task create/archive 与 JSONL seed、archive auto-commit |

### Code patterns

- Trellis 当前 active task 已明确是 **session-scoped runtime state**，状态文件位于 `.trellis/.runtime/sessions/`，不是旧式全局 current-task 文件模型。见 `.trellis/scripts/common/active_task.py:1`、`.trellis/scripts/common/active_task.py:108`、`.trellis/scripts/common/active_task.py:466`。
- Session context 输出会同时汇总当前任务、活跃任务、journal 和包级 git 信息。见 `.trellis/scripts/common/session_context.py:103`、`.trellis/scripts/common/session_context.py:152`。
- `workflow_phase.py` 当前会主动 strip `[workflow-state:*]` 块，说明 session-start 与 per-turn workflow-state 注入已分层。见 `.trellis/scripts/common/workflow_phase.py:62`。
- `task_store.py` 当前实现仍保留只读/受限 git 环境的恢复引导逻辑，并会在 `task.py create` 时为 agent-capable 平台 seed `implement.jsonl` / `check.jsonl`。见 `.trellis/scripts/common/task_store.py:43`、`.trellis/scripts/common/task_store.py:79`、`.trellis/scripts/common/task_store.py:114`。

### Residual surface inventory

#### 1. `.new` files

Current live repo no longer contains `.new` files under `.trellis/`.

- During this audit, the reviewed `.new` residue set included:
  - `.trellis/config.yaml.new`
  - `.trellis/scripts/add_session.py.new`
  - `.trellis/scripts/common/cli_adapter.py.new`
  - `.trellis/scripts/common/config.py.new`
  - `.trellis/scripts/common/task_context.py.new`
  - `.trellis/scripts/common/task_store.py.new`
  - `.trellis/scripts/task.py.new`
  - `.trellis/workflow.md.new`
- These files were ignored by `.trellis/.gitignore` (`*.new`), but they were candidate upgrade templates rather than harmless cache, so they required explicit disposition decisions.
- In the final on-disk state after this cleanup pass, the live `.new` count is `0`.

#### 2. Backup directories

Current `.trellis/.backup-*` directories:

- `.trellis/.backup-2026-05-04T11-53-46`

Older `.trellis/.backup-*` residue has already been cleaned. Current policy remains: retain only the latest backup directory.

#### 3. Scattered `*.backup`

Live platform / shared skill directories no longer contain `*.backup` files.

- Previously observed backup residue under `.claude/`, `.opencode/`, `.codex/`, `.agents/skills/`, `.kiro/`, and `.qoder/` has been deleted.
- Remaining `*.backup` files now exist only inside the retained `.trellis/.backup-2026-05-04T11-53-46/` snapshot and are intentionally preserved as part of that backup.

#### 4. Runtime state / recovery files

- `.trellis/.runtime/sessions/*` is active session state and should not be treated as code drift.
- `.trellis/.pending-record-session/` currently has no files and therefore is not a live problem surface.

### `.new` decision matrix (current repo contract)

The table below records the disposition decisions for the `.new` residue reviewed during this audit, even though the live `.new` files are now gone.

#### Drop `.new`

| File | Reason |
| --- | --- |
| `.trellis/config.yaml.new` | Diff is only comment/example expansion about polyrepo git packages; no current runtime contract gap |
| `.trellis/scripts/common/config.py.new` | Replaces imported YAML helper with inline parser refactor; not required for current 0.5 runtime |

#### Keep current live file; do NOT blindly merge `.new`

| File | Reason |
| --- | --- |
| `.trellis/workflow.md.new` | Introduces phase-number drift (`3.1` → `3.4`) and weakens current commit-confirmation contract |
| `.trellis/scripts/task.py.new` | Removes `archive-commit-only` recovery path and rewrites phase references from `1.2` to `1.3`; not safe without repo-specific review |
| `.trellis/scripts/common/task_store.py.new` | Removes read-only git failure recovery guidance now present in live file |
| `.trellis/scripts/add_session.py.new` | Removes record-session resume state / recovery guidance for restricted git environments |
| `.trellis/scripts/common/task_context.py.new` | Only phase-number wording / annotation changes; no need to replace live file |

#### Drop now under current repo contract

| File | Reason |
| --- | --- |
| `.trellis/scripts/common/cli_adapter.py.new` | Mixed proposal residue: reintroduces removed `.iflow` support, adds `.pi` behavior not present in the live adapter, and folds in unrelated detection changes. Current repo contract keeps the live `cli_adapter.py` as source of truth, so the `.new` file should be deleted rather than left pending. |

### `.iflow` and `cli_adapter.py.new`

- Archived migration records under `.trellis/tasks/archive/2026-05/05-03-migrate-to-0.5.0-rc.2/` explicitly classify `.iflow` as removed from the root runtime surface.
- The audit found only empty `.iflow/` directories plus `hooks/__pycache__/`; no live runtime files remained, so the root `.iflow/` residue was deleted.
- `cli_adapter.py.new` attempted to reintroduce explicit `iflow` support while the current root-runtime migration history says `.iflow` should stay removed.
- The same `.new` file also proposed `.pi` and shared-skills detection changes, but those were not adopted into the live adapter in this task because they are platform-contract decisions, not runtime-residue repairs.

Current conclusion:

- keep the live `cli_adapter.py`
- delete `cli_adapter.py.new`
- delete the root `.iflow/` residue now

### Recommended handling

1. Keep live runtime behavior as source of truth.
2. Resolve every `.new` explicitly; do not leave them hanging indefinitely.
3. Retain only latest `.trellis/.backup-*`.
4. Delete scattered live `*.backup` once comparison value is exhausted; keep backup-internal copies only inside the retained `.trellis/.backup-*` snapshot.

## Caveats / Not Found

- This audit did not execute `trellis update --migrate`; all conclusions are based on current on-disk live files and archived migration tasks.
- `__pycache__/` directories were intentionally excluded per user instruction and should not be reported as Trellis defects.

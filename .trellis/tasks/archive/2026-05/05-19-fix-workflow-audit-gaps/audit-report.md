# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - `project-audit` 正式进入链只允许从 `implementation` / `test-first` 进入，缺少从 `check` / `review-gate` 进入的标准编排，同时 `project-audit` 仍被当作 leaf-only stage
  - 任务列表状态展示仍只显示 `workflow-state.json.stage`，丢失 `blocked` / `awaiting_confirmation_with_blockers` / `target` / `reason`
  - `check-quality.py` 只支持 test/lint/typecheck，失败证据偏弱，跳过项没有标准化 `not run`
  - `task.py` 强门禁补丁仍残留 “planning → in_progress” 旧注释和旧示例
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` workflow-installed state (`/tmp/trellis-0.5.17-2`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Checked `COMPATIBLE_TRELLIS_VERSION` in `docs/workflows/新项目开发工作流/commands/workflow_assets.py` — Layer: `source repo`
- Ran `trellis -v` and confirmed `0.5.17` — Layer: `runtime command output`
- Read repo-local docs/scripts/skills specs and the `workflow-audit` contract — Layer: `source repo`
- Used `ace.search_context` plus targeted source reads to locate `project-audit`, `workflow-state`, task-status view patch, `check-quality.py`, and installed target copies — Layer: `source repo` / `generated target project`
- Read `/tmp/trellis-0.5.17-2` installed copies of `.trellis/scripts/workflow/workflow-state.py`, `.trellis/scripts/common/tasks.py`, `.trellis/scripts/task.py`, `.agents/skills/project-audit/SKILL.md`, `.agents/skills/check/SKILL.md` — Layer: `generated target project`
- Ran `python -m unittest docs.workflows.新项目开发工作流.commands.shell.test_check_quality` — Layer: `runtime command output`
- Ran `python -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state` — Layer: `runtime command output`
- Ran `PYTHONPATH=docs/workflows/新项目开发工作流/commands python -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers` — Layer: `runtime command output`
- Ran a one-off real-baseline patch probe that copied the current Trellis `task.py` / `common/tasks.py` / `task_queue.py` into a temp root and executed `patch_task_status_views()` to verify the task-list/help rewrite path — Layer: `runtime command output`

## Confirmed Issues

### [P1] `project-audit` 正式进入链真实缺口，且伴随 leaf-only 同类问题
- Conclusion: 真实存在。`project-audit.md` 明确把正式模式定义为“全部代码相关任务完成后，在最终质量门禁前做一次项目级统一回看”，但 `workflow-state.py` 与 `workflow-patch-projectization.md` 只允许 `implementation/test-first -> project-audit`。同时 `project-audit` 还被放在 `LEAF_REQUIRED_STAGES` 中，导致聚合 task 在正式 project-audit 场景下会被误判为必须切到子任务。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/project-audit.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - Layer: `generated target project`
  - `/tmp/trellis-0.5.17-2/.agents/skills/project-audit/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
- Validation Action:
  - 静态比对 source repo 与 `/tmp` 安装态 transition graph / stage category
  - 新增 `test_check_allows_project_audit_transition`、`test_review_gate_allows_project_audit_transition`、`test_validate_allows_parent_task_with_children_during_project_audit`
- Applied Fix:
  - `workflow-state.py` 新增 `check -> project-audit`、`review-gate -> project-audit`
  - `project-audit` 改为 coordination stage，不再 leaf-only
  - 同步更新 `project-audit.md` 与 `workflow-patch-projectization.md` 的正式/预审入口说明

### [P1] 任务列表状态展示仍然丢失 strong-gate 语义
- Conclusion: 真实存在。`/tmp` 中 `.trellis/scripts/common/tasks.py` 的 `_display_status()` 只显示裸 `stage`，没有把 `route` 的 `action / target / blockers / reason` 带出来；这与已 route-first 的 session hooks 表意不一致。
- Evidence Source:
  - Layer: `generated target project`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
- Validation Action:
  - 对照 hooks breadcrumb 已注入的 route metadata 与 task list patch 的现状
  - 新增 installer 断言，验证 `common/tasks.py` 会安装 route-aware status summary 补丁
- Applied Fix:
  - 安装器的 task-status view patch 改为调用 `workflow-state.py route`，把关键 strong-gate 摘要附加到任务展示元数据
  - 保持主状态仍以 stage 为主，避免直接回退到 legacy `task.json.status`

### [P2] `check-quality.py` 证据模型偏弱
- Conclusion: 真实存在。原 helper 只支持 `test/lint/typecheck`，省略项只打印“跳过”而非 `not run`，失败时只保留 stdout，stderr 丢失。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
  - `docs/workflows/新项目开发工作流/commands/check.md`
  - Layer: `generated target project`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/check-quality.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/check/SKILL.md`
- Validation Action:
  - 静态读取 `/tmp` 安装态 helper 与 check skill
  - 新增 `test_check_quality.py`，覆盖 `not run`、额外检查、stderr 证据
- Applied Fix:
  - `check-quality.py` 新增 `--extra-check LABEL=COMMAND`
  - 统一输出 `Result: pass / fail / not run`
  - 失败时保留 `Exit Code`、stdout、stderr；无任何命令时保持非零退出
  - `check.md` 同步升级使用说明

### [P2] `task.py` 仍残留 legacy status 语义注释
- Conclusion: 真实存在。`/tmp` 中 `.trellis/scripts/task.py` 仍保留 “Still flip task.json status: planning → in_progress...” 注释，帮助示例仍有 `--status in_progress` 残影。
- Evidence Source:
  - Layer: `generated target project`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Validation Action:
  - 静态读取 `/tmp` 安装态 task.py
  - 安装器测试验证 no-status-flip patch 重新命中并移除旧注释
  - 额外执行 real-baseline patch probe，确认 `task.py` 旧 `--status in_progress` 示例和列表摘要补丁能在真实 baseline 上命中
- Applied Fix:
  - `patch-task-start-strong-gate.py` 先替换 legacy 注释，再稳定命中 status-flip block
  - 安装器 refresh 逻辑同步保留新注释语义
  - `task.py` 帮助示例在真实 baseline 可被替换为 stage-based 示例

## Unconfirmed Items / False Alarms

- None in this run. 用户列出的四类问题全部确认为真实存在；其中 `project-audit` 额外带出了 leaf-only 同类缺陷。

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

- None

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable
- Repo-local evidence checked: `project-audit.md`, `check.md`, installer patch chain
- Practical development-use evidence checked: installer tests deploying `.claude/commands/trellis/*`
- Agreement / discrepancy: 本轮修复不改变 Claude 载体边界；相关安装测试通过

### OpenCode
- Official docs checked: not-applicable
- Repo-local evidence checked: `project-audit.md`, `check.md`, installer patch chain
- Practical development-use evidence checked: installer tests deploying `.opencode/commands/trellis/*`
- Agreement / discrepancy: 本轮修复不改变 OpenCode 载体边界；相关安装测试通过

### Codex
- Official docs checked: local carrier evidence only
- Repo-local evidence checked: `.agents/skills/*`, `.codex/hooks/*`, installer patch chain
- Practical development-use evidence checked: `/tmp` 安装态 skill/task 脚本 + installer tests
- Agreement / discrepancy: 本轮未改变 Codex 主承载边界，但修复了 shared task/task-view patch 的强门禁一致性

## Suggested Fix Directions

- 已实施：扩展 `project-audit` transition graph，并把其从 leaf-only 执行态中移出
- 已实施：将任务列表状态展示升级为 route-aware summary，而不是裸 `stage`
- 已实施：增强 `check-quality.py` 的 `pass/fail/not run` 证据输出与额外检查能力
- 已实施：修复 no-status-flip patch 的命中稳定性并移除 legacy 注释残留

## Propagation Scope and Synchronized Update Range

- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/project-audit.md`
- `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/check.md`
- `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
- `docs/workflows/新项目开发工作流/commands/shell/patch-task-start-strong-gate.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/shell/test_check_quality.py`
- `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`

## Recommended Next Step
- Recommended action: `finish verification / commit planning`
- Trigger condition: `工作流 source 侧修复已完成，三组验证命令均通过`
- Recommendation reason: `当前问题已在 workflow source 层闭环，且没有遗留 failed / blocked 验证`
- Stronger alternatives not selected: `未直接重嵌入 /tmp/trellis-0.5.17-2；本轮依赖已有安装态证据与 fresh installer tests`

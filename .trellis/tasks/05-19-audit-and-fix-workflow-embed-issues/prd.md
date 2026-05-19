# 审计并修复新项目开发工作流嵌入问题

## Goal

基于 `docs/workflows/新项目开发工作流` 的源码资产与 `/tmp/trellis-0.5.17-2` 的已嵌入结果，验证用户列出的候选问题哪些在当前版本中仍真实存在，并只在 `docs/workflows/新项目开发工作流` 内进行兼容性修复。

## What I Already Know

- 当前工作流版本锚点为 `0.5.17`，本机 `trellis -v` 也是 `0.5.17`，满足 `workflow-audit` 的 same-version 门禁。
- `/tmp/trellis-0.5.17-2/.trellis/workflow.md` 的 no-task 入口已声明：
  - 外包项目：首次入口先走 feasibility。
  - 个人项目：允许跳过 feasibility，但必须在 brainstorm 中补齐 `assessment.md` 核心字段。
- 当前源码中的 `workflow-state.py route` 已部分支持“无 active task 但已有允许进入 brainstorm 的 assessment 时，first_entry 直接指向 brainstorm”。
- 当前 `/tmp` 样本中的 `.trellis/scripts/task.py` 已带有 `strong-gate-no-status-flip` 补丁：当 `workflow-state.json` 存在时，`task.py start` 不再把 `task.json.status` 从 `planning` 翻成 `in_progress`。
- 当前 `/tmp` 样本中的 `.codex/hooks/inject-workflow-state.py` 已带有 `prefer-workflow-route` 补丁：breadcrumb 读取 `workflow-state.py route`，不是单纯读 `task.json.status`。

## Candidate Issue Triage

### Confirmed

1. 个人项目“可跳过 feasibility，在 brainstorm 补 assessment”与 `brainstorm` / `workflow-state.py validate` 的强制 assessment 前置仍冲突。
   - 安装后 `.trellis/workflow.md` 明确允许 personal profile 直进 brainstorm。
   - 但 `commands/brainstorm.md` 与 `workflow-state.py` 的 `validate_external_project_controls()` / `collect_route_readiness_blockers()` 仍将“缺少 assessment.md”视为 brainstorm 阶段阻断。
   - 这是当前真实缺陷，不是纯操作繁琐。

2. 阶段切换文档仍有同类不一致残留。
   - `workflow-state.py set` 对除 feasibility 外的阶段切换强制要求当前 `stage_status=awaiting_user_confirmation`。
   - 但仍有补丁源文档保留了“feasibility → brainstorm 直接 set --stage brainstorm”的旧写法，未显式包含 readiness step。
   - 这会导致源码资产与真实实现不一致，并在重新嵌入后继续传播。

3. 部分“已修一半”的规则仍未全链路同步。
   - 安装后 `.trellis/workflow.md`、`workflow-state.py route`、`task.py`、hook 补丁已经部分吸收新语义。
   - 但 `brainstorm.md`、`workflow-patch-projectization.md`、以及 `workflow-state.py` 校验逻辑仍保留旧前提，属于源资产层协议分叉。

### Not A Current Defect

1. “route 在没有 workflow-state.json 时一律建议 init --stage feasibility”
   - 当前源码已不再“一律”如此。
   - `cmd_route()` 在无 active task 且无 task 时，会根据现有 `assessment.md` 判断 first_entry 指向 `feasibility` 还是 `brainstorm`。
   - 仍存在的问题不是 route 完全不支持，而是与 personal-profile 文案和 validate 逻辑尚未统一。

2. “task.py start 保留双真相窗口”
   - 在当前工作流源码对应的安装后样本里，`task.py start` 已通过补丁避免在 `workflow-state.json` 存在时再翻转 `task.json.status`。
   - 剩余问题只是在 `workflow-state.json` 尚不存在时，fallback 仍会翻转 `task.json.status`；这属于兼容性设计，不是当前候选描述中的原始缺陷。

3. “Hook 每轮 route 会把入口污染”
   - 当前 hook 读取 route 是有意设计，用于展示 `action/stage_status/blockers`，不再把 blocked/repair 状态降级成普通阶段名。
   - 这是运行成本与可观测性的取舍，不构成当前需要在本次范围内回退的真实缺陷。

## Repair Scope

- 只修改 `docs/workflows/新项目开发工作流/**`
- 重点修复：
  - personal profile 首次进入 brainstorm 的协议与文档/校验一致性
  - feasibility → brainstorm 的两步切换文档一致性
  - 与上述问题同类的补丁源 / 命令文档 / 路由说明残留不一致

## Acceptance Criteria

- `brainstorm` 源文档、`workflow-state.py`、`workflow-patch-projectization.md` 对 personal profile 首次入口的说明一致。
- `workflow-state.py validate` / `route` 对 personal profile 的 brainstorm 入口不再与安装后 `.trellis/workflow.md` 自相矛盾。
- `workflow-state.py set` 的阶段切换契约在文档中不再保留会失败的示例。
- 修改后只触及 `docs/workflows/新项目开发工作流`。

# 修复嵌入工作流门禁与交付控制缺陷

## Goal

修复 `docs/workflows/新项目开发工作流` 中已经确认存在的门禁与交付控制缺陷，使后续嵌入到目标项目后的 workflow 在 `/tmp/trellis-$(trellis -v)-2` 这类目标项目里能正确强制 formal `PROJECT-AUDIT`、真实 task 存在性、UI 前端基线链路、显式 task-level owner 绑定，以及稳定的 `delivery_control_track` 解析，同时不破坏现有“task-level check 与 project-level project-audit 属于并列双门禁”的设计。

## What I already know

- 用户要求只修改 `docs/workflows/新项目开发工作流`，其他目录不能改。
- 真实判断对象是嵌入后的临时目标项目 `/tmp/trellis-0.5.17-2`，source workflow 的修复要让未来嵌入后的结果正常。
- 已确认真实问题：
  - plan 阶段没有强制“条件性必建 PROJECT-AUDIT”
  - 外部交付控制任务与源码归属证明任务只做文案出现校验，没有强制真实 Trellis task 存在
  - `task_level_check_task` 的 source 文档仍鼓励 `current_active_task/self/parent` 等隐式 owner
  - UI 前端视觉链路只有文档，没有正式 plan gate
  - `delivery-control-validate.py` 在 plan/delivery 阶段对 `trial_authorization` 采用脆弱字符串匹配
- 已重新确认第 2 点不能按“check 与 project-audit 混维度”处理：
  - `check` 是任务级闭环
  - `project-audit` 是项目级闭环
  - `delivery` 同时消费两者是设计契约，不是缺陷
- 第 2 点真正可修的收敛版本是：
  - formal `project-audit` 在判断“代码相关 task 已完成”时，可以接受 `check` 阶段已闭环但尚未 archive 的 task
  - 但若某个被引用 task 已声明自己处于 `review-gate` 或 `delivery`，则不应只重验 `check.md`，还应要求其当前声明阶段的正式 artifact 也闭环

## Assumptions (temporary)

- 允许在 `docs/workflows/新项目开发工作流/commands/shell/test_*.py` 中新增或调整测试，以锁定修复后的行为。
- 如需修改 source command 文档或 skill 文档，应只改 `docs/workflows/新项目开发工作流` 内的 source 资产，不改 repo 级 `.agents/skills/` 实际运行副本。
- 本次不扩展到 Trellis 原生其他目录；若存在必须依赖 patch 的问题，只在 workflow source 的合适位置打补丁。

## Open Questions

- 无阻塞问题；修复范围和收敛口径已经由用户确认。

## Requirements (evolving)

- 修复 `plan-validate.py`，让其在满足 formal `PROJECT-AUDIT` 条件时强制要求真实 project-audit task，而不是只在已声明时做一致性检查。
- 修复 `delivery-control-validate.py`，让 plan/delivery 阶段基于结构化字段解析 `delivery_control_track`，不再依赖固定字面串。
- 修复 `delivery-control-validate.py`，让外部交付控制任务不仅要在摘要中出现，还必须出现在结构化 `Trellis Task 清单` 且对应 task 目录真实存在。
- 修复同类问题：`ownership-proof-validate.py` 里的归属证明任务也应升级为真实 task 存在性校验，而不只是文案出现。
- 修复 `validators_gates.py` / 对应文档，使 `task_level_check_task` 新文档只鼓励显式真实 owner；运行时可保留 legacy 兼容读取，但不能再把隐式 owner 当推荐新写法。
- 修复 formal `project-audit` 对上游代码相关 task 完成态的判断：
  - 保留 `check` 已闭环但 task 尚未 archive 的合法路径
  - 如果上游 task 已声明 `review-gate` 或 `delivery`，则其对应阶段 artifact 也必须闭环
  - 不改变 `check` 与 `project-audit` 属于双维度并列门禁的设计
- 为 UI 前端视觉链路新增正式 plan gate：
  - 当 `ui_lane_decision` 表示存在前端视觉落地链路时
  - 必须存在 `UI -> 首版代码界面` 独立 task
  - 计划摘要中必须明确 `design/frontend-ui-spec.md` 作为后续前端任务统一约束来源

## Acceptance Criteria (evolving)

- [ ] 针对已确认真实问题的新增/修改测试先失败，再在实现后通过。
- [ ] `plan-validate.py` 能拦截“本应存在 PROJECT-AUDIT 但未建真实 task”的 plan。
- [ ] `delivery-control-validate.py` 能拦截“只写摘要不建真实交付控制 task”的 plan，并能稳定识别合法 `trial_authorization` assessment。
- [ ] `ownership-proof-validate.py` 能拦截“只写摘要不建真实归属证明 task”的 plan。
- [ ] `validators_gates.py` 对 formal `project-audit` 的代码相关 task 完成态判定不再对 `review-gate` / `delivery` 仅复验 `check.md`。
- [ ] 现有合法路径保持可用：
  - task-level `check` 已闭环但 task 未 archive，formal `project-audit` 仍可接受
  - `delivery` 仍同时消费 task-level `check` 与 project-level `project-audit`
- [ ] 相关 source 文档与测试已同步更新，不留下新旧契约冲突。

## Definition of Done (team quality bar)

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green where applicable
- Docs/notes updated if behavior changes
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- 不修改 `docs/workflows/新项目开发工作流` 之外的目录
- 不重构无关 workflow 阶段或 CLI 适配面
- 不改变“check 是任务级、project-audit 是项目级”的双维度设计
- 不把 source workflow 扩展成新的功能集，只修已确认缺陷与同类紧邻问题

## Technical Notes

- 主要实现文件预期包括：
  - `docs/workflows/新项目开发工作流/commands/shell/plan-validate.py`
  - `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
  - `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - 相关 source command docs under `docs/workflows/新项目开发工作流/commands/*.md`
  - 对应 `test_*.py`
- 参考证据来自 `/tmp/trellis-0.5.17-2` 的嵌入后副本与 source workflow 对照分析。

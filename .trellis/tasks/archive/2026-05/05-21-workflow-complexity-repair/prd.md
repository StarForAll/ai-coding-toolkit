# audit and repair embedded workflow complexity issues

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流` 的临时目标项目，判断用户列出的“状态管理双轨制 / 两步阶段切换 / 文档过载 / workflow-state.py 过重 / degraded-active-task / needs-init / repair_needed / recovery_needed”等问题是否真实存在；若确认存在，则只在 `docs/workflows/新项目开发工作流` 内做安全修复，并同步修复同根因的类似问题，避免再次在临时项目分析时反复发现同类缺陷。

## What I Already Know

- 当前仓库是工作流作者仓库，`docs/workflows/新项目开发工作流` 是待修复的产品源目录，不是当前仓库自身运行中的 workflow。
- 用户明确要求判断对象是 `/tmp/trellis-0.5.17-2` 的实际嵌入结果，修复位置只允许在 `docs/workflows/新项目开发工作流`，任务目录可写，其他目录不能修改。
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 的 `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.17`，当前 `trellis -v` 也是 `0.5.17`，版本门禁通过。
- `workflow-audit` 明确要求：先验证候选问题是否真实，再做修复；`workflow-repair` 明确要求：目标判断仍以临时项目为主，源仓库只是修复位置。
- 初步检索显示该工作流确实大量依赖 `workflow-state.json`、`workflow-state.py route`、`awaiting_user_confirmation`、`repair_needed`、`recovery_needed` 与 degraded active-task fallback。

## Constraints

- 只允许修改 `docs/workflows/新项目开发工作流/**` 和当前任务目录。
- 不修改 `/tmp/trellis-0.5.17-2`、`.trellis/` 现有运行时、仓库其他目录。
- 若问题根因在 Trellis 原生侧，只能在工作流目录内通过补丁、安装器、命令文档或约束调整来闭环，不得越界修 Trellis 源。
- 需要同时检查同类问题与契约面，避免只修单点症状。

## Candidate Issues To Validate

- `task.json.status`、`workflow-state.json.stage`、`.runtime/sessions/*.json` 是否形成过度复杂的多层状态源。
- 阶段切换是否依赖 “先置 `awaiting_user_confirmation`，再用户确认后 set 到下一阶段” 的双步骤协议，且维护成本过高。
- 工作流文档数量与分层是否已经形成维护负担，并且文档与脚本/安装结果是否存在漂移。
- `commands/shell/workflow-state.py` 是否承担了超出合理边界的职责，并由此制造了恢复与状态碎片问题。
- `degraded-active-task-*` fallback、`repair_needed`、`recovery_needed` 等恢复分支是否是真需求，还是被工作流设计放大出来的伪问题。
- 是否存在同根因的附带问题，例如补丁脚本、命令文档、walkthrough、安装说明仍把复杂协议当成必需契约。

## Requirements

- 以 `/tmp/trellis-0.5.17-2` 的已安装文件和行为作为“问题存在性”主证据。
- 对每个候选项输出结论：真实问题 / 非问题但设计选择 / 证据不足。
- 对真实问题执行最小且完整的源工作流修复，并同步更新同契约面的脚本、文档、测试或安装声明。
- 不引入新的跨文件漂移、路径错误、版本不一致或补丁失效。

## Acceptance Criteria

- [ ] 对用户列出的每类问题都给出基于临时项目和源工作流的证据判断。
- [ ] 至少修复已确认存在且可在工作流源目录内安全闭环的问题，并一并处理同类问题。
- [ ] 所有修改仅发生在 `docs/workflows/新项目开发工作流/**` 与当前任务目录。
- [ ] 运行相关验证命令，真实报告 pass / fail / not run。

## Out Of Scope

- 不直接修改 Trellis 原生源码或当前仓库 `.trellis/` 运行时。
- 不在本次任务中重构整个 workflow 为原生 Trellis 单文件模型，除非证据表明存在必须修复的错误契约。
- 不删除任务文件。

## Technical Notes

- 关键技能：`workflow-audit` 负责判定候选问题真假，`workflow-repair` 负责在工作流源目录内闭环修复。
- 关键证据面：
  - 源工作流：`docs/workflows/新项目开发工作流/**`
  - 临时项目：`/tmp/trellis-0.5.17-2/**`
  - 当前任务：`.trellis/tasks/05-21-workflow-complexity-repair/`

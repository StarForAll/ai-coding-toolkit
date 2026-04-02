# Workflow E2E Issues

This file is the single record for:

- simulated human inputs
- workflow defects
- project assumptions
- environment gaps
- stop conditions

## Usage

Append new records. Do not split records into multiple files unless explicitly requested.

## Template

```md
## SIM-001
- kind: simulated-human-input
- stage: feasibility
- role: customer | user | reviewer
- prompt: <what confirmation was needed>
- input: <simulated human input>
- note: only for this project black-box test

## ISSUE-001
- kind: workflow-defect | project-assumption | env-gap | stop-condition
- stage: feasibility | brainstorm | design | plan | test-first | start | self-review | check | finish-work | delivery | record-session
- trigger: <what triggered the issue>
- observed: <what actually happened>
- expected: <what should have happened according to the workflow>
- decision: <what this project decided to do>
- impact: <impact on the next stage>
```

## Initial Frozen Inputs

### SIM-001
- kind: simulated-human-input
- stage: feasibility
- role: customer
- prompt: 项目是否值得做，是否允许进入 brainstorm
- input: 值得做，允许进入 brainstorm，按 MVP 范围继续
- note: internal personal project, no external delivery branch

### SIM-002
- kind: simulated-human-input
- stage: brainstorm
- role: customer
- prompt: MVP 范围与复杂度确认
- input: 采用本地工具 MVP，复杂度按 L1 处理，走完整主链
- note: prioritize workflow black-box coverage over shortest delivery path

### SIM-003
- kind: simulated-human-input
- stage: design
- role: customer
- prompt: 技术路线确认
- input: 采用本地 Web 单页应用，首版无后端，但保留后续扩展后端的可能
- note: browser extension is out of scope for the first version

### SIM-004
- kind: simulated-human-input
- stage: design
- role: customer
- prompt: 重复判定与导出策略确认
- input: 仅按 URL 完全相同判定重复；首版只标记重复项；导出清理后的 bookmarks.html
- note: do not auto-move duplicates into archive folders in the first version

## ISSUE-001
- kind: env-gap
- stage: feasibility
- trigger: 开始按 workflow 真正进入黑盒测试时检查目标项目 Trellis 运行基线
- observed: 目标项目当前只有 `.trellis/tasks/...`，缺少 `.trellis/scripts/`、`.trellis/workflow-installed.json`、`.trellis/library-lock.yaml` 等 workflow 常规运行结构，无法按文档中的命令入口直接执行
- expected: 目标项目应先具备 Trellis init 和 workflow 嵌入后的最小运行基线，再从 `feasibility` 开始走主链
- decision: 本次黑盒测试继续，但将 `feasibility` 视为“按 workflow 语义手工执行并落产物”，不伪装为已具备完整命令运行环境
- impact: 后续阶段需要持续区分“语义执行成功”和“命令入口可直接运行”这两层结果

## ISSUE-002
- kind: workflow-defect
- stage: design
- trigger: 进入前端/UI 设计阶段
- observed: `design` 阶段正文将前端设计强绑定到外部 UI 站点与原型工具，并要求明确提醒用户离开当前 CLI 去完成操作
- expected: workflow 应提供“纯本地文档降级链路”或明确声明这是可选分支，而不是让前端项目默认命中外部工具依赖
- decision: 本次黑盒测试记录该缺陷，并在目标项目内仅使用本地设计文档继续推进，不生成真实外部 UI 工具产物
- impact: 可以继续进入设计文档产出，但“真实外部 UI 设计调用”这条链路在本次未被覆盖

## ISSUE-003
- kind: project-assumption
- stage: design
- trigger: 命中 ISSUE-002 后决定是否继续
- observed: 当前 workflow 文档没有给出纯本地前端设计降级模板
- expected: 至少应允许在目标项目内通过页面说明、规格说明、技术设计继续推进到 `plan`
- decision: 本次项目将用本地 `design/` 文档骨架、页面说明和模块规格代替外部 UI 工具产物
- impact: 后续 `plan` 依然可以读取设计目录，但需要记住这属于当前项目临时假设，不代表 workflow 已修复

## ISSUE-004
- kind: env-gap
- stage: design
- trigger: 使用 workflow 自带 `design-export.py --scaffold` 在目标项目内创建设计骨架
- observed: 当前运行环境的文件系统沙箱默认不允许命令直接写目标项目目录，需要额外提权后才能执行官方脚本
- expected: 在真实本地开发环境中，目标项目目录应默认可写，不应因为测试沙箱限制阻塞 design 阶段
- decision: 本次黑盒测试保留脚本执行结果，并将沙箱限制视为环境问题，不视为 workflow 本体缺陷
- impact: 后续凡是依赖命令直接写目标项目的步骤，都要同时区分“workflow 是否可行”和“当前沙箱是否允许”

## ISSUE-005
- kind: workflow-defect
- stage: plan
- trigger: 进入 `plan` 前检查文档列出的前置条件
- observed: `plan` 阶段要求在拆任务前先完成 `.trellis/spec/` 对齐、自动化检查矩阵定义、`finish-work` 首次项目化适配、`record-session` 基线适配；而当前空项目黑盒测试没有明确的低成本初始化路径来完成这些前置
- expected: 对于从零开始的新项目黑盒测试，workflow 应给出更清晰的最小可执行路径，或显式提供“先生成 task_plan.md，再逐步补齐 spec/收尾基线”的降级方案
- decision: 本次黑盒测试继续，但将 `plan` 视为“在设计文档基础上先手工生成 task_plan.md”，不把 `.trellis/spec/` 缺失伪装成已解决
- impact: 后续 `test-first` 和实施阶段可继续推进，但需要持续记住 plan 前置条件并未完全满足

## ISSUE-006
- kind: project-assumption
- stage: plan
- trigger: 命中 ISSUE-005 后决定是否继续主链
- observed: 当前目标项目尚未引入 `.trellis/spec/` 与项目化的 `finish-work` / `record-session` 基线
- expected: 若 workflow 有官方降级路径，应优先使用
- decision: 当前项目先以已有 `assessment.md`、`prd.md`、`design/` 为输入，直接手工生成 `task_plan.md`，把缺失前置作为后续黑盒观察点，而不是当前阶段硬阻断
- impact: 后续若审查或收尾阶段再次依赖这些基线，需要重新评估是否继续还是停止

## SIM-005
- kind: simulated-human-input
- stage: test-first
- role: customer
- prompt: 首版前端实现栈确认
- input: 采用本地前端工程，优先选择轻量可测方案；当前测试默认按 TypeScript 前端工程 + 单元测试能力推进
- note: only for this project black-box test, used to let test-first continue without additional clarification

## ISSUE-007
- kind: workflow-defect
- stage: test-first
- trigger: 读取 `test-first` 阶段正文时检查默认输出与门禁
- observed: 文档将测试文件命名、评估集格式和验证命令默认写死为 `tests/<module>.test.ts`、`tests/evals/EVAL-<id>.yaml`、`pnpm test`
- expected: workflow 应把这些作为示例或模板，而不是对空项目新建流程默认强绑定单一前端技术栈与包管理器
- decision: 本次黑盒测试继续沿用该默认格式落测试产物，以尽量贴近文档默认路径
- impact: 后续实施阶段如果继续沿用该技术栈假设，则需要同时记录“这是项目假设，不是 workflow 的通用能力”

## ISSUE-008
- kind: env-gap
- stage: test-first
- trigger: 运行 `pnpm test`
- observed: 测试命令在当前沙箱内首次执行失败，原因是 Vitest/Vite 需要创建临时目录；提权后测试真实通过
- expected: 在真实本地开发环境中，`pnpm test` 应直接可运行，不应因测试沙箱写权限失败
- decision: 本次把测试结果判定为“代码通过，环境层面需额外权限”
- impact: 后续 `build`、`dev`、`finish-work` 等命令结果也需要区分“代码问题”和“当前沙箱权限问题”

## ISSUE-009
- kind: env-gap
- stage: finish-work
- trigger: 运行 `pnpm build`
- observed: 构建命令在当前沙箱内首次执行失败，原因是 Vite 需要写入临时配置与产物目录；提权后构建真实通过
- expected: 在真实本地开发环境中，`pnpm build` 应直接可运行，不应因测试沙箱写权限失败
- decision: 本次把构建结果判定为“代码通过，环境层面需额外权限”
- impact: 后续 finish-work 结论需要同时写明真实代码状态和当前测试环境限制

## ISSUE-010
- kind: env-gap
- stage: delivery
- trigger: 进入交付与收尾链路时检查 git 依赖
- observed: 目标项目当前不是 git 仓库，无法按 workflow 默认路径生成基于提交历史的 changelog，也无法满足部分提交前/收尾检查假设
- expected: 目标项目若要完整走 delivery 和 record-session，应具备最小 git 仓库状态
- decision: 本次继续手工生成交付文档，但不伪装为已满足 git 侧收尾前提
- impact: `delivery` 可部分继续；`record-session` 可用性会进一步受限

## ISSUE-011
- kind: stop-condition
- stage: record-session
- trigger: 检查 `/trellis:record-session` 默认依赖
- observed: 目标项目缺少 `.trellis/scripts/task.py`、`.trellis/.current-task`、record-session helper 等 Trellis 基线脚本与元数据闭环能力，无法按文档原样完成 archive 和 session record
- expected: 若 workflow 要支持从零开始的新项目黑盒测试，应明确提供 record-session 的最小初始化路径或合法中断出口
- decision: 本次黑盒测试在交付文档完成后停止于 `record-session` 前，不伪造 archive / helper 执行成功
- impact: 当前主链已覆盖到 delivery，但最终 record-session 无法按文档原样闭环

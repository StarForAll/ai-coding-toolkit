# Project Rules


<!-- workflow-nl-routing-start -->

## 自然语言命令路由

> 由工作流安装器自动生成。当用户用自然语言描述意图时，本表提供阶段入口候选映射与推荐口径。
>
> 入口约束：
> - Claude Code / OpenCode：优先使用项目级 `/trellis:xxx` 命令；OpenCode CLI 可使用 `trellis/xxx`
> - Codex：通过 `AGENTS.md` 自然语言路由或显式触发对应 skill；不要期待项目级 `/trellis:xxx` 命令目录
> - 本表用于缩小候选范围，不表示所有 CLI 都存在确定性的自动命令路由；若命中歧义、缺少前置条件或上下文不足，仍应先确认再进入对应阶段
> - 当前 workflow 采用强门禁阶段状态机：阶段切换必须由用户明确确认；`/trellis:continue` 只重入当前已确认阶段，不自动跨阶段推进
> - 当前嵌入 workflow **显式禁用** `agent / subagent` 路径；即使平台仍保留 `trellis-*` agent carrier 或通用 agent/subagent 能力，也不得派发，所有 research / implement / check 都必须由当前主会话按阶段入口直接完成

### 工作流阶段命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 评估、能做吗、报价、新项目、风险、可行性、接不接、看看这个项目、能不能接、估个价、接私活、外包项目、客户需求 | `/trellis:feasibility` | 描述可行性评估意图，或显式触发 `feasibility` skill | §1 可行性评估。所有新实现任务默认先走这里；若 route 返回 `profile_hint=unknown`，保持 feasibility 保守回退并先确认项目应按 personal 还是 outsourcing 理解；若已有仍有效的 assessment，可复用结果 |
| 需求、PRD、明确需求、需求文档、需求分析、想法、梳理需求、讨论方案、判断要不要拆任务 | `/trellis:brainstorm` | 描述需求澄清意图，或显式触发 `brainstorm` skill | §2 需求发现。前提：已存在有效 assessment，并且 assessment 明确允许进入 brainstorm |
| 设计、架构、架构设计、选型、接口设计、方案、技术方案、开始设计、画架构图、设计方案 | `/trellis:design` | 描述设计阶段意图，或显式触发 `design` skill | §3 设计阶段 |
| 拆任务、排期、计划、任务分解、里程碑、估时、做计划、工作分解、工作计划 | `/trellis:plan` | 描述任务拆解意图，或显式触发 `plan` skill | §4 任务拆解 |
| 写测试、TDD、测试驱动、先写测试、测试用例、验收测试 | `/trellis:continue` | 描述测试先行意图，并在 implementation 内按 TDD 方式执行，或显式触发相关测试先行 skill | implementation 内的测试先行入口，不是独立公开阶段命令 |
| 项目全局审查、全局代码审查、代码查缺补漏、项目审计、project-audit | `/trellis:project-audit` | 描述项目级审查意图，或显式触发 `project-audit` skill | §5.1 项目全局审查 |
| 检查一下、质量检查、对照 spec、对照规范、自检、有没有偏差 | `/trellis:check` | 描述质量检查意图，或显式触发 `check` skill | §5.1.x 质量检查 |
| 补充审查、多 CLI 审查、多人审查、让其他 CLI 看一下、review-gate、审查门禁 | `/trellis:review-gate` | 描述补充审查意图，或显式触发 `review-gate` skill | §5.1.y 补充审查 |
| 提交前检查、准备提交、完成检查、commit 前、收尾 | `/trellis:finish-work` | 描述提交前检查意图，或显式触发 `trellis-finish-work` skill | §6 提交检查 |
| 交付、部署、上线、发布、测试通过、准备交付、跑验收、整理交付物、项目收尾 | `/trellis:delivery` | 描述交付收尾意图，或显式触发 `delivery` skill | §6+§7 测试交付 |
| 记录、保存进度 | `/trellis:finish-work` | 描述当前活动任务的最终收尾 / 归档 / 会话记录意图，或显式触发 `trellis-finish-work` skill | native Trellis task-level close-out 入口。若当前轮同时存在项目级交付收口，再单独进入 `delivery` |
| 收工、结束工作 | `/trellis:finish-work` | 描述当前活动任务的最终收尾 / 归档 / 会话记录意图，或显式触发 `trellis-finish-work` skill | native Trellis task-level close-out 入口。若当前轮同时存在项目级交付收口，再单独进入 `delivery` |

### 框架通用命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 调研、研究、查资料、查文档、看源码、搜代码、搜资料、技术调研、仓库分析 | 描述研究意图，并由当前主会话继续处理；禁止派发 `trellis-research` 或其他 agent/subagent | 描述研究意图，并由当前主会话继续处理；禁止派发 `trellis-research` 或其他 agent/subagent | implementation 内部 research 仍由主会话直接完成；当前嵌入 workflow 已显式禁用 agent/subagent 路径 |
| 开始写代码、实现、开发、编码、动手、修这个功能、开始改代码 | `/trellis:continue` | 描述当前实现意图，或显式触发 `trellis-continue` skill | implementation 的公开重入入口。没有对称的 `/trellis:implementation` 命令；continue 会先做 Phase Router 判断，再在当前 task 上执行 implementation 内部链 |
| 开始、新会话、继续、下一步 | `/trellis:continue` | 描述当前意图，或显式触发 `trellis-continue` skill | Phase Router 自动检测 |
| 卡住了、反复出错、死循环、调不通 | 描述排障意图，或显式触发 `trellis-break-loop` skill | 描述排障意图，或显式触发 `trellis-break-loop` skill | 深度 bug 分析 |
| 更新规范、新发现、沉淀经验 | 描述规范更新意图，或显式触发 `trellis-update-spec` skill | 描述规范更新意图，或显式触发 `trellis-update-spec` skill | 规范更新 |
| 跨层检查、跨模块、影响面 | `/trellis:check` + 手动指定跨层范围 | 描述跨层检查意图，或显式触发 `check` skill 并说明跨层范围 | 当前未提供专用 `check-cross-layer` skill；用 `/trellis:check` 替代 |
| 集成 skill、添加 skill | 手动完成 skill 集成 | 手动完成 skill 集成 | 当前未提供专用 `integrate-skill` skill；按 skill 文档手动集成 |
| 读规范、开发前准备、看看有什么规范 | `/trellis:continue` | 描述开发前准备意图，或显式触发 `trellis-before-dev` skill | 开发前读规范；当前 workflow 默认由 continue 自动执行 before-dev，不承诺存在独立 `/trellis:before-dev` 命令 |
| 新人入门、项目介绍、怎么用 trellis | 阅读 AGENTS.md NL 路由表 | 阅读 AGENTS.md 路由表 | 当前未提供专用 `onboard` skill；按项目文档入门 |
| 创建命令、新命令、加个命令 | 按平台格式手动创建 | 按平台格式手动创建 | 当前未提供专用 `create-command` skill；按对应 CLI 格式手动创建 |

### 歧义消解

- 多个命令匹配时：当前阶段上下文 > 精确关键词 > 当前已确认阶段优先 > 模糊语义
- 无法确定时：路由到 `/trellis:continue`（Phase Router 自动检测）
- 当前 workflow 明确禁用基于 `parallel/worktree` 的后台 dispatch + PR 完成路径；如用户提到并行开发，应先回到 `/trellis:plan` 重新安排任务依赖，不再默认路由到 `parallel`
- top-2 优先级接近时：向用户确认意图，而不是假定已经完成自动精确路由

<!-- workflow-nl-routing-end -->

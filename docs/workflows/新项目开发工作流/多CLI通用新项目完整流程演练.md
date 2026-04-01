# 多CLI通用新项目完整流程演练

> 首次接触这套 workflow 时，优先看这份文档。它负责把 Claude Code、OpenCode、Codex 在同一个目标项目里的通用主链讲清楚，并把专项案例分流到对应文档。

---

## 这份文档的定位

这不是平台安装说明，也不是某个具体业务案例。

它只做三件事：

- 说明新项目主链从 `feasibility` 到 `record-session` 应该怎么走
- 明确 Claude Code、OpenCode、Codex 的入口差异
- 给出每个阶段推荐调用的 MCP / skills、典型降级方式和退出门禁

若你需要平台原生配置细节，请按需再看：

- [工作流总纲](./工作流总纲.md)
- [命令映射](./命令映射.md)
- [双轨交付控制完整流程演练](./完整流程演练.md)
- [Claude Code 适配](./commands/claude/README.md)
- [OpenCode 适配](./commands/opencode/README.md)
- [Codex CLI 适配](./commands/codex/README.md)

---

## 如何阅读这套 Workflow

### 阅读导航表

| 场景 | 先看 | 再看 | 为什么 |
|------|------|------|--------|
| 第一次接触这套 workflow | 本文 | [工作流总纲](./工作流总纲.md) | 先建立主链，再补完整规则 |
| 已经知道阶段名，但不清楚怎么触发 | 本文 | [命令映射](./命令映射.md) | 本文讲阶段目的，映射文档讲入口和路由 |
| 需要某个 CLI 的具体承载方式 | 本文对应阶段 | 平台 README | 主链和平台细节分开，避免默认上下文过重 |
| 你做的是外包 / 定制 / 新客户交付 | 本文 | [双轨交付控制完整流程演练](./完整流程演练.md) | 本文给通用主链，专项文档给外部交付案例 |
| 你只想看某个阶段的命令正文 | 本文对应阶段 | `commands/*.md` | 先知道为什么走这一步，再看命令细则 |

### 文档角色表

| 文档 | 角色 |
|------|------|
| `多CLI通用新项目完整流程演练.md` | 第一入口，讲通用主链 |
| `工作流总纲.md` | 权威规则层，讲原则、门禁、边界 |
| `命令映射.md` | 路由层，讲阶段到命令 / skills / CLI 的映射 |
| `完整流程演练.md` | 专项案例层，讲外部项目双轨交付控制 |
| `commands/*/README.md` | 平台展开层，讲各 CLI 的原生承载方式 |

---

## 使用前提

### 多 CLI 同装，但入口协议不同

同一个目标项目里，可以同时存在 Claude Code、OpenCode、Codex 的适配层，但三者入口协议不同：

| CLI | 阶段入口 |
|-----|---------|
| Claude Code | 项目命令：`/trellis:<phase>` |
| OpenCode | TUI: `/trellis:<phase>`；CLI: `trellis/<phase>` |
| Codex | 自然语言 + 对应 skill；不提供项目级 `/trellis:<phase>` 命令目录 |

### 能力路由基线

默认遵循以下共用规则：

- 本地代码定位：优先 `ace.search_context`
- 第三方库/框架官方文档：优先 `Context7`
- 最新事实/版本/新闻：优先 live 检索
- 需求模糊：优先 `ace.enhance_prompt`
- 复杂分支推理：优先 `sequential-thinking`
- 阶段文档列出的 MCP / skills 默认视为**先调用的主能力**，不是可有可无的装饰项；只有能力不可用时才降级
- 关键能力不可用：必须显式写 `[Evidence Gap]`

### 统一对话收尾约定

每个阶段执行完后，都应在本轮回复末尾输出「下一步推荐」。

- Claude Code：优先推荐项目命令，如 `/trellis:brainstorm`
- OpenCode：优先推荐项目命令；若是在 CLI 语境，可补充 `trellis/brainstorm`
- Codex：优先推荐“自然语言意图 + 对应 skill 名”，如“继续需求澄清，或显式触发 `brainstorm` skill”
- 不要把 `/trellis:xxx` 当作 Codex 的唯一入口协议
- 用户不确定下一步时：
  - Claude / OpenCode：推荐 `/trellis:start`
  - Codex：推荐描述当前意图，或显式触发 `start` skill

### 统一阶段模板

阅读下方每个阶段时，都只抓 6 件事：

1. 这个阶段要解决什么问题
2. 三个 CLI 分别怎么进入
3. 推荐调用什么 MCP / skills
4. 没有这些能力时怎么降级
5. 满足什么门禁后才能进入下一步
6. 本轮结束时应该如何用当前 CLI 的原生入口表达“下一步推荐”

---

## 阶段 1：Feasibility

### 目标

确认项目是否合法、能不能做、值不值得做，以及是否允许进入需求发现。

### CLI 入口差异

- Claude Code：`/trellis:feasibility`
- OpenCode：TUI 用 `/trellis:feasibility`，CLI 用 `trellis/feasibility`
- Codex：自然语言描述或显式触发 `feasibility` skill

### 推荐 MCP / Skills

- `demand-risk-assessment`
- `exa_create_research`
- `deepwiki`
- `sequential-thinking`

### 典型降级方式

- 无法联网时，不输出“行业最新情况”或“最新政策”结论，改为本地已知风险清单，并标记 `[Evidence Gap]`
- 无法完成结构化风险评估时，至少保留“接 / 谈判后接 / 暂停 / 拒绝”的结论和原因

### 外部交付项目分支

外包、定制开发、新客户项目必须在这里明确：

- `delivery_control_track`
- `delivery_control_handover_trigger`
- `delivery_control_retained_scope`

内部项目通常不需要双轨交付字段，但仍要写是否允许进入 `brainstorm`。

### 退出门禁

- 形成 `assessment.md`
- 明确是否允许进入 `brainstorm`
- 若为外部项目，交付控制轨道已定

---

## 阶段 2：Brainstorm

### 目标

确认需求描述是否准确，统一做 `L0/L1/L2` 分类，并决定是否需要先补信息或拆子任务。

### CLI 入口差异

- Claude Code：`/trellis:brainstorm`
- OpenCode：TUI 用 `/trellis:brainstorm`，CLI 用 `trellis/brainstorm`
- Codex：自然语言描述或显式触发 `brainstorm` skill

### 推荐 MCP / Skills

- `brainstorm`
- `ace.enhance_prompt`
- `sequential-thinking`
- `markmap`

### 典型降级方式

- 无 `ace.enhance_prompt` 时，人工补齐“目标 / 范围 / 验收 / 边界”四项后再分类
- 无可视化工具时，用纯 markdown 列表表达“需求 → 功能 → 验收”

### 外部交付项目分支

若是外部项目，这一步要把对客户的交付边界说人话，而不只是写机器字段：

- 尾款前给什么
- 尾款前不交什么
- 变更如何计入下一轮

### 退出门禁

- 需求描述达到“已准确”
- 已完成 `L0/L1/L2` 分类
- 已决定走 `design`、`plan` 还是极小任务直进 `start`

> 通用新项目默认继续走 `design`。只有边界极小、单上下文可闭环的 `L0` 事项，才建议直接进 `start`。

---

## 阶段 3：Design

### 目标

冻结关键设计决策，补齐项目 spec 基线，并同步适配后续 `finish-work` / `record-session` 的项目化门禁。

### CLI 入口差异

- Claude Code：`/trellis:design`
- OpenCode：TUI 用 `/trellis:design`，CLI 用 `trellis/design`
- Codex：自然语言描述或显式触发 `design` skill

### 推荐 MCP / Skills

- `ace.search_context`
- `Context7`
- `doc-coauthoring`
- `architecture-patterns`
- `backend-patterns`
- `api-design-principles`

### 典型降级方式

- 没有官方文档证据时，不下 API / 框架细节结论，只保留待验证设计假设
- 没有完整架构样板时，先冻结接口/数据/错误矩阵，再补实现细节

### 外部交付项目分支

这里要显式导入和对齐外部交付基线：

- 基础必选：`delivery-control` + `transfer-checklist`
- `trial_authorization`：额外补 `authorization-management`
- 涉及正式移交密钥/配置：额外补 `secrets-and-config`

同时在这里完成：

- `/trellis:finish-work` 的首次项目化适配
- `/trellis:record-session` 的基线适配

### 退出门禁

- 关键设计文档与项目 spec 已对齐
- 自动化检查矩阵已明确
- `finish-work` / `record-session` 的项目化基线已定

---

## 阶段 4：Plan

### 目标

把冻结后的需求与设计拆成可闭环、可验证、可收尾的任务执行矩阵。

### CLI 入口差异

- Claude Code：`/trellis:plan`
- OpenCode：TUI 用 `/trellis:plan`，CLI 用 `trellis/plan`
- Codex：自然语言描述或显式触发 `plan` skill

### 推荐 MCP / Skills

- `project-planner`
- `writing-plans`
- `sequential-thinking`
- `ace.search_context`

### 典型降级方式

- 没有结构化拆解能力时，至少按“范围 / 风险 / 验收 / 依赖 / 回归”五列拆任务
- 对不确定项单独列成待补信息，不要混入已承诺任务

### 外部交付项目分支

这里必须把以下内容拆成独立任务，而不是放进一个笼统“交付”：

- 试运行版交付
- 永久授权切换
- 源码移交
- 生产权限移交
- 最终控制权移交

### 退出门禁

- `task_plan.md` 或等价执行矩阵已形成
- 每个任务都有验收与回归边界
- 已决定进入 `test-first + start`

---

## 阶段 5：Test-First + Start

### 目标

先把验收标准转成测试或最小验证门禁，再进入实现闭环。

### CLI 入口差异

- Claude Code：`/trellis:test-first` → `/trellis:start`
- OpenCode：TUI 用 `/trellis:test-first`、`/trellis:start`；CLI 用 `trellis/test-first`、`trellis/start`
- Codex：自然语言描述或显式触发 `test-first`、`start` skill

### 推荐 MCP / Skills

- `test-driven-development`
- `ace.search_context`
- `Context7`
- `coding-standards`
- `simplify`
- `karpathy-guidelines`

### 典型降级方式

- 无法先写自动化测试时，至少先写手工验证步骤与证据口径
- 无 `Context7` 时，只引用项目内既有模式或已确认官方文档
- 若不确定当前该进哪个阶段，用 `start` 作为 Phase Router 兜底

### 外部交付项目分支

通常不单独分支。除非实现内容直接触及试运行限制、授权切换、交付控制逻辑，此时应回看 `design` / `plan` 基线而不是临时拍脑袋修改。

### 退出门禁

- 已有测试门禁或等价验证计划
- 当前任务在单上下文内可闭环
- 实现完成并保留了可审查证据

---

## 阶段 6：Self-Review + Check

### 目标

先做本 CLI 的自审，再判断是否需要进入多 CLI 补充审查门禁。

### CLI 入口差异

- Claude Code：`/trellis:self-review` → `/trellis:check`
- OpenCode：TUI 用 `/trellis:self-review`、`/trellis:check`；CLI 用 `trellis/self-review`、`trellis/check`
- Codex：自然语言描述或显式触发 `self-review`、`check` skill

### 推荐 MCP / Skills

- `verification-before-completion`
- `sharp-edges`
- `multi-cli-review`
- `multi-cli-review-action`

### 典型降级方式

- 没有 reviewer skill 时，不伪造多 CLI 审查，直接记录“未执行原因 + 当前残余风险”
- 只要出现安全、跨层 contract、数据迁移、高 blast radius，就不要把 `check` 当成可有可无

### 外部交付项目分支

通常只做轻量提醒：若改动触及交付控制、授权、密钥、最终移交，审查时必须把这些边界视为高风险面。

### 退出门禁

- 自审结论已写清
- `check` 结果已明确为 `required` / `recommended` / `skip`
- 所有审查发现已修复或已留风险说明

---

## 阶段 7：Finish-Work

### 目标

在提交前用项目真实检查矩阵证明“这轮工作可以交给人测试或提交”。

### CLI 入口差异

- Claude Code：`/trellis:finish-work`
- OpenCode：TUI 用 `/trellis:finish-work`，CLI 用 `trellis/finish-work`
- Codex：自然语言描述或显式触发 `finish-work` skill

### 推荐 MCP / Skills

- `verification-before-completion`

### 典型降级方式

- 没法运行某项检查时，明确写 `not run` 和原因，不要说“应该没问题”
- 不用默认 `lint/test/build` 占位词替代真实项目检查矩阵

### 外部交付项目分支

这里只做轻量提醒：若本轮涉及交付控制文档、授权条款或移交 checklist，也应纳入提交前检查证据。

### 退出门禁

- 真实执行了本项目要求的检查
- 结果按 `pass / fail / not run` 记录
- 可以进入 `delivery`

---

## 阶段 8：Delivery

### 目标

做验收测试、交付物整理、变更日志与交付控制门禁检查。

### CLI 入口差异

- Claude Code：`/trellis:delivery`
- OpenCode：TUI 用 `/trellis:delivery`，CLI 用 `trellis/delivery`
- Codex：自然语言描述或显式触发 `delivery` skill

### 推荐 MCP / Skills

- `doc-coauthoring`
- `changelog-generator`
- `verification-before-completion`
- `requesting-code-review`

### 典型降级方式

- 没有自动 changelog 时，手工按“用户可感知变化 / 风险 / 验证结果”整理
- 没有专项交付脚本时，至少执行 checklist，而不是跳过交付门禁

### 外部交付项目分支

这是必须显式分支的阶段：

- `retained-control delivery`：交付材料，但不移交最终控制权
- `final control transfer`：只有触发条件满足后，才移交源码、永久授权、密钥、管理员权限

### 退出门禁

- 验收结果清晰
- 交付物已整理
- 若为外部项目，当前交付事件类型与允许移交范围已写清

---

## 阶段 9：Record-Session

### 目标

完成当前任务的最终收尾记录，关闭元数据闭环。

### CLI 入口差异

- Claude Code：`/trellis:record-session`
- OpenCode：TUI 用 `/trellis:record-session`，CLI 用 `trellis/record-session`
- Codex：自然语言描述或显式触发 `record-session` skill

### 推荐 MCP / Skills

- `record-session`

### 典型降级方式

- helper 或自动提交失败时，不把 session 记为完成
- 若 `.trellis/tasks`、`.trellis/.current-task`、staged 区仍脏，先处理元数据问题，不直接记录

### 外部交付项目分支

通常只做轻量提醒：若本轮完成的是交付事件任务，session 应明确记下“当前交付事件类型”和“是否已触发最终移交”。

### 退出门禁

- 当前任务已 archive 或满足项目约定的收尾前置条件
- session 已记录成功
- 元数据闭环完成

---

## 从这份文档再往下怎么走

- 要看权威规则与门禁：去 [工作流总纲](./工作流总纲.md)
- 要看阶段到命令 / skills 的映射：去 [命令映射](./命令映射.md)
- 要看外部项目双轨交付案例：去 [双轨交付控制完整流程演练](./完整流程演练.md)
- 要看具体 CLI 的原生承载方式：去 `commands/*/README.md`

# brainstorm: 新项目开发工作流多CLI原生适配与MCP/Skills增强

## Goal

分析 `docs/workflows/新项目开发工作流/` 目录下现有工作流文档，评估其对 Claude Code、Codex、OpenCode 的原生适配完整度，以及对仓库内已有 MCP 和 skills 的利用率是否充分；先完成现状盘点、缺漏分析与后续探索入口，不直接实现。

## What I already know

* 目标范围限定在 `docs/workflows/新项目开发工作流/`
* 用户要求先分析现有信息与缺漏，采用渐进性披露，而不是一次性输出完整方案
* 目录中已存在 `工作流总纲.md`、`命令映射.md`、`完整流程演练.md`、`commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md`
* `工作流总纲.md` 已写入多 CLI 原生适配、渐进性披露、能力路由基线，以及 MCP / skills 的配置边界
* `命令映射.md` 已写入阶段到命令、skills 的初步映射，以及多 CLI 同装原则
* 平台 README 已分别说明 Claude Code、OpenCode、Codex 的原生承载模型与配置边界
* 范围内各阶段命令文档大多已带 `Cross-CLI` 声明，且部分命令已写入 MCP 能力路由
* `完整流程演练.md` 当前几乎不承载多 CLI 入口差异、MCP 路由和 skills 触发说明
* `命令映射.md` 中至少存在一处技能名与当前仓库/会话资产不一致：`brainstorming`，而当前实际存在的是 `brainstorm`
* `commands/design.md` 的一处 MCP 表格存在结构异常，说明“阶段文档已写能力路由”但局部质量未完全收口
* `完整流程演练.md` 当前标题与目标都聚焦“双轨交付控制”，主链只覆盖 `feasibility -> brainstorm -> design -> plan -> delivery`
* `完整流程演练.md` 明确排除了 `/trellis:start`、`/trellis:self-review`、`/trellis:check`、`/trellis:finish-work` 的代码审查链路，只在末尾给出最小收尾样例
* `完整流程演练.md` 基本没有演练 Claude Code / OpenCode / Codex 的实际入口差异，也没有把 MCP / skills 的触发点嵌入阶段 walkthrough

## Assumptions (temporary)

* 当前主要问题不一定是“完全没有适配说明”，更可能是“已有原则未完全落到各阶段文档/演练/命令说明”
* 当前需要先识别文档层面的缺漏与不一致，再决定是否进入具体改写
* 需要把“能力该何时触发”与“平台如何挂接”继续拆开，避免主文档过重
* 本轮最有价值的缺漏可能分成三类：工作流 walkthrough 缺漏、阶段命令下沉不均匀、文档声明与真实资产不一致
* 对 `完整流程演练.md` 来说，当前更像“特定业务轨道案例”，而不是“多 CLI 原生工作流演练”

## Open Questions

* 这轮 brainstorm 是否只输出“缺漏清单 + 后续方向”，还是需要同时收敛出一个明确的改写优先级顺序？

## Requirements (evolving)

* 盘点范围内文档与命令说明文件
* 识别多 CLI 原生适配的现有覆盖面与缺口
* 识别 MCP / skills 在工作流阶段中的现有映射与遗漏
* 输出应遵循渐进性披露，先给摘要，再逐步展开
* 对 `完整流程演练.md` 的处理方向已确定为方案 C：保留专项案例，另建一份“多 CLI 原生工作流全链路演练”文档
* 新增主演练文档定位已确定为“通用新项目主链”，而不是本仓库自身开发示例
* 新增主演练文档默认同时覆盖“内部项目 + 外部交付项目”，其中外部交付作为条件分支，而不是拆成两套平行主演练
* 新增主演练文档采用中等粒度：每阶段写“CLI 入口差异 + 推荐 MCP/skills + 典型降级方式”，但不展开成三套独立操作手册
* 新增主演练文档将直接写具体工具名与回退顺序，以增强可执行性；但不写凭据、provider、MCP server 注册或平台配置细节
* 新增主演练文档文件名已确定为 `多CLI通用新项目完整流程演练.md`
* 新增主演练文档将作为 `docs/workflows/新项目开发工作流/` 下给新读者的第一推荐入口；现有 `完整流程演练.md` 退回为专项案例入口
* 本轮缺漏分析范围已扩展到：需要同步识别并更新哪些旧文档中的导航链接、推荐阅读顺序与 walkthrough 指向
* 当前偏好的链接拓扑已收敛为“新指向旧”：由新主演练文档统一分流到 `工作流总纲.md`、`命令映射.md`、`完整流程演练.md` 等旧文档
* 旧文档需要补最小反向提示：若读者从旧文档进入，应提示“首次阅读请先看 `多CLI通用新项目完整流程演练.md`”
* 旧文档的反向提示不采用统一模板，而是按文档角色微调措辞，以同时完成导流和职责重申
* 新主演练文档章节顺序采用“先讲如何阅读这套 workflow，再进入阶段主链”
* 需要为新主演练文档定义统一的“阶段章节模板”，保证各阶段同时呈现入口差异、能力路由、降级方式和门禁，而不漂移成松散案例
* 阶段合并策略已确定：`test-first + start` 合并为一个实现准备/执行大章，`self-review + check` 合并为一个实现后验证大章；`feasibility`、`brainstorm`、`design`、`plan`、`finish-work`、`delivery`、`record-session` 保持独立
* 外部交付项目分支适用范围已收敛：
  * 必须显式分支：`feasibility`、`brainstorm`、`design`、`plan`、`delivery`
  * 仅做轻量提示：`self-review + check`、`finish-work`、`record-session`
  * 通常不做 workflow 分支：`test-first + start`
* 新主演练文档开头的“如何阅读这套 workflow”应同时保留两张表：
  * 主表：阅读导航表（场景 / 先看 / 再看 / 为什么）
  * 辅表：简短文档角色表（文档 / 角色）

## Acceptance Criteria (evolving)

* [ ] 能列出范围内主要文档及其当前职责
* [ ] 能指出至少一组“已有原则”和“尚未落地位置”之间的缺口
* [ ] 能区分 Claude Code、OpenCode、Codex 的入口与承载差异
* [ ] 能给出后续 brainstorm 的 2-3 个可探索方向
* [ ] 能明确新增“主演练文档”和现有 `工作流总纲.md` / `命令映射.md` / `完整流程演练.md` 的职责边界

## Definition of Done (team quality bar)

* 分析结论基于仓库内现有文档证据
* 说明哪些内容已存在、哪些内容缺失或不一致
* 输出保持渐进性披露，不一次性铺满所有细节

## Out of Scope (explicit)

* 本轮不直接修改 `docs/workflows/新项目开发工作流/` 下文件
* 本轮不编写安装器、hooks、skills 或 agents 的实现
* 本轮不扩展到 `旧项目重构工作流`

## Technical Notes

* 任务目录：`.trellis/tasks/04-01-workflow-multi-cli-mcp-skills/`
* 首轮已检索目录文件清单
* 首轮已定位与多 CLI / MCP / skills 相关的关键文档：`工作流总纲.md`、`命令映射.md`、`commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md`
* `完整流程演练.md` 目前更偏业务 walkthrough，对 CLI 入口差异、MCP 路由、skills 复用没有形成对应演练说明
* 当前范围内命令文档已覆盖：`feasibility.md`、`brainstorm.md`、`design.md`、`plan.md`、`test-first.md`、`self-review.md`、`check.md`、`delivery.md`
* 文档声明与资产对照：
  * 本地 `skills/` 下存在：`demand-risk-assessment`、`multi-cli-review`、`multi-cli-review-action`
  * 本地 `.agents/skills/` 下存在：`brainstorm`、`start`、`finish-work`、`record-session` 等阶段技能
  * `命令映射.md` 仍引用 `brainstorming`
* walkthrough 缺漏锚点：
  * 标题和适用范围聚焦双轨交付控制，见 `完整流程演练.md` 第 1-23 行
  * 主链只覆盖到 `delivery`，见第 15-23 行
  * `brainstorm`、`design`、`plan`、`delivery` 均写了业务产物和校验，但未写多 CLI 入口差异或对应 MCP / skills 触发动作，见第 122-329 行
  * `finish-work` / `record-session` 仅以“最小收尾样例”出现，且 `/trellis:start`、`/trellis:self-review`、`/trellis:check` 仅在“后续扩展”里被列为待补，见第 377-452 行
* 用户已选择方案 C：保留 `完整流程演练.md` 作为双轨交付控制专项案例；新增一份多 CLI 原生工作流全链路演练文档
* 用户已确认新增主演练文档应按“通用新项目主链”设计
* 用户已确认新增主演练文档同时覆盖内部项目与外部交付项目，外部交付通过条件分支处理
* 用户已确认新增主演练文档采用中等粒度展开
* 用户已确认主演练文档中写具体工具名与回退顺序，但不下沉到平台配置细节
* 用户已确认新增主演练文档文件名：`多CLI通用新项目完整流程演练.md`
* 用户已确认新增主演练文档是目录内第一入口
* 用户已确认“需要”把旧文档导航与链接同步更新纳入分析范围
* 用户已确认链接拓扑优先采用“新指向旧”
* 用户已确认旧文档需要补最小反向提示
* 用户已确认反向提示按文档角色微调措辞
* 用户已确认新文档采用“如何阅读 → 阶段主链”的顺序
* 当前正在收敛新主演练文档的统一阶段模板
* 用户已确认阶段合并策略：`test-first + start` 合并，`self-review + check` 合并，其余阶段独立
* 用户已确认采用“外部交付项目分支范围”建议
* 用户已确认“如何阅读这套 workflow”一节需要保留简短文档角色表

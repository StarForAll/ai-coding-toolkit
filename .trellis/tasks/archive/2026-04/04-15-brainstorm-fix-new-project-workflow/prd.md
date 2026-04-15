# brainstorm: 修复完善新项目开发工作流

## Goal

在保持 Trellis 核心工作流主链不被破坏的前提下，修复并完善 `docs/workflows/新项目开发工作流/`，使其在设计阶段和多 CLI 原生适配层上更加一致、可执行、可验证，尤其补齐设计阶段的文档产物链、UI 原型阶段的 CLI 约束、以及面向 Stitch 的高质量提示词生成流程。

## What I already know

* 用户要求本轮先做分析和修改方案，不直接改文件。
* 修改范围限定在 `docs/workflows/新项目开发工作流/` 目录。
* 用户明确要求后续修改必须同时兼容 Claude Code / Codex / OpenCode 官方原生格式，但优先以 Trellis 框架核心为前提。
* 当前 `commands/design.md` 已经包含 `uiprompt.site -> stitch.withgoogle.com` 的外部 UI 原型链路，但缺少：
  - UI 原型阶段禁止使用 Codex 的硬性约束
  - “先生成 Stitch 适用 Prompt，再生成 UI 原型”的单独门禁
  - “去 AI 味”作为明确提示词质量要求
  - 与总纲、演练、路由、导出脚本的一致性收口
* 当前 `工作流总纲.md` 已经存在扩展设计文档体系说明，包含 `TAD / DDD / IDD / AID / ODD` 等，但和 `commands/design.md`、`design-export.py`、阶段门禁之间仍有落差。
* 当前 `commands/shell/design-export.py` 把 `BRD / TAD / DDD / IDD` 设为必需，把 `AID / ODD` 设为可选；尚未覆盖 README 使用说明，也未区分“开发人员部署文档”和“非专业人员部署文档”。
* 当前 `commands/brainstorm.md` 和 `commands/start-patch-phase-router.md` 仍主要以双 PRD / 有无设计文档来做阶段判断，没有把设计阶段新增文档集合定义为显式门禁。
* 当前 workflow 文档中已经明确：Claude / OpenCode 使用项目阶段命令；Codex 使用 `AGENTS.md + hooks + skills + subagents`，不提供项目级 `/trellis:xxx` 命令目录。

## Assumptions (temporary)

* 本轮修改应以“增强现有 workflow”而非“重写整个设计阶段”为目标。
* 为了减少返工，建议把新增规则优先沉淀到权威层和阶段命令层，再向演练文档、边界矩阵、导出脚本同步传播。
* 用户提出的“其他相关联文档”以最小充分集合落地即可，不应无限扩张文档模板数量。

## Open Questions

* 当前无阻塞问题；待输出方案后，等待用户确认是否进入实施。

## Requirements (evolving)

* 分析 `docs/workflows/新项目开发工作流/` 当前设计阶段、阶段门禁、CLI 适配层现状。
* 基于当前实现提出一个尽量小而完整的修正方案。
* 方案必须覆盖以下新增要求：
  - 技术架构确认后，除 PRD 外，明确补齐系统设计文档、数据库设计（按需）、API 接口文档（按需）、双版本部署文档、项目根 README 使用说明等。
  - UI 原型子任务阶段禁止使用 Codex 实现，强制改为 OpenCode 或 Claude Code 中更适合视觉原型的原生模型/入口。
  - design 阶段必须显式要求先从 `https://www.uiprompt.site/zh/styles` 获取风格提示词，再在 CLI 中生成高质量、去 AI 味、适合 Stitch 的最终 UI Prompt，再进入 `https://stitch.withgoogle.com/` 生成 UI 原型。
* 方案必须说明会改哪些文件、每类文件各自承担什么职责、为什么需要改。
* 方案必须尽量符合 Claude Code / OpenCode / Codex 当前官方原生入口约束。

## Acceptance Criteria (evolving)

* [ ] 明确列出当前 workflow 中与用户诉求不一致的点。
* [ ] 明确列出建议修改的文件集合及职责分工。
* [ ] 明确给出文档产物链的必选/条件可选划分。
* [ ] 明确给出 UI 原型阶段对 Claude Code / OpenCode / Codex 的差异化约束方案。
* [ ] 明确给出 Stitch Prompt 生成阶段的新增门禁与建议写法。
* [ ] 输出方案后等待用户确认，再进入实际修改。

## Definition of Done (team quality bar)

* 方案能够直接指导后续文件修改，不需要再次大范围补分析。
* 变更范围和传播范围被明确识别，避免只改单文件导致规则漂移。
* 对官方 CLI 入口的判断有文档证据支撑。

## Out of Scope (explicit)

* 本轮不直接改 workflow 文件。
* 本轮不创建或更新目标项目中的真实 `design/` 文档模板内容。
* 本轮不评估 Stitch 或 UI Prompt 网站本身的产品效果，仅评估如何把它们纳入 workflow。

## Technical Notes

* 关键本地文件：
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/commands/design.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/commands/shell/design-export.py`
* 已核对的官方入口证据：
  - Claude Code 官方文档已将 custom commands 合并进 skills；`.claude/commands/*.md` 仍可继续工作，但推荐 skills 形态。
  - OpenCode 官方文档确认项目级自定义命令位于 `.opencode/commands/*.md`，agent 可用 `opencode.json` 或 Markdown 配置。
  - Codex 官方文档确认项目级长期规则以 `AGENTS.md` 为核心，并支持 `.codex/hooks.json`、`.agents/skills` / `SKILL.md`、`.codex/agents/*.toml`、CLI built-in slash commands。

## Research Notes

### What similar tools do

* Claude Code 当前官方把“自定义命令”并入 skills，说明其推荐方向是“轻入口 + 技能化承载”，但保留 `.claude/commands/` 兼容旧资产。
* OpenCode 当前官方继续支持 `.opencode/commands/*.md` 作为项目命令入口，同时支持 agents 配置。
* Codex 当前官方把项目能力拆在 `AGENTS.md`、hooks、skills、subagents 上，而 CLI slash commands 是内建会话控制，不等于项目 workflow 命令目录。

### Constraints from our repo/project

* 当前 workflow 的主叙事已经明确三平台入口协议不同，不能把 Codex 强行写成 `/trellis:design` 式命令入口。
* 当前目录下已有权威层、映射层、平台展开层、演练层、导出脚本层；新增规则需要做跨文档传播。
* 当前仓库已经有设计文档体系雏形，因此更适合收口和补门禁，而不是重新发明一套命名体系。

### Feasible approaches here

**Approach A: 最小闭环增强** (Recommended)

* How it works:
  - 保留现有 `BRD / TAD / DDD / IDD / AID / ODD` 命名体系
  - 在 `工作流总纲 + commands/design.md` 中重新定义“必选/条件可选/派生”产物和 UI 原型阶段门禁
  - 同步更新 `brainstorm/start-patch/演练/边界矩阵/design-export.py`
* Pros:
  - 改动集中，和现有资产兼容性最好
  - 更容易做规则传播和验证
* Cons:
  - 仍要兼容既有命名，不能完全按用户新术语重新命名所有文件

**Approach B: 设计阶段全面重构**

* How it works:
  - 重写设计阶段文档结构、命令、导出脚本和演练文档
  - 以“系统设计 / API / 部署(双版本) / README”为新主命名
* Pros:
  - 用户语义更直观
* Cons:
  - 影响面过大，和当前 workflow 现有案例及脚本兼容成本高
  - 容易引入跨层漂移

**Approach C: 仅补充 design.md**

* How it works:
  - 只改 `commands/design.md` 提示话术与步骤
* Pros:
  - 成本最低
* Cons:
  - 无法解决总纲、路由、导出脚本、演练和平台 README 之间的不一致
  - 很容易再次漂移

## Decision (ADR-lite)

**Context**: 用户提出的是设计阶段和多 CLI 适配层的规则完善，不只是单一提示词修改。当前仓库相关规则散落在总纲、阶段命令、路由、演练和导出脚本中。  
**Decision**: 倾向采用 Approach A，做“最小闭环增强”，以最少的结构改动完成规则收口和跨文档传播。  
**Consequences**: 后续实施时需要同时更新多份文档和一个脚本，但风险低于全面重构，也能避免只改单点导致的二次漂移。

## Point A Focus

### Point A 的核心问题

当前 workflow 对“技术架构确认后到底必须补齐哪些项目文档”定义不够清晰，主要表现为：

* 文档集合虽已有雏形，但没有形成稳定的“必选 / 条件可选 / 派生补充”矩阵。
* `design` 阶段命令、总纲、导出脚本之间的强制性不一致。
* 文档名存在，但每份文档至少要覆盖哪些关键内容没有统一门禁。
* 缺少“项目根 README 也是交付文档”的明确定位。
* “部署文档”当前只有单一 `ODD.md` 概念，未拆成面向开发者与非专业人员的双版本。

### Point A 建议收口方式

以“项目级正式需求文档 + 设计阶段交付文档”两层来定义。

#### 已在前置阶段完成的正式需求文档

* `docs/requirements/customer-facing-prd.md`
* `docs/requirements/developer-facing-prd.md`

#### 技术架构确认后进入 design 阶段的文档产物

**必选**

* `design/TAD.md`
  * 系统架构图
  * 技术栈与版本
  * 模块边界与职责
  * 核心流程/数据流
  * 部署架构
  * 安全与风险
* `design/ODD-dev.md`
  * 开发/运维人员部署准备
  * 环境变量与依赖
  * 本地/测试/生产部署步骤
  * 回滚、排障、监控入口
* `design/ODD-user.md`
  * 面向非专业人员的部署/交付使用说明
  * 如何启动/访问
  * 账号、权限、初始化信息
  * 常见问题、交付边界、联系/升级路径
* 项目根 `README.md`
  * 项目定位
  * 技术栈
  * 目录说明
  * 启动方式
  * 文档索引
  * 部署与使用说明入口

**条件必选**

* `design/DDD.md`
  * 触发条件：涉及数据库、持久化、缓存数据模型、迁移、数据字典
* `design/IDD.md`
  * 触发条件：涉及后端 API、前后端接口契约、第三方集成接口、Webhook
* `design/AID.md`
  * 触发条件：涉及 AI/LLM、Prompt、上下文策略、评估、回退
* `design/specs/<module>.md`
  * 触发条件：复杂模块需要单独规格说明
* `design/pages/<page>.md`
  * 触发条件：存在前端页面或交互页面

**建议新增的派生产物**

* `design/STITCH-PROMPT.md`
  * 触发条件：涉及页面视觉原型
  * 用于沉淀从 PRD/设计约束整理出的最终 Stitch 可用 Prompt

### Point A 实施时的门禁原则

* 进入 `plan` 前，不要求所有条件文档都存在，但要求：
  * 必选文档已存在
  * 条件文档已按项目是否涉及被明确判定
  * README 已更新到可供协作者使用的最低程度
* `design-export.py` 第一版只做：
  * 必选文档强校验
  * 条件文档提示校验
  * 不把业务判断逻辑写得过重

### Point A 已确认决策

* 不单独新增 `BRD.md`
* `docs/requirements/customer-facing-prd.md` 直接承担 BRD 主文档职责
* `design/` 目录下不再把 `BRD.md` 作为设计阶段硬必选产物
* `docs/requirements/developer-facing-prd.md` 只保留需求实现说明，不承载接口正文或数据库正文
* 若需要接口信息、数据结构信息，只在 `developer-facing-prd.md` 中保留跳转链接，正文下沉到 `design/IDD.md`、`design/DDD.md` 等专项文档
* `DDD.md`、`IDD.md` 采用“条件必选”规则，但判断时机必须前置到技术架构确认后的 design 阶段
* 在 design 阶段完成 `TAD` 时，必须同时判断是否涉及数据库设计 / API 契约；若判断涉及，则在同一阶段直接创建并细化 `DDD.md`、`IDD.md`，不能拖到实现阶段再补
* `ODD` 直接拆分为两个独立文件：`design/ODD-dev.md`、`design/ODD-user.md`
* 允许两份 `ODD` 之间存在必要的重复内容，不强制为了“避免重复”而合并成单文件或过度抽象
* `README.md` 在 design 阶段只要求“最低可用版”：
  * 项目简介
  * 技术栈
  * 目录结构
  * 文档索引
  * 启动方式占位
  * 部署/使用文档链接
* 项目完成之后，再补充成“接近可交付版” README：
  * 安装
  * 运行
  * 构建
  * 部署入口
  * 常见问题

## Point B Focus

### Point B 的核心问题

当前 workflow 已经区分了三类 CLI 的原生入口协议，但没有定义“UI 原型执行器”的平台约束：

* `design` 阶段默认对 Claude Code / OpenCode / Codex 都给出了阶段入口，只区分触发协议，不区分视觉原型能力边界。
* 当前文档只强调“需要离开 CLI 去外部设计站点”，没有规定在“生成 UI 代码原型 / 视觉原型”这个子任务阶段，哪些 CLI 可以作为主执行器，哪些不可以。
* 如果不增加硬约束，Codex 侧仍会被理解为可以参与整个 `design` 子任务，只是入口换成 skill，这和用户要求不一致。

### Point B 建议收口方式

将 design 阶段拆成两个不同能力域：

* **设计说明与技术设计域**
  * 三类 CLI 都可参与
  * 包括：需求转设计、技术方案、文档沉淀、Prompt 草案整理、原型结果回收
* **UI 视觉原型执行域**
  * 明确禁止 Codex 作为执行器
  * 强制要求使用 Claude Code 或 OpenCode 中具备原生视觉能力、适合视觉原型生成的模型/入口
  * 外部原型站点仍按 `uiprompt.site -> Stitch` 主链执行

### Point B 当前建议规则

* Codex **可以**参与：
  * 设计文档整理
  * Stitch Prompt 文本润色
  * 原型结果回收与结构化沉淀
* Codex **不可以**参与：
  * 直接承担 UI 视觉原型生成主执行器
  * 在该子任务阶段输出“用 Codex 继续完成 UI 页面原型/视觉稿/原型代码”的推荐
  * 在代码实现初始任务中承担“把 UI 原型/设计稿转换成首版代码界面”的主执行器
* Claude Code / OpenCode 在 UI 视觉原型子任务阶段应被标记为唯一允许的 CLI 主执行入口
* Claude Code / OpenCode 在“UI -> 首版代码界面”的初始前端落地任务中，也应被标记为唯一允许的 CLI 主执行入口

### Point B 待确认边界

* 已确认：Codex 仅禁止前端视觉落地链路的前两步：
  * UI 原型生成
  * UI -> 首版代码界面
* 后续前端视觉微调、样式修复、非首版视觉修改不强制禁用 Codex
* 但在“UI -> 首版代码界面”任务完成时，必须同步沉淀一份全局统一的视觉 / 前端实现 spec，作为后续任意 CLI 修改前端时的统一约束来源，避免样式与效果漂移
* 全局统一视觉 / 前端实现 spec 默认采用单文档模式即可
* 仅当页面复杂度明显升高时，才允许补充 `design/pages/*.md` 级别的页面实现规范

## Point C Focus

### Point C 的核心问题

当前 workflow 虽然已经写了 `uiprompt.site -> Stitch` 的链路，但还没有把“Stitch Prompt”定义为一个稳定中间产物：

* 当前更多是提醒用户去外部站点操作，而不是先在 CLI 内生成一份高质量、结构固定、可复用的最终 Prompt。
* 没有固定骨架模板，容易导致不同执行者每次都临时组织 Prompt，返工率高。
* “去 AI 味”“尽量贴近主题”“适合 Stitch”这些要求目前没有被拆成可执行字段。

### Point C 已确认决策

* workflow 必须提供一套固定骨架模板，用于生成 Stitch 最终 Prompt
* 用户先去 `https://www.uiprompt.site/zh/styles` 选择风格提示词
* 再由当前 CLI 按固定模板，把项目需求 + 风格词整合成最终可投喂 `https://stitch.withgoogle.com/` 的 Prompt
* 基于 Stitch 官方/准官方建议，Prompt 组织方式不采用“整站一次性大 Prompt”，而采用“两层结构”：
  * 项目级总上下文 Prompt
  * 面向 Stitch 执行的单页面 / 单流程 Prompt
* 默认采用单文件模式：`design/STITCH-PROMPT.md`
* 该文件同时承载：
  * 项目级总上下文 Prompt
  * 每个页面 / 流程的执行 Prompt 小节
* 仅当页面复杂度明显升高时，才允许补充页面级文件承载单页 Prompt
* “去 AI 味”采用强约束规则，不只写抽象要求，而是要在模板里明确列出反例禁止项
* 反例禁止项采用固定全局基线：
  * 每个项目默认都带同一组禁止项
  * 项目级只允许在此基础上增补，不允许删除全局基线项

# brainstorm: 强化新项目开发工作流中的 MCP 与 skills 使用

## Goal

补强 `docs/workflows/新项目开发工作流/` 中对 MCP 与 skills 的使用与配置指导，使这套 workflow 在多 CLI 原生适配场景下，不仅明确“什么场景优先用什么工具”，还明确“这些能力应该配置在哪一层、由什么文件承载、哪些属于项目基线、哪些属于 CLI 私有配置、失败时如何降级”，并与当前项目正在使用的全局提示词规则保持一致。

## What I already know

* 目标目录当前已经明确多 CLI 同装叙事，且对 Codex 的入口模型有清晰说明：Codex 主要通过 `AGENTS.md + hooks + skills + subagents` 承载，而不是项目级 `/trellis:xxx` 命令。
* `docs/workflows/新项目开发工作流/命令映射.md` 已有“阶段 → 命令 → Skills”映射，但几乎没有把 MCP 路由写成阶段化操作规则。
* `docs/workflows/新项目开发工作流/commands/codex/README.md` 已强调 Codex 使用 skills 作为 workflow 入口，但尚未把“什么时候优先用哪类 MCP / skill”沉淀成统一规范。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 已有“证据优先”“先调研再实现”的方法论表述，但仍停留在原则层，没有细化到具体 MCP / skill 选择策略。
* 当前会话里的全局规则已明确以下关键点：
  - 代码相关定位与上下文读取优先 `ace.search_context`
  - 第三方库 / SDK / 框架问题优先 `context7.resolve-library-id -> context7.query-docs`
  - 最新信息、版本、新闻、今天/本周类问题必须走 live web retrieval
  - 网络检索优先级为 `grok-search > exa-pool > 内置 Web tools`
  - 浏览器交互类任务应使用 `agent-browser` skill
  - 若关键能力不可用，必须显式标注 `[Evidence Gap]` 并说明降级路径
* 现有 workflow 文档已能说明部分承载层，但不足以说明配置责任边界：
  - Codex：`AGENTS.md` + `.codex/config.toml` + `.codex/hooks.json` + `.agents/skills/` + `.codex/agents/`
  - OpenCode：`.opencode/commands/trellis/` + `.opencode/agents/` + `AGENTS.md` + `opencode.json.instructions`
  - Claude：`.claude/commands/trellis/` + `.claude/hooks/` + `.claude/settings.json/.claude/settings.local.json` + `AGENTS.md`
* 现有文档更偏“入口说明”，例如命令、hooks、skills、agents 放在哪里；但对于 MCP/skills 的配置层级仍缺：
  - 哪些规则应该进 `AGENTS.md`
  - 哪些属于 CLI 的原生配置文件
  - 哪些属于 workflow 文档注入层
  - 哪些能力只作为 skill 组织，不应硬写进命令正文
  - 哪些属于运行时验证与降级策略

## Assumptions (temporary)

* 本次工作的主目标是更新 workflow 文档与阶段命令文案，不一定要同步修改安装脚本或运行时代码。
* 需要加强的重点已经从“使用规则”升级为“配置规范 + 使用规则”两层设计。
* 新规则应同时服务 Claude Code / OpenCode / Codex 的共存场景，不应把 Codex 的 skill 入口模型误写成全平台统一入口。
* MCP / skill 的配置规范应优先回答“放哪一层、为何放这里”，而不是直接罗列所有可用工具。

## Open Questions

* 本次范围只做到“配置规范与文档指引”，还是要进一步补到各 CLI 的可复制配置示例片段？

## Requirements (evolving)

* 把 MCP / skills 使用规则整理成 workflow 内的统一策略，而不是散落在单个平台说明里。
* 把 MCP / skills 的配置责任边界整理成 workflow 内的统一策略，而不是只写“推荐使用”。
* 规则必须覆盖至少这些场景：
  - 最新信息获取
  - 第三方官方文档查询
  - 本地代码上下文定位
  - 浏览器操作 / 页面交互
  - 复杂多步分析与证据缺口处理
* 规则必须体现优先级、适用场景、配置层级、失败降级与禁止做法。
* 规则需要嵌入到新项目开发工作流的合适层级，避免只有总纲有原则、阶段命令无法执行，也避免平台 README 与主 workflow 脱节。
* 规则应和当前全局提示词保持一致，避免 workflow 文档与真实执行策略冲突。

## Acceptance Criteria (evolving)

* [ ] workflow 文档中明确写出 MCP / skills 的工具路由原则，而不是只说“先调研”
* [ ] workflow 文档中明确写出 MCP / skills 的配置层级与责任边界
* [ ] 至少定义 `grok-search > exa > 内置 Web tools` 的检索优先级及其适用场景
* [ ] 至少定义 `agent-browser` 在浏览器操作类任务中的默认位置
* [ ] 至少定义 `ace.search_context` 与 `context7` 的触发条件
* [ ] 至少定义关键能力不可用时的 `[Evidence Gap]` 处理口径
* [ ] 最终改动后的工作流结构中，读者能知道这些规则应该在哪个阶段执行、又该在哪个配置层落地，而不只是知道“存在这些工具”

## Definition of Done (team quality bar)

* 文档结构清晰，规则不与现有多 CLI 叙事冲突
* 引导语是可执行的，不是泛泛建议
* 相关映射文档、阶段文档、平台适配说明在配置边界上保持一致
* 如有新增规范基线，需给出后续可能需要同步的文件范围

## Out of Scope (explicit)

* 本次不新增 MCP server、本地插件或 skill 实现
* 本次不设计新的 workflow 阶段
* 本次不默认改动项目根级全局提示词本身

## Technical Notes

* 已检查文件：
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/feasibility.md`
  - `docs/workflows/新项目开发工作流/commands/plan.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* 当前缺口：
  - 有“skills 映射”，但缺“按任务类型选用 MCP / skills”的执行规则
  - 有“证据优先”口号，但缺“最新信息 / 官方文档 / 浏览器操作 / 代码定位”的标准路由
  - 有入口承载说明，但缺“配置应放在 AGENTS / CLI config / hooks / instructions / skills / agents 哪一层”的统一规范
  - 有平台适配 README，但缺跨阶段统一规则，也缺跨 CLI 统一配置口径

## Research Notes

### Constraints from our repo/project

* workflow 当前是“多 CLI 同装 + 不同入口协议”的结构，新增规则不能默认所有 CLI 都共享同一触发方式。
* Codex 的表达必须兼容 skill 入口，不应把项目级 slash command 当作 Codex 主叙事。
* 文档应优先把规则放在 workflow 层，而不是散落在某个工具 README 里。

### Feasible approaches here

**Approach A: 总纲 + 映射层补强**

* How it works:
  - 只在 `工作流总纲.md` 和 `命令映射.md` 新增统一的 MCP / skills 路由与配置章节
* Pros:
  - 改动面最小
  - 规则集中，便于维护
* Cons:
  - 阶段命令文档仍可能缺少可执行指引
  - 平台配置责任边界可能仍不够具体
  - 使用者在具体阶段里不一定会主动回看总纲

**Approach B: 总纲定总规则 + 关键阶段嵌入执行指引** 

* How it works:
  - 在 `工作流总纲.md` 定义统一工具路由原则与配置分层
  - 在 `命令映射.md` 增加“阶段 × 场景 × 工具”映射，并补“配置层 × 责任边界”表
  - 在高频阶段文档里嵌入简短但可执行的调用规则，如 `feasibility`、`brainstorm`、`design`、`plan`、`start`、`check`
* Pros:
  - 既有统一原则，也有阶段落点
  - 能同时覆盖“怎么选工具”和“怎么挂配置”
  - 最接近“实际会被执行”的文档形态
* Cons:
  - 需要维护多个文件的一致性

**Approach C: 文档 + 平台 README + 配置示例全面同步** (Recommended)

* How it works:
  - 在 Approach B 基础上，再同步 `commands/codex/README.md`、`commands/opencode/README.md`，并补每个 CLI 的建议配置片段或配置矩阵
* Pros:
  - 平台叙事与 workflow 主文档完全一致
  - 后续安装/适配说明更闭环
  - 最能回答“现在需要清楚如何进行 MCP / skill 的使用配置”
* Cons:
  - 改动范围最大
  - 本次若只想先定规范，可能超出 MVP

## Decision (ADR-lite)

**Context**: 现有 workflow 已有多 CLI 与 skills 叙事，但尚未把 MCP 与 skills 的使用规则沉淀为统一、可执行、可降级的工作流规范。

**Decision**: 初步倾向 `Approach C`，因为用户新增要求已经从“增强使用规则”升级为“写清多 CLI 下的 MCP / skill 配置方式”。

**Consequences**:

* 若选 A，交付更快，但阶段可执行性偏弱。
* 若选 B，能建立实际可用的主规范，成本适中。
* 若选 C，一次性最完整，但会扩大修改面并提高一致性维护成本。

# brainstorm: 分析新项目开发工作流多 CLI 支持

## Goal

分析 `./docs/workflows/新项目开发工作流/` 这套工作流对多 AI CLI 的支持是否达到要求，重点评估 Claude Code、Codex、OpenCode 三类 CLI 的适配完整度、能力边界、落地可执行性，以及与官方文档和真实使用方式之间是否存在偏差。

## What I already know

* 目标目录已经存在完整工作流文档：`工作流总纲.md`、`命令映射.md`、`完整流程演练.md`、`commands/*.md`
* 仓库内已经有面向多 CLI 的适配说明：
* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md`
* `docs/workflows/新项目开发工作流/commands/cursor/README.md`
* 现有文档对多 CLI 的表述分层是：
* Claude Code / Cursor 记为较完整支持
* OpenCode / Codex/Gemini 多处仅记为“基础”或“⚠️”
* `命令映射.md` 已把 `check` 等环节设计为多 CLI 补充审查门禁，说明作者预期存在跨 CLI 协同链路
* `工作流总纲.md` 的主目标是流程正确性、证据门禁与测试先行，不只是命令分发

## Assumptions (temporary)

* 这次任务当前以“分析与建议”为主，不默认直接修改工作流文档
* “达到要求”需要从三个层面同时判断：
* 官方支持能力是否真实存在
* 当前 workflow 的落地方式是否与该 CLI 的真实交互模型匹配
* 当前文档中的“支持级别”是否表达准确、不会误导后续使用者
* 对 Codex 的判断必须基于当前 OpenAI 官方文档，而不能沿用历史印象

## Open Questions

* 无。当前阶段先输出正式分析报告、文档修订清单与子任务拆分，不直接实施文档改写。

## Requirements (evolving)

* 盘点 `./docs/workflows/新项目开发工作流/` 中所有与多 CLI 支持相关的设计与声明
* 对 Claude Code、Codex、OpenCode 分别建立“官方能力模型”
* 对比当前 workflow 的嵌入方式、命令机制、上下文注入方式、脚本调用方式是否匹配各 CLI
* 识别文档中“真实支持 / 变通支持 / 假定支持 / 已过时”的边界
* 给出面向这三个 CLI 的差距分析和改进建议
* 生成可直接执行的文档修订清单
* 将后续修订拆成独立子任务，至少区分 OpenCode 与 Codex 的原生适配工作

## Acceptance Criteria (evolving)

* [x] 能明确指出当前 workflow 中与 Claude Code、Codex、OpenCode 适配相关的关键文件与关键声明
* [x] 每个 CLI 都有对应的官方文档证据或官方仓库证据支撑分析结论
* [x] 每个 CLI 都有“现状判断 + 主要差距 + 是否达到要求 + 建议动作”
* [x] 结论能区分“理论可做”与“当前仓库方案已可靠支持”
* [x] 形成按文件组织的修订清单
* [x] 完成父任务到子任务的拆分，避免 OpenCode/Codex 适配混写

## Definition of Done (team quality bar)

* 结论基于仓库证据与官方文档，不靠记忆推断
* 对时效性强的 CLI 能力说明给出具体来源
* 分析结果可直接作为后续修订 workflow 文档的输入
* 后续实现任务的边界已拆清，不把 OpenCode 与 Codex 适配混在同一子任务

## Out of Scope (explicit)

* 直接实现新的 CLI 适配脚本或命令安装器
* 泛化到 Cursor、Gemini、iFlow 等所有平台的完整评估
* 对每个 CLI 做实际端到端交互自动化验证

## Technical Notes

* 当前已发现的仓库内关键文件：
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `docs/workflows/新项目开发工作流/命令映射.md`
* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md`
* `docs/workflows/自定义工作流制作规范.md`

## Research Notes

### What similar tools officially support

* Claude Code 官方文档明确支持：
* 项目级和用户级自定义 slash commands，位置是 `.claude/commands/` 与 `~/.claude/commands/`
* 自定义 subagents，位置是 `.claude/agents/` 与 `~/.claude/agents/`
* hooks 生命周期扩展，支持 `PreToolUse`、`PostToolUse`、`SessionStart`、`Stop` 等
* OpenAI Codex 官方文档明确支持：
* Codex CLI 原生 slash commands，包含 `/plan`、`/agent`、`/review`、`/model`、`/status`、`/init` 等
* `AGENTS.md` 指令链，支持 `AGENTS.override.md`、目录级叠加、fallback filenames
* hooks、skills、subagents 都是官方一等能力
* OpenCode 官方文档明确支持：
* `.opencode/commands/` 或 `opencode.json.command` 定义自定义 slash commands
* `opencode.json.instructions` 与 `AGENTS.md` 共同作为规则来源
* 原生 agents / subagents / permissions / task permissions
* 原生 skills，且兼容 `.agents/skills/` 与 `.claude/skills/`

### Constraints from our repo/project

* 当前工作流资产以 Claude Code 风格命令为主定义，再尝试为其他 CLI 写适配 README
* `docs/workflows/新项目开发工作流/commands/opencode/README.md` 仍写着“OpenCode 的命令系统尚在开发中（TBD）”，这与当前官方文档不一致
* `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md` 仍把 Codex 归类为“没有统一的命令扩展机制”，这与当前官方文档不一致
* 仓库的这套 workflow 不只是“提示词套壳”，还依赖多 CLI 审查门禁、skills、命令路由和阶段切换

### Feasible approaches here

**Approach A: 纠正文档定位，分层声明真实支持级别**（Recommended）

* How it works:
* Claude Code 标注为“原生完整支持”
* OpenCode 标注为“现已具备原生命令/agents/skills 支持，但本仓库适配尚未升级”
* Codex 标注为“现已具备原生命令/AGENTS/hooks/skills/subagents 支持，但当前 workflow 仍未按官方能力重写适配层”
* Pros:
* 不夸大现状，也不继续保留过时判断
* 能把“CLI 能力已支持”与“本仓库还没用好”分开
* Cons:
* 需要同步修改多处 README / 兼容矩阵 / 命令映射措辞

**Approach B: 继续保守表述，只保留脚本兼容层**

* How it works:
* 不承认 OpenCode / Codex 的原生能力，只继续把它们视为“脚本调用 + 上下文注入”
* Pros:
* 改动少
* Cons:
* 与当前官方文档不符，容易误导后续设计
* 会让 workflow 的跨 CLI 设计停留在低配兼容模式

**Approach C: 直接把三套 CLI 都重构成原生适配架构**

* How it works:
* Claude 用 `.claude/commands/`
* OpenCode 用 `.opencode/commands/` + `agent` / `permission`
* Codex 用技能、AGENTS、hooks、内建 slash command 协调，而不是伪装成不存在命令能力
* Pros:
* 能把 workflow 从“文档适配”升级成“平台原生适配”
* Cons:
* 范围大，已经超出这次纯分析任务

## Technical Approach

先做“文档真相校正”，再做“平台原生化拆分”。

第一层只修正文档中的事实错误与支持级别：
* 统一把 Claude Code 标记为原生完整支持
* 统一把 OpenCode 改写为“具备原生命令 / agents / rules / skills，但存在 hook/subagent 注入限制”
* 统一把 Codex 改写为“具备 AGENTS / hooks / skills / subagents 与内建 slash commands，但 workflow 应按其原生承载模型设计”

第二层再按平台拆文档：
* OpenCode 独立维护原生适配说明
* Codex 独立维护原生适配说明，不再与 Gemini 混写
* 共用文档只保留兼容矩阵、总原则与链接，不塞平台细节

## Decision (ADR-lite)

**Context**: 当前 workflow 文档把 OpenCode 与 Codex 统一写成弱兼容平台，已与官方文档和仓库现有实践不一致。

**Decision**: 采用“共享文档修正 + 平台专属适配拆分”的结构。父层文档修正兼容矩阵与术语；OpenCode 和 Codex 分别拆成独立子任务与独立适配说明。

**Consequences**:
* 优点：兼容矩阵更真实，后续维护不会再把平台差异揉成一句“⚠️ 基础”
* 代价：需要同时修改总纲类文档和平台专属 README，且 Codex/Gemini 适配文档要拆分

## Document Revision Checklist

### Shared documents

* `docs/workflows/自定义工作流制作规范.md`
  * 重写“条件 9：跨 CLI 兼容”矩阵
  * 去掉 `OpenCode = instructions + Python 脚本` 的过时表述
  * 去掉 `Codex/Gemini = Python 脚本 + Markdown 上下文注入` 的笼统表述
  * 改成“Claude / OpenCode / Codex / Gemini”分列，而不是把 Codex 和 Gemini 合并
* `docs/workflows/新项目开发工作流/命令映射.md`
  * 更新文件结构说明中的平台适配文件命名
  * 更新多 CLI 能力前提描述，区分 reviewer CLI 的原生能力边界
  * 明确 OpenCode/Codex 的参与方式不相同
* `docs/workflows/新项目开发工作流/commands/*.md`
  * 逐个审查 `Cross-CLI` 行
  * 不再统一使用“⚠️ OpenCode · ⚠️ Codex/Gemini”模板
  * 至少改成“OpenCode 原生支持但当前适配待升级 / Codex 原生能力强但承载模型不同”

### OpenCode-specific documents

* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * 从“instructions 降级适配”改写为“原生命令/agents/rules/skills 适配”
  * 单独写清 `instructions` 只是 rules 来源之一，不是唯一机制
  * 补充 `.opencode/commands/`、`.opencode/agents/`、permissions、skills 的映射
  * 明确记录 hook/subagent 注入限制，避免把 OpenCode 描写成与 Claude 完全等价

### Codex-specific documents

* `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md`
  * 拆分为 Codex 与 Gemini 两份文档
  * Codex 部分改写为 `AGENTS.md + hooks + skills + subagents + built-in slash commands` 模型
  * 删除“没有统一的命令扩展机制”这类过时结论
  * 明确区分“Codex 有原生命令能力”与“当前 workflow 不宜直接照搬 Claude 命令分发模型”

## Implementation Plan (small PRs)

* PR1: 修订共享兼容矩阵与 Cross-CLI 表述，统一术语与支持级别
* PR2: 重写 OpenCode 原生适配说明，并回填 OpenCode 的真实能力边界
* PR3: 拆分并重写 Codex 原生适配说明，剥离 Gemini 混写内容

## Subtask Decomposition

* 子任务 1：`03-31-revise-workflow-cross-cli-matrix`
  * 负责共享文档：兼容矩阵、术语、Cross-CLI 标签、命令映射
* 子任务 2：`03-31-revise-workflow-opencode-native-adapter`
  * 负责 OpenCode 原生适配文档与相关引用修订
* 子任务 3：`03-31-revise-workflow-codex-native-adapter`
  * 负责 Codex 原生适配文档拆分与重写，不与 Gemini 混做


## Subtask Completion Rollup

### 03-31-revise-workflow-cross-cli-matrix

* Completion: 已在当前工作区落地，子任务元数据尚未单独收口。
* Landed files:
* `docs/workflows/自定义工作流制作规范.md`
* `docs/workflows/新项目开发工作流/命令映射.md`
* `docs/workflows/新项目开发工作流/commands/brainstorm.md`
* `docs/workflows/新项目开发工作流/commands/check.md`
* `docs/workflows/新项目开发工作流/commands/delivery.md`
* `docs/workflows/新项目开发工作流/commands/design.md`
* `docs/workflows/新项目开发工作流/commands/feasibility.md`
* `docs/workflows/新项目开发工作流/commands/plan.md`
* `docs/workflows/新项目开发工作流/commands/self-review.md`
* `docs/workflows/新项目开发工作流/commands/test-first.md`
* Outcome: 共享矩阵已拆分 Codex 与 Gemini；主命令 `Cross-CLI` 行已从旧模板改为指向 `opencode/README.md`、`codex/README.md`、`gemini/README.md` 的真实口径。
* Verification: 已通过 `rg` 检索确认共享文档中不再残留 `Codex/Gemini`、`⚠️ 基础`、`当前文档适配待升级`、`当前承载方式待独立适配` 等旧表述。

### 03-31-revise-workflow-opencode-native-adapter

* Completion: 已在当前工作区落地，子任务元数据尚未单独收口。
* Landed files:
* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* Outcome: 文档已从 `instructions` 降级兼容说明改写为 OpenCode 原生命令 / rules / agents / skills 适配说明，并明确了与 Claude 在 hook / subagent 注入链路上的差异。
* Verification Evidence:
* `/tmp/opencode-workflow-smoke/run-report.md` 存在
* 当前 README 已包含 `/tmp` 最小验证建议与已知限制
* Boundary: 本轮只改文档，不改 OpenCode 插件、hook 或 agents 实现。

### 03-31-revise-workflow-codex-native-adapter

* Completion: 已在当前工作区落地，并已在子任务 PRD 中写入交接状态；子任务元数据尚未单独收口。
* Landed files:
* `docs/workflows/新项目开发工作流/commands/codex/README.md`
* `docs/workflows/新项目开发工作流/commands/gemini/README.md`
* `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md`
* Outcome: Codex 与 Gemini 已拆分；Codex README 已改写为 `AGENTS.md + hooks + skills + subagents + built-in slash commands` 模型，过渡 README 只保留跳转说明。
* Verification Evidence:
* `/tmp/codex-workflow-smoke/run-report.md` 存在
* `/tmp/opencode-workflow-smoke/run-report.md` 存在
* 子任务 PRD 已记录 `codex exec` 非交互 smoke 结论、`AGENTS.md` 加载验证、`SessionStart` hook 文件协议验证
* Boundary: 本轮只改文档与任务上下文，不改 Codex hooks 或 skills 代码。

### Parent-Task Interpretation

* 三个子任务的文档改动都已实际落在当前工作区，可作为父任务结论输入。
* 仍未完成的是子任务级 `task.json` 状态收口、人工测试后 commit、以及 `$record-session`。
* 因此父任务当前应理解为：分析结论 + 文档修订已基本成型，但任务元数据与会话记录尚未全部闭环。

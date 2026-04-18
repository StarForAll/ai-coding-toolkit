# brainstorm: 提升新项目工作流对 trellis 原生能力的使用

## Goal

在 `/tmp` 创建两个临时项目，分别作为纯净 Trellis 基线和嵌入当前 `docs/workflows/新项目开发工作流` 后的期望状态；基于脚本结果与对临时项目目录的直接检查，识别当前 workflow 相比 Trellis 原生能力缺失了哪些能力与承载链路，并提出仅修改 `docs/workflows/新项目开发工作流` 范围内的兼容性修复方案。

## What I already know

* 用户要求先做分析与方案，不直接实施兼容性修复。
* 分析必须同时包含脚本判断和对 `/tmp` 临时项目 A/B 的直接检查。
* 修复范围必须限制在 `docs/workflows/新项目开发工作流` 内，并显式避免数据漂移。
* 用户已明确：`parallel/worktree` 能力不需要，后续只讨论 `dispatch / plan agent` 在当前 workflow 中是否仍有必要。
* `docs/workflows/新项目开发工作流/命令映射.md` 已要求维护 workflow 源内容时先在 `/tmp` 执行 `trellis init` 获取纯净基线，再对照 workflow 源资产。
* `docs/workflows/新项目开发工作流/commands/install-workflow.py` 明确当前 workflow 是“嵌入 + 增强”模型，不会重建 Trellis 原生命令全集。
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 当前仅声明部分 patch/overlay/additional commands、shared docs 和 helper scripts 的托管集合。
* 已创建 A=`/tmp/trellis-native-a-HqweO8`、B=`/tmp/trellis-native-b-qDy6wp` 两个临时项目，并在两者上执行 `trellis init --claude --opencode --codex -y -u xzc`。
* 已在 B 上执行 `docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-native-b-qDy6wp`。
* 目录级对比显示：B 保留了 Trellis 原生 `.claude/agents`、`.claude/hooks`、`.opencode/agents`、`.codex/agents`、`.codex/hooks`、`.codex/config.toml`，这些目录/文件与 A 相同。
* `analyze-upgrade.py` 只覆盖 55 个 workflow 托管资产，未覆盖原生 hooks / agents / config 这一类能力承载层。
* B 显式禁用了 `parallel/worktree` 能力；Claude 和 Codex 侧都把 `parallel` 改写成 disabled 说明。
* B 的 `start` 主链仍然显式依赖 `research -> implement -> check` 子代理调用与 hook 注入，但当前 workflow 文档把多处原生 hooks / agents / config 仍标成“手动维护”。
* A/B 实际存在 `dispatch` / `plan` 原生 agents，但当前 workflow 边界文档只显式列举 `research / implement / check / debug`。

## Assumptions (temporary)

* 当前环境中的 `trellis` CLI 可直接在 `/tmp` 初始化空白项目。
* workflow 的安装入口为 `docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root <target>`.
* 对“缺失原生能力”的判断，不仅包含命令文件缺失，也包含 hooks、skills、agents、AGENTS 注入块、文档链路与使用路径缺失。

## Open Questions

* 当前 workflow 相较纯净 Trellis 基线，缺失项主要集中在“未接入/未托管/被禁用”的哪些层级？
* 哪些缺失项应该通过文档/映射修复，哪些应该通过安装器校验或资产枚举扩展修复？
* 对 hooks / agents / config 这类 Trellis 原生承载层，应定义成“前置能力校验”还是“纳入 workflow 托管集合”？

## Requirements (evolving)

* 在 `/tmp` 创建项目 A，并执行 `trellis init` 形成纯净基线。
* 在 `/tmp` 创建项目 B，并执行 `trellis init` 后嵌入当前 workflow。
* 对项目 A/B 同时做脚本对照和目录级人工检查。
* 输出缺失的 Trellis 原生能力清单，并按“能力类型 / 当前现状 / 风险 / 建议修复点”归类。
* 给出仅限 `docs/workflows/新项目开发工作流` 范围内的修复方案，不直接动手修复。

## Acceptance Criteria (evolving)

* [ ] 能提供项目 A/B 的实际创建与初始化证据。
* [ ] 能给出脚本分析结果与人工目录检查结果，两者互相印证。
* [ ] 能明确列出项目 B 相比纯净 Trellis 原生能力的缺失项。
* [ ] 能给出修复方案，并说明修改文件范围、同步点和防漂移措施。

## Definition of Done (team quality bar)

* 分析结论有真实文件/脚本证据支撑
* 不在未获用户确认前实施兼容性修复
* 方案明确限定改动范围在 `docs/workflows/新项目开发工作流`
* 识别潜在数据漂移点并给出同步策略

## Out of Scope (explicit)

* 直接修改 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 当前仓库内的已部署副本
* 未经用户确认直接实施 workflow 兼容性修复
* 目标项目业务代码层面的改动

## Technical Notes

* 关键文档：
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
* 关键脚本：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* 关键约束：
  * 纯净 Trellis 基线必须来自 `/tmp` + `trellis init`
  * 兼容性修复只允许落在 workflow 源目录范围内

## Research Notes

### Temporary Projects

* A: `/tmp/trellis-native-a-HqweO8`
* B: `/tmp/trellis-native-b-qDy6wp`

### What script analysis sees

* `analyze-upgrade.py` 对 A/B/B 输出 `keep=55`，说明当前脚本模型只覆盖 workflow 已托管资产。
* 当前脚本可见资产主要包括：
  * Claude / OpenCode 命令层
  * Codex skills
  * `.trellis/workflow.md`
  * `.trellis/scripts/workflow/*.py`
* 当前脚本不可见资产包括：
  * `.claude/settings.json`
  * `.claude/hooks/*.py`
  * `.claude/agents/*.md`
  * `.opencode/agents/*.md`
  * `.codex/config.toml`
  * `.codex/hooks.json`
  * `.codex/hooks/*.py`
  * `.codex/agents/*.toml`

### What direct project inspection shows

* B 并没有丢失 Trellis 原生 hooks / agents / config；这些文件依然存在，并与 A 保持一致。
* B 的 `start` 命令主链直接调用 `research`、`implement`、`check` 子代理，说明 workflow 实际依赖 Trellis 原生 agent/hook 能力。
* B 的 `parallel` 在命令层和 skill 层都被显式禁用，说明当前 workflow 主动放弃了 Trellis 的 worktree/dispatch 并行能力。
* A/B 都存在 `dispatch` / `plan` 原生 agents，但当前 workflow 文档没有把它们作为可用原生能力写进边界模型。

### Dispatch / Plan Agent analysis

* `parallel-disabled.md` 已把“后台 worktree agent、dispatch + create-pr 流水线、任何 PR 驱动任务收尾方式”列为禁用对象。
* 当前 workflow 已自建 `/trellis:plan` 阶段，并明确规定：
  * `plan` 只做任务拆解与摘要规划
  * 不自动进入实现
  * 进入实现必须回到 `/trellis:start`
  * 同项目域默认串行，不自动续跑
* 纯净 Trellis 的 `dispatch` agent 语义仍然是 “按 phase 顺序自动调用 subagents”，与当前 workflow 的强门禁、逐阶段人工确认模型冲突。
* 纯净 Trellis 的 `plan agent` 语义仍然是 “为 dispatch 准备可执行 task directory”，而当前 workflow 已把这部分职责拆成：
  * `brainstorm` / `design` 负责前置澄清
  * `/trellis:plan` 负责真实 Trellis task 图与 `task_plan.md`
  * `/trellis:start` 负责重入当前已确认阶段与 before-dev 自动前置

### Research / Implement / Check subagent chain analysis

* 当前 workflow 实际仍然依赖 `research -> implement -> check` 这一组阶段内角色：
  * Claude / OpenCode 的 `start` 基线正文仍显式调用 `research`、`implement`、`check` 子代理。
  * Codex README 明确把 `.codex/agents/*.toml` 定义为 research / implement / check 角色承载层。
* 用户新增约束：
  * `research` agent 的外部搜索能力优先使用 `exa`
  * 遇到第三方库 / 框架 / SDK 官方文档场景时，必须通过 `Context7` 调用，不再把普通网页搜索当作首选
* 这条链更适合定义为“内部执行角色链”，而不是“用户可见阶段链”：
  * 用户可见阶段链仍是 `brainstorm / design / plan / start / check / finish-work / delivery / record-session`
  * `research / implement / check` 更像 `start` 或 `check` 阶段内部使用的角色分工
* 当前存在一个明显语义冲突：
  * `start` 基线正文里仍保留自动 `Check Agent` 步骤
  * 但当前 workflow 又定义了显式的 `/trellis:check` 阶段，并要求 `start -> check` 之间保留用户确认门禁
* 当前还存在一个能力契约缺口：
  * Claude / OpenCode research agent 已暴露 `exa` 能力，但正文尚未把 `Context7` 写成库文档场景的强约束
  * Codex research.toml 当前只描述“读 spec / 找代码模式 / 定位文件”，没有显式写出 `exa` / `Context7` 的调用规则
* Claude / OpenCode / Codex 三端的这条链强度并不一致：
  * Claude：有 `PreToolUse` + `inject-subagent-context.py`，子代理上下文注入最完整
  * OpenCode：存在 `inject-subagent-context.js`，但文档仍保留“需额外验证”的平台差异说明
  * Codex：有 SessionStart hook 与 subagents，但没有与 Claude 等价的 subagent-context hook；且 `check.toml` 当前是 read-only reviewer 语义，不等于 Claude/OpenCode 的“可自修复 check agent”

### New candidate execution model from discussion

* 用户提出的新模型：
  * 将 `research -> implement -> check` 视为一个整体
  * 将该整体定义为 workflow 的“具体任务实现阶段（implementation stage）”内部链条
  * 该内部链条完成后，再进入正式的 `/trellis:check`
  * 若正式 `/trellis:check` 不通过，则回到 implementation 内部链条继续修复
* 该模型与当前状态机大体兼容：
  * `workflow-state.stage = implementation` 时，`/trellis:start` 负责重入实施主链
  * `/trellis:check` 已经定义为“实现后质量检查”正式门禁
  * `/trellis:check` 不通过时，当前下一步推荐本来就是回到 `/trellis:start`
* 该模型当前仍有两个待收口问题：
  * **命名冲突**：内部 `check` agent 与外部 `/trellis:check` 阶段同名，文档语义容易混淆
  * **Codex 差异**：Codex 的 `check.toml` 当前偏 reviewer 语义，不完全等同 Claude/OpenCode 的“review & fix”型内部 check agent

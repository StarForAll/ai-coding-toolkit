# brainstorm: 修复完善新项目开发工作流

## Goal

在不脱离 Trellis 核心工作流设计的前提下，分析并修复 `docs/workflows/新项目开发工作流` 对目标项目的安装与执行行为，使其原生适配 Claude Code / Codex / OpenCode 的官方使用方式，并去除不需要的后台 PR 式任务执行。

## What I already know

* 目标工作流目录是 `docs/workflows/新项目开发工作流`
* 当前阶段只做分析和修改方案，不直接改动代码
* OpenCode 当前完整执行任务时会在后台默默运行并以创建 PR 的形式完成任务，用户要求改为直接在目标项目内实现任务
* 所有 CLI 都需要禁止 git PR 功能
* 需要在目标项目使用该工作流的 brainstorm 阶段增加一个固定任务，分为“代码分析讨论 → 方案确认 → 具体修改”三个阶段
* 该固定任务不是每个任务完成后都执行，而是在目标项目所有代码相关任务完成后，作为项目级全局审查任务执行一次
* 可以新增独立命令 `project-audit`
* 为支持 `project-audit` 自动触发，`task_plan.md` 的任务执行矩阵可以新增 `任务域` 列，允许值为 `代码相关 / 非代码相关 / 项目级审查`
* `project-audit` 手动触发时采用“预审模式”：允许完整执行 1/2/3，但不将项目级 `project-audit` 终局任务标记为最终完成
* 修改要遵循 Claude Code / Codex / OpenCode 官方原生格式，但优先服从 Trellis 框架核心

## Assumptions (temporary)

* 当前问题既涉及工作流文档，也涉及该工作流下的命令脚本与安装产物
* PR 行为可能来自 `.trellis/scripts/multi_agent/create_pr.py`、工作流命令模板或某个子代理/命令文档
* “禁止 git pr 功能”应落到源工作流资产层，而不是只在单个 CLI 部署副本里临时修补

## Open Questions

* 需要确认“禁止 git PR 功能”是仅禁止自动创建 PR，还是连任何 PR 相关文案、脚本入口、任务提示都一并移除
* 需要确认项目级全局审查任务是复用现有阶段承载，还是新增独立阶段/命令承载

## Requirements (evolving)

* 分析 `docs/workflows/新项目开发工作流` 当前结构、文档、命令、安装逻辑与运行行为
* 识别 OpenCode 后台执行与创建 PR 的触发链路
* 给出遵循官方 CLI 原生格式的修正方案
* 方案必须禁止所有 CLI 的 git PR 功能
* 方案必须把固定的“三阶段代码分析/方案/修改”任务纳入目标项目 brainstorm 阶段
* 该固定任务不能只停留在 brainstorm 文案里，必须在后续任务拆解/阶段路由中成为真实会执行的项目级任务
* 该固定任务的执行时机是“目标项目所有代码相关任务完成之后”，而不是每个子任务完成后执行
* 工作流需要能区分“代码相关任务”与非代码任务，否则无法正确触发该项目级全局审查
* `project-audit` 需要同时支持自动触发与手动触发
* 手动触发 `project-audit` 时采用“预审模式”：可以执行完整审查与修改，但不替代终局正式 `project-audit`

## Acceptance Criteria (evolving)

* [ ] 能说明当前工作流中后台执行与 PR 行为的来源
* [ ] 能说明需要修改的文件范围和每类修改的目的
* [ ] 能给出至少一个可执行且与 Trellis 核心兼容的推荐方案
* [ ] 在用户确认前不执行具体修改
* [ ] 已明确 `project-audit` 的触发条件、矩阵字段和与最终收尾链路的关系

## Definition of Done (team quality bar)

* 方案覆盖文档、命令、脚本、安装产物四类影响面
* 明确说明哪些修改位于源工作流目录，哪些会影响目标项目安装结果
* 风险、兼容性影响、回滚思路清晰

## Out of Scope (explicit)

* 本轮不直接修改工作流文件
* 本轮不运行目标项目侧的安装/升级实操
* 本轮不处理与本工作流无关的其他 workflow

## Technical Notes

* 待分析目录：`docs/workflows/新项目开发工作流`
* 需要检查与该工作流相关的 `.claude/`、`.opencode/`、`.iflow/`、`.codex/`、`.agents/`、`.trellis/scripts/` 资产
* 需要补充官方格式证据，避免对 CLI 原生格式做错误假设

## Repo Findings

### Relevant Specs / Assets

* `docs/workflows/新项目开发工作流/工作流总纲.md`：主链路说明，仍把 `parallel/worktree` 作为可选后续路径
* `docs/workflows/新项目开发工作流/命令映射.md`：阶段映射与安装叙事，仍保留 `/trellis:parallel`
* `docs/workflows/新项目开发工作流/commands/brainstorm.md`：需求发现阶段定义，适合注入新增固定任务
* `docs/workflows/新项目开发工作流/commands/plan.md`：任务拆解阶段，当前仍把并行开发作为推荐出口之一
* `docs/workflows/新项目开发工作流/commands/test-first.md`：测试阶段说明，也仍引用 `/trellis:parallel`
* `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`：阶段路由补丁，当前自然语言路由仍会把“并行/worktree”导向 `/trellis:parallel`
* `docs/workflows/新项目开发工作流/commands/install-workflow.py`：安装器，当前会分发命令、补丁、shared scripts，并向目标项目 `AGENTS.md` 注入 NL 路由表
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py`：受管理资产清单，当前未管理 `parallel`

### Code Patterns / Behavior Sources

* `docs/workflows/新项目开发工作流` 自身没有分发 `parallel` 命令，但多处文档和路由仍主动推荐 `/trellis:parallel`
* `.opencode/commands/trellis/parallel.md` 明确要求在主仓库中调度 worktree agent，并调用 `.trellis/scripts/multi_agent/start.py`
* `.opencode/agents/dispatch.md` 明确包含 `create-pr` 阶段，并调用 `.trellis/scripts/multi_agent/create_pr.py`
* `.trellis/scripts/multi_agent/create_pr.py` 会执行 commit / push / `gh pr create`
* `.trellis/scripts/multi_agent/start.py` 会在后台启动 CLI 进程执行 dispatch 流程
* `.opencode/commands/trellis/start.md` 的常规单任务路径本身并不要求 PR，也不是 worktree/dispatch 模型；问题主要来自对 `parallel` 的推荐与旧多代理资产仍在仓库中可用

### Official CLI Format Evidence

* Claude Code 官方文档说明：项目级 `.claude/commands/` 仍可工作，但已与 skills 统一；子代理使用专门的 subagent/skill frontmatter 机制
* OpenCode 官方文档说明：项目级 `.opencode/commands/` 与 `.opencode/agents/` 都是原生承载方式；命令可绑定 agent / subtask，agent 可配置 `mode` 与 `permission`
* Codex 官方资料说明：项目规则主要通过 `AGENTS.md`、`~/.codex/config.toml`、hooks、skills 承载，而不是项目级 slash command 目录

## Feasible Approaches Here

**Approach A: Workflow-level deparallelization + PR prohibition** (Recommended)

* How it works:
  * 在 `docs/workflows/新项目开发工作流` 内移除或改写所有 `/trellis:parallel`、`worktree`、后台 dispatch、PR 导向叙事
  * 修改 `brainstorm.md` / `plan.md` / `test-first.md` / `start-patch-phase-router.md` / `命令映射.md` / `工作流总纲.md` / `install-workflow.py`
* 在 `brainstorm.md` 中把“全局代码分析与查缺补漏”定义为固定的项目级终局任务，并要求写入 `prd.md`
* 在 `plan.md` 中强制把该任务加入 `task_plan.md` 末端，依赖于全部代码相关任务完成
* 在阶段路由中增加项目级门禁：全部代码相关任务完成后，不直接进入最终交付，而是先进入该固定任务
* 在 `task_plan.md` 的任务执行矩阵中新增 `任务域` 列，支持根据 `代码相关 / 非代码相关 / 项目级审查` 判断自动触发条件
* 让安装器注入的 `AGENTS.md` NL 路由表不再暴露 `parallel`
* 明确把默认执行模型统一为“当前 CLI 在目标项目当前工作区直接完成单任务闭环”
* 在 workflow 规则中显式禁止 `git pr` / `gh pr create` / PR 驱动完成路径
* Pros:
  * 修改范围集中在当前 workflow 源目录
  * 能直接切断用户通过 workflow 进入旧多代理 PR 流水线的入口
  * 与用户要求“优先以 Trellis 核心为前提，但按各 CLI 官方原生格式承载”一致
* Cons:
  * 不能自动删除仓库中本来就存在的旧 `.trellis/scripts/multi_agent/*` 资产，只能让 workflow 不再引用/暴露它们
  * 若目标项目或用户手动调用旧 `parallel` 能力，仍需额外规则约束

**Approach B: 在 Approach A 基础上，新增 workflow 对 baseline `parallel` 的显式覆盖/禁用补丁**

* How it works:
  * 除了去掉推荐路径，还扩展安装器，使其对目标项目现有 `parallel` 命令/skill 做覆盖或禁用提示
  * 例如改写 `parallel` 为“此 workflow 禁止使用并行 worktree + PR 流水线，请直接在当前项目实现”
* Pros:
  * 约束更强，能减少用户误触旧命令
  * 对 OpenCode/Claude/Codex 的“禁止 PR”更接近硬约束
* Cons:
  * 改动面更大，需要额外设计 Claude/OpenCode/Codex 三端的覆盖策略
  * 需要确认 Trellis 基线中 `parallel` 在目标项目是否一定存在，否则补丁逻辑要做兼容分支

**Approach C: 仅改文档与命令说明，不碰安装器**

* How it works:
  * 只改 `工作流总纲.md`、`命令映射.md`、阶段命令文档
* Pros:
  * 实现最轻
* Cons:
  * `install-workflow.py` 仍会把旧 NL 路由注入到目标项目 `AGENTS.md`
  * 不能真正解决 workflow 安装后的错误引导，风险最高

## Recommended Direction

推荐采用 **Approach A**，并预留是否升级到 **Approach B** 的决定点。

原因：

* 当前用户问题的直接根因是 workflow 在源文档和路由层仍暴露 `parallel/worktree/PR` 路径
* 这些问题可以在当前工作流目录内完成闭环修复，不必先碰全局 Trellis 基线
* 如果后续确认目标项目普遍仍会误触 baseline `parallel`，再追加 B 做安装期显式禁用更稳妥

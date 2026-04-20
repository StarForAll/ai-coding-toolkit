# brainstorm: analyze 新项目开发工作流 drift and closure

## Goal

在不修改 `docs/workflows/新项目开发工作流/` 目录外资产的前提下，系统分析当前工作流文档是否存在数据漂移、流程定义与执行闭环脱节、与真实 Trellis 初始化行为不一致、以及 Claude Code / Codex / OpenCode 原生适配边界不清的问题，并产出一份可执行的文档修改方案。

## What I already know

* 用户要求当前阶段只做分析与修改方案，不直接实施修改。
* 目标范围明确限定为 `docs/workflows/新项目开发工作流/` 目录。
* 用户特别关注的数据漂移面不只包括 `.trellis/.claude/.opencode`，还包括 `.agents/skills` 与 `.codex`。
* 当前 workflow 文档已经显式提到 `.agents/skills` 会同时影响 OpenCode 与 Codex，且存在多 skills 目录边界说明。
* 当前 workflow 文档已经显式提到 `start` / `finish-work` / `record-session` 属于 Trellis baseline + workflow patch 模型，而不是当前 workflow 全量重定义。
* 当前 `install-workflow.py` 会自动检测多个 CLI，并在同一个目标项目中部署多 CLI 适配层。
* 当前 `install-workflow.py` 已包含对 `finish-work`、`record-session`、`parallel`、managed agents 等补丁/部署逻辑。
* 当前 `upgrade-compat.py` 已包含对 Claude / OpenCode / Codex 三类目标的恢复与检查逻辑，且 Codex 逻辑显式处理多 skills 目录。

## Assumptions (temporary)

* 目前最主要的问题更可能是“文档分散、声明重复、闭环验证点没有统一清单”，而不一定是安装器实现完全缺失。
* 需要通过 `/tmp` 临时项目执行 `trellis init` 才能确认文档里关于隐藏目录、skills 双目录、baseline patch 边界的描述是否与真实初始化结果一致。
* 需要补充官方 CLI 原生格式证据，避免 workflow 文档只基于仓库现状自洽而与官方约定发生偏差。

## Open Questions

* `trellis init` 在一个最小临时项目里实际会生成哪些隐藏目录、哪些目录是 baseline、哪些目录只是本仓库已有历史定制？
* 当前 workflow 文档里哪些“流程层面有，执行闭环没做完”的条目只是文档没写清，哪些是安装/升级/验证链路真的缺口？
* Claude Code / Codex / OpenCode 的官方原生适配格式，与当前 workflow 文档写法之间是否存在需要修订的边界或措辞？

## Requirements (evolving)

* 识别 `docs/workflows/新项目开发工作流/` 内容易产生数据漂移的文档点、重复声明点、以及 source-of-truth 不清的内容。
* 识别工作流中“定义了动作/阶段/闭环要求，但没有给出完整执行或核验机制”的缺口。
* 分析当前 workflow 是否符合真实开发经验，包括前置条件、阶段切换、收尾链路、升级核对、以及多 CLI 共存时的维护负担。
* 分析 `trellis init` 后目标项目中的 `.trellis`、`.claude`、`.opencode`、`.agents/skills`、`.codex` 等隐藏目录与当前 workflow 的真实关联边界。
* 产出只针对 `docs/workflows/新项目开发工作流/` 的修改方案，且要求 Claude Code / Codex / OpenCode 均按各自官方原生格式表达。

## Acceptance Criteria (evolving)

* [ ] 给出 workflow 目录内的主要漂移风险清单，并说明每一项的触发原因与影响面。
* [ ] 给出“流程有定义但闭环未完成”的缺口清单，并区分文档缺口与实现缺口。
* [ ] 给出基于临时项目 `trellis init` 结果的隐藏目录关联分析。
* [ ] 给出 Claude Code / Codex / OpenCode 原生适配边界的证据化比对结果。
* [ ] 给出一套按文档层次组织的修改方案，明确建议改哪些文件、为何改、如何降低后续漂移。

## Definition of Done (team quality bar)

* 分析结论引用到实际文件或命令证据
* 临时项目验证结果可复现
* 明确区分“已证实”“待验证”“推断”
* 不越界修改 `docs/workflows/新项目开发工作流/` 之外的正式资产

## Out of Scope (explicit)

* 直接修改 workflow 文档或安装器代码
* 修改 `.claude/`、`.opencode/`、`.codex/`、`.agents/skills/`、`.trellis/` 的正式资产
* 处理与本次 workflow 目录无关的其他项目任务

## Technical Notes

* 已检索目录：`docs/workflows/新项目开发工作流/`
* 已定位关键文件：`工作流总纲.md`、`命令映射.md`、`CLI原生适配边界矩阵.md`、`目标项目兼容升级方案指导.md`、`commands/install-workflow.py`、`commands/upgrade-compat.py`、`commands/test_workflow_installers.py`
* 已定位关键主题：多 CLI 同装、baseline patch、双 skills 目录、record-session metadata closure、parallel 禁用覆盖、workflow-installed.json、bootstrap task 清理

## Research Notes

### /tmp 临时项目验证

* 已在 `/tmp/trellis-workflow-inspect` 执行 `trellis init --claude --opencode --codex -y -u xzc`
* baseline 结果证实：`trellis init` 不仅会生成 `.trellis/.claude/.opencode`，还会生成 `.agents/skills/`、`.codex/agents/`、`.codex/hooks.json`、`.codex/hooks/session-start.py`，并在本次观测中只在 `.codex/skills/` 下创建 `parallel`
* 在该临时项目上执行 `docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-workflow-inspect` 后，安装器会：
  - 向 Claude / OpenCode 分发阶段命令并注入 `start` / `finish-work` / `record-session` / `parallel` 补丁
  - 向 Codex 的所有 skills 目录同步写入阶段 skills
  - 只在活动 skills 目录注入 `start` / `finish-work` patch
  - 部署 `.trellis/scripts/workflow/*.py`
  - 更新 `.trellis/workflow.md`
  - 写入 `.trellis/workflow-installed.json`
  - 在 `AGENTS.md` 注入 `workflow-nl-routing` 托管区段
* 已执行 `upgrade-compat.py --project-root /tmp/trellis-workflow-inspect --check`，结果为 0 冲突，说明当前“安装器 + 升级检查器”闭环是存在的

### 已证实的文档漂移点

* `工作流总纲.md` 的 Codex CLI 原生配置层表述只写了 `.agents/skills/`，未纳入 `.codex/skills/`
* `命令映射.md` 的 Codex 配置层矩阵同样遗漏 `.codex/skills/`
* `CLI原生适配边界矩阵.md` 内部存在 Codex 口径不一致：
  - 前文明确写了阶段 skills 同步写入 `.agents/skills/` + `.codex/skills/`
  - 速查表却只保留 `.agents/skills/*/SKILL.md`
  - 前文明确写了 `start` / `finish-work` 双 patch
  - 速查表却只写 Codex `finish-work`
* `工作流总纲.md` 安装时序对 Codex “hooks 相关补丁嵌入”表述偏强，但 `install-workflow.py` 实际只校验 `.codex/hooks.json` 与 `.codex/hooks/session-start.py` 是否存在，不负责分发这两项

### 已证实的闭环缺口类型

* 当前缺口更偏向“主安装链路文档没有把装后核对显式提升为默认步骤”，而不是安装器或升级检查器完全缺失
* `装后/升后必检项` 目前主要集中在 `目标项目兼容升级方案指导.md`，但 `工作流总纲.md` 的安装时序只写到“安装完成后直接使用”，没有把隐藏目录与托管边界核对提升成主链动作

### 官方格式证据

* Claude Code 官方文档证实：`.claude/settings.json` / `.claude/settings.local.json` / `.claude/agents/` 是原生项目层承载面，且 `.claude/commands/*.md` 仍兼容工作
* OpenCode 官方文档证实：`.opencode/commands/`、`.opencode/agents/`、`AGENTS.md`、`.agents/skills/` 均是原生或兼容承载面
* Codex 官方文档证实：`.codex/config.toml`、`.codex/hooks.json`、`.codex/agents/*.toml`、`AGENTS.md`、`.agents/skills/` 是原生承载面；官方文档未把 `.codex/skills/` 定义为项目技能主目录，因此当前 workflow 对 `.codex/skills/` 的处理应继续作为 Trellis 初始化后的兼容性现实，而不是在主叙述中误写成 Codex 官方唯一标准

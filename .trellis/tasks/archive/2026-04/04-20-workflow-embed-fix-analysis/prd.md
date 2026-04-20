# brainstorm: 修复新项目开发工作流嵌入不完全

## Goal

分析 `docs/workflows/新项目开发工作流/` 对应工作流在目标项目中出现“旧的/半嵌入”状态的原因，结合 `/tmp` 临时项目中的 `trellis init` 基线行为与 ClaudeCode / Codex / OpenCode 的原生承载格式，提出以 Trellis 核心为前提的修复方案，并在用户确认后再进行具体修改。

## What I already know

* 用户限定分析与后续修改范围为 `docs/workflows/新项目开发工作流/` 目录。
* 用户要求先在 `/tmp` 新建临时项目并执行 `trellis init`，基于真实初始化结果判断当前 workflow 的嵌入机制。
* 当前 workflow 的核心安装入口是 `docs/workflows/新项目开发工作流/commands/install-workflow.py`。
* 安装器默认是“多 CLI 同装 + 基线补丁增强”模型，不是完全替换 Trellis 原生命令全集。
* 文档已经明确要求“先 `trellis init`，再运行 `install-workflow.py`”，并且安装后需要做装后核对。
* Codex 侧当前通过 skills / hooks / AGENTS / subagents 承载，而不是 slash commands。
* `/tmp/trellis-workflow-embed-analysis-sBFAfe` 中已验证：`trellis init --claude --opencode --codex -y -u xzc` 会生成 `.claude/commands/trellis/`、`.opencode/commands/trellis/`、`.agents/skills/`、`.codex/skills/parallel`、`.codex/hooks.json`、`.codex/hooks/session-start.py`、`.codex/agents/*.toml`、`AGENTS.md`、`.trellis/.version`。
* 对该临时项目执行 `install-workflow.py --dry-run` 与真实安装后，再执行 `upgrade-compat.py --check`，结果均为完整通过，没有出现安装器自身导致的残缺态。
* OpenAI 官方 Codex 文档确认：Codex 依赖 `AGENTS.md`、`<repo>/.codex/hooks.json`、`.codex/agents/*.toml`、以及从当前目录到仓库根逐层扫描的 `.agents/skills/`；Codex CLI slash commands 是内建控制命令，不是项目自定义 workflow 命令目录。
* Anthropic 官方文档确认：Claude Code 项目自定义命令目录是 `.claude/commands/`。
* OpenCode 官方文档确认：项目命令目录是 `.opencode/commands/`，项目 agents 目录是 `.opencode/agents/`，并且会扫描 `.agents/skills/*/SKILL.md`。

## Assumptions (temporary)

* “半嵌入”更可能来自目标项目内通过自然语言驱动 Codex 手工复制/局部改写，而不是执行安装器本身。
* 触发该偏差的关键因素之一，是现有文档示例命令主要使用相对路径 `docs/workflows/.../install-workflow.py`，这只适用于在源仓库根执行；当操作者位于目标项目目录时，该路径无效，模型容易退回到手工嵌入。
* 目前“如何嵌入”相关规范分散在总纲、命令映射、多 CLI 演练、平台 README、边界矩阵、装后核对清单中，模型容易只读到局部说明，遗漏 `requirements-discovery-foundation` 导入、AGENTS 路由块注入、`.trellis/workflow.md` patch、`.codex/skills` 额外影响面同步、以及装后校验。
* 需要一个单一事实源文档，统一描述“嵌入步骤 + 前置校验 + 绝对路径执行方式 + 成功判据 + 漂移修复入口”，并明确禁止手工复制落盘替代安装器。

## Open Questions

* 是否需要在安装器中内置“安装后自动校验”或 `--verify` 行为，进一步阻止“看起来装完、实际上没验”的情况？
* 是否需要增加专门的嵌入规范文件名与入口约定，方便用户在目标项目中直接把该文件路径交给 ClaudeCode/Codex/OpenCode 读取执行？

## Requirements (evolving)

* 解释为什么在目标项目目录下用 Codex 输入嵌入要求时，会出现旧的/半嵌入状态。
* 给出避免旧状态、半嵌入、局部覆盖的工作流修复方案。
* 方案需要兼容 ClaudeCode / Codex / OpenCode 的原生格式，但优先遵守 Trellis 核心机制。
* 给出“把嵌入工作流所需步骤、规范、关联内容集中到一个文件”的整理方案。
* 方案应覆盖“从源仓库执行”和“从目标项目目录直接发起”的两种使用场景。
* 单文件规范不能只面向 Codex，需要同时适配 ClaudeCode / OpenCode / Codex 的阅读与执行习惯。
* 在其他项目中，只要向 CLI 指定该文件的绝对路径，就应能根据该文件完成完整、有效、可校验的 workflow 嵌入。
* 该文件不得包含嵌入失败、半嵌入、异常嵌入状态下的自动重置、自动修复、自动补装流程。
* 若执行嵌入前判定目标项目已嵌入但状态异常，或本次嵌入执行失败，必须阻止后续操作，并明确提示用户需要手动处理后重新执行完整嵌入。
* 需要补充 spec / 联动更新合同：以后每次修改 `docs/workflows/新项目开发工作流/` 的嵌入协议、状态判定、托管资产范围、安装器/校验器行为时，都必须先判断 `工作流嵌入执行规范.md` 是否需要同步修改。
* 当前阶段只输出分析与修改方案，等待用户确认后再实施。

## Acceptance Criteria (evolving)

* [ ] 给出“半嵌入”问题的可验证成因链，而不是仅凭推测。
* [ ] 给出按 Trellis 基线 + 多 CLI 原生承载格式设计的修复方案。
* [ ] 给出单文件聚合嵌入规范的文档方案，并说明它与其他文档的边界。
* [ ] 单文件方案明确支持通过绝对路径在目标项目中被 ClaudeCode / Codex / OpenCode 直接读取执行。
* [ ] 单文件方案明确禁止自动修复/自动重置，并定义异常状态下的阻断输出。
* [ ] 单文件方案配套联动更新规则，明确哪些工作流改动必须回看并评估是否同步更新该文件。
* [ ] 明确哪些修改点属于代码、哪些属于文档、哪些属于验证链路。

## Definition of Done (team quality bar)

* 分析结论有代码、文档、初始化样例或官方文档证据支撑
* 修复方案包含验证方式与回归关注点
* 明确完成项、未完成项、风险与下一步

## Out of Scope (explicit)

* 当前阶段不直接修改 `docs/workflows/新项目开发工作流/` 下任何文件
* 当前阶段不提交代码、不执行安装器写入目标项目

## Technical Notes

* 关键入口：`docs/workflows/新项目开发工作流/commands/install-workflow.py`
* 参考文档：`命令映射.md`、`多CLI通用新项目完整流程演练.md`、`装后隐藏目录与托管边界核对清单.md`、`commands/{claude,opencode,codex}/README.md`
* `/tmp` 基线证据：
  - `trellis init --claude --opencode --codex -y -u xzc`
  - `.agents/skills/` 为 Codex 主要 skills 面，`.codex/skills/parallel` 为额外影响面
  - 安装器真实执行后，`upgrade-compat.py --check` 结果为 `总冲突: 0`
* 官方 CLI 文档约束摘要：
  - Claude Code：项目命令落在 `.claude/commands/`
  - OpenCode：项目命令落在 `.opencode/commands/`，项目 agents 落在 `.opencode/agents/`，skills 会扫描 `.agents/skills/`
  - Codex：读取 `AGENTS.md`、`<repo>/.codex/hooks.json`、`.codex/agents/*.toml`，并从工作目录向上扫描 `.agents/skills/`
  - Codex CLI slash commands 是内建控制命令，不是当前 workflow 的项目命令承载面

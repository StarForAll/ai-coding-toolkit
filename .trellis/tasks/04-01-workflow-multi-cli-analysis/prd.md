# brainstorm: 新项目开发工作流多 CLI 适配分析

## Goal

分析 `docs/workflows/新项目开发工作流/` 这套工作流对多 AI CLI 的原生适配是否达到要求，重点审查 Claude Code、Codex CLI、OpenCode 三个平台的能力声明、命令承载模型、上下文注入方式、安装落地叙事与实际 CLI 行为是否一致；在结论明确后，仅修改 `docs/workflows/新项目开发工作流/` 内的文档或脚本说明。

## What I already know

* 当前目标目录已经包含完整工作流文档、命令映射、安装/卸载脚本、平台适配 README 与辅助脚本。
* 用户已明确澄清：在目标项目执行 `trellis init` 后嵌入当前工作流时，默认是把当前工作流支持的多 CLI 配置一起装进同一个项目，而不是按某个 CLI 单独安装。
* 安装器默认会自动检测并同时部署多个 CLI：
* `commands/install-workflow.py` 中 `detect_cli_types()` 会收集 `claude`、`opencode`、`codex`
* 未传 `--cli` 时，`workflow-installed.json` 会记录全部检测到的 CLI
* `命令映射.md` 的总体口径已经接近正确方向：
* Claude Code 被视为原生命令基线平台。
* OpenCode 被视为“原生命令 / rules / agents / skills 可承载”平台。
* Codex 被视为“AGENTS / hooks / skills / subagents 可承载，workflow 入口采用 skills/agents 模型”的平台。
* 现有 `commands/*.md` 多处 `Cross-CLI` 标注仍使用同一套模板，可能存在过度乐观或粒度不够的问题。
* `commands/install-workflow.py` 的实现显示：
* Claude / OpenCode 通过命令目录部署。
* Codex 通过把命令文件直接转换为 `.agents/skills/*/SKILL.md` 落地。
* 这说明“文档口径”与“安装脚本实际行为”已经不完全只是说明层问题，而是存在部署模型设计问题。
* 本机实际环境已确认三套 CLI 可执行：
* `claude 2.1.85 (Claude Code)`
* `codex-cli 0.118.0`
* `opencode 1.3.13`
* 已在 `/tmp` 夹具项目上实际验证：同一目标项目可同时生成
* `.claude/commands/trellis/*.md`
* `.opencode/commands/trellis/*.md`
* `.agents/skills/*/SKILL.md`
* `.trellis/scripts/workflow/*`
* `.trellis/workflow-installed.json` 中 `cli_types = [\"claude\", \"opencode\", \"codex\"]`

## Assumptions (temporary)

* 本轮不仅要输出分析结论，还需要把目标目录中的文档口径修正到“与官方能力、当前落地实现、以及多 CLI 同装事实一致”。
* 若发现安装脚本与文档结论明显冲突，允许在同目录内修正脚本注释、README 或映射说明，但不修改仓库其他目录。
* 本轮优先解决“平台承载模型是否说对”“同装叙事是否说清”“workflow 入口是否设计对”三个问题，不扩展到 Gemini、Cursor 的完整重构。

## Open Questions

* 文档最终是否要把“多 CLI 同装”写成默认推荐叙事，同时把 `--cli` 仅保留为高级过滤能力，而不是主叙事？

## Requirements (evolving)

* 逐项核对 Claude Code / Codex / OpenCode 的官方原生能力：
* 自定义命令
* 项目规则文件
* hooks
* agents / subagents
* skills
* 给出“当前工作流是否达到要求”的分平台判断，而不是泛泛写“支持/不支持”。
* 识别文档中的三类偏差：
* 把平台内建能力误写成项目工作流入口
* 把平台可承载能力写得比真实落地更完整
* 文档口径与安装脚本实际行为不一致
* 识别“多 CLI 同装”语境下的额外偏差：
* 是否把“默认同装”误写成“按 CLI 单独安装”
* 是否没有区分“同装”与“同一触发方式”
* 是否没有清楚说明 Codex 在同装后仍然不是命令目录入口模型
* 所有修改仅发生在 `docs/workflows/新项目开发工作流/`。

## Acceptance Criteria (evolving)

* [ ] 能给出 Claude Code / Codex / OpenCode 三个平台各自的“原生能力矩阵 + workflow 正确承载模型”。
* [ ] 能指出当前文档中至少哪些地方已经正确，哪些地方仍然失真或不完整。
* [ ] 若发生文档修改，修改后能明确区分：
* Claude Code 的项目命令模型
* OpenCode 的项目命令模型
* Codex 的 skills / hooks / AGENTS / subagents 模型
* [ ] 修改后能明确表达：同一个目标项目可同时装入三套 CLI 适配，但三套入口模型并不相同。
* [ ] 若触及安装说明，文档描述不能与 `install-workflow.py` 的实际行为互相矛盾，或必须明确标注“当前实现/推荐模型”的差距。

## Definition of Done

* 结论基于官方文档和本机 CLI 可执行证据，不靠记忆猜测
* 变更范围严格限制在 `docs/workflows/新项目开发工作流/`
* 文档中的平台能力描述、命令入口描述、安装叙事彼此一致
* 完成后至少运行与目标目录相关的静态校验或最小验证命令

## Out of Scope (explicit)

* 不修改 `.codex/`、`.claude/`、`.opencode/`、`.agents/` 等项目根下其他目录
* 不重构 Trellis 全仓库多 CLI 体系
* 不扩展到 Gemini 的原生适配实现

## Technical Notes

* 已审查仓库文件：
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `docs/workflows/新项目开发工作流/命令映射.md`
* `docs/workflows/新项目开发工作流/commands/codex/README.md`
* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* `docs/workflows/新项目开发工作流/commands/install-workflow.py`
* 已获得的官方/一手证据方向：
* Claude Code 官方文档：slash commands、subagents、hooks
* Codex 官方文档：AGENTS.md、skills、slash commands、hooks
* OpenCode 官方文档：commands、agents、rules、skills

## Research Notes

### What similar tools do

**Claude Code**

* 支持项目级自定义 slash commands，路径为 `.claude/commands/`
* 支持项目级 subagents，路径为 `.claude/agents/`
* 支持 hooks 扩展

**Codex CLI**

* 支持 built-in slash commands，但它们是 Codex 自身控制命令
* 支持 `AGENTS.md` 指令链、hooks、skills、subagents
* 当前更像“规则 + skills + agents”的 workflow 入口模型，而不是“项目自定义 slash command 文件目录”

**OpenCode**

* 支持 `.opencode/commands/` 项目命令
* 支持 `AGENTS.md` / rules / agents / skills
* 但 plugin/hook 对 subagent 上下文注入链路需单独验证，不能默认等于 Claude Code

### Constraints from our repo/project

* 现有文档中很多命令页使用统一 `Cross-CLI` 模板，容易把“可承载”误读成“已完整适配”。
* 安装脚本对 Codex 采取“命令文件直接转 skill 文件”的策略，这可能和推荐的 skill 设计边界不完全一致。
* 当前工作流真正的安装模型是“同一项目多 CLI 共存”，所以文档必须同时说明“共存”与“差异”，不能只写单平台适配说明。
* 用户明确要求不得修改目标目录之外的任何文件。

### Feasible approaches here

**Approach A: 文档口径优先收敛**（Recommended）

* How it works:
* 先统一修正文档中的平台能力表述、Cross-CLI 标注、安装说明，必要时仅在同目录内补充“当前实现 vs 推荐模型”的边界说明。
* Pros:
* 风险低，严格满足修改范围限制。
* 能先把“说法错误”收敛掉，避免继续误导。
* 能先把“多 CLI 同装，但入口不同”这件事说清楚。
* Cons:
* 若安装脚本本身有设计偏差，只能文档化揭示，不能完全消除实现偏差。

**Approach B: 文档 + 目标目录内安装脚本说明一起收敛**

* How it works:
* 在修文档的同时，修正 `commands/install-workflow.py` 内注释、输出文案，必要时对其在 Codex/OpenCode 上的承载叙事做最小调整。
* Pros:
* 结论、README、安装输出更一致。
* 能减少“文档说一套，安装输出说另一套”。
* Cons:
* 需要更仔细地区分“说明修正”与“真实安装行为变更”。
* 若改到行为层，验证成本更高。

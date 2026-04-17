# brainstorm: 修复完善新项目开发工作流

## Goal

在不直接修改当前 workflow 的前提下，先对 `docs/workflows/新项目开发工作流/` 做结构化分析，明确需要如何补强“项目完成耗时预估”这一能力，并确保后续修改同时满足 Trellis 基线约束、当前仓库的 workflow 架构，以及 Claude Code / Codex / OpenCode 的原生适配边界。

## What I already know

* 分析对象限定为 `docs/workflows/新项目开发工作流/`
* 当前阶段只输出分析与修改方案，待用户确认后再实施
* 用户要求：当修改涉及 Trellis 联动时，先在 `/tmp` 创建临时项目并执行 `trellis init`，以纯净初始化产物作为判断依据
* 现有 workflow 文档已多处声明：应先 `trellis init`，再运行 `docs/workflows/新项目开发工作流/commands/install-workflow.py`
* 当前 workflow 默认是多 CLI 同装模型，但三种 CLI 的入口协议不同：
  * Claude Code / OpenCode 以项目命令目录为主
  * Codex 以 `AGENTS.md + hooks + skills + subagents` 为主
* 已定位到与本次分析强相关的文件：
  * `工作流总纲.md`
  * `命令映射.md`
  * `多CLI通用新项目完整流程演练.md`
  * `CLI原生适配边界矩阵.md`
  * `commands/claude/README.md`
  * `commands/opencode/README.md`
  * `commands/codex/README.md`
  * `commands/install-workflow.py`

## Assumptions (temporary)

* “项目完成耗时估计”不应在需求尚未澄清时强制产出
* 用户确认的实际业务习惯是：需求与客户讨论清楚后，立即给出项目级粗估
* 若该能力影响报价与完工预期，不能只写提醒文案，最好沉淀为明确产物、字段或门禁
* 需要检查是否已有 `assessment.md`、`prd.md`、`workflow-state.json` 或其他任务产物可承载工时估算

## Open Questions

* 工时预估应以什么格式沉淀，才能兼容三种 CLI 的入口和安装器逻辑
* 是否需要区分“brainstorm 粗估”与“plan 复估”两个层次

## Requirements (evolving)

* 基于当前仓库真实 workflow 内容做分析，不凭记忆下结论
* 涉及 Trellis 基线判断时，以 `/tmp` 中执行 `trellis init` 的纯净产物为准
* 后续方案必须优先服从 Trellis 框架核心，再分别原生适配 Claude Code / Codex / OpenCode
* 本轮仅输出分析结论与修改方案，不实施代码或文档修改
* 覆盖优化点 A：在项目明确之后，需要支持估计项目完成耗时，服务报价与预计完工判断
* 项目级粗估的首次强制产出时点应放在 `brainstorm` 阶段需求已准确、准备离开需求发现时
* `feasibility` 可保留商务层的可行性与报价预判，但不应承担“需求未清时的正式工时承诺”

## Acceptance Criteria (evolving)

* [ ] 明确当前 workflow 中最适合承接工时粗估的阶段与产物位置
* [ ] 说明该能力需要改哪些文档/命令/校验点
* [ ] 给出至少一个推荐方案，并说明为什么优于替代方案
* [ ] 说明该方案如何兼容 Claude Code / Codex / OpenCode 的原生入口差异
* [ ] 在用户确认前不执行具体修改

## Definition of Done (team quality bar)

* 结论有本地文件依据；涉及 Trellis 联动时有 `/tmp` 初始化证据
* 方案说明包含修改点、影响范围、风险与验证思路
* 用户可直接基于方案决定是否进入实施

## Out of Scope (explicit)

* 本轮不直接改 `docs/workflows/新项目开发工作流/` 内任何文件
* 本轮不处理尚未给出的其他优化点
* 本轮不提交 commit、不记录 session、不归档 task

## Technical Notes

* `docs/workflows/新项目开发工作流/命令映射.md` 已声明多 CLI 同装原则、安装顺序与三种 CLI 的入口差异
* `docs/workflows/新项目开发工作流/commands/install-workflow.py` 是实际安装器，后续若能力需要落地到目标项目，最终需要检查其是否受影响
* `docs/workflows/旧项目重构工作流/工作流总纲.md` 已存在“使用 `/tmp` + `trellis init` 作为升级兼容基线”的明确规则，可作为当前 workflow 补齐同类规则的参照

## Research Notes

### Trellis 基线观察

* 已在 `/tmp/trellis-init-baseline-20260417` 执行：
  * `git init -b main`
  * `trellis init --claude --opencode --codex -y -u xzc`
* 当前本机 `trellis --version` 输出为 `0.4.0-beta.10`
* 纯净 `trellis init` 基线中：
  * Claude / OpenCode 会生成 `.claude/commands/trellis/*.md`、`.opencode/commands/trellis/*.md`
  * Codex 会生成 `.agents/skills/*/SKILL.md`
  * 基线中存在 `brainstorm`、`start`、`check`、`finish-work` 等能力
  * **不存在 `feasibility` 阶段命令**
* 结论：`feasibility` 及其中的报价/工时估算能力属于当前自定义 workflow 扩展，不属于 Trellis 核心基线；后续修改应保持“基于 Trellis、但不回写 Trellis 核心”的边界

### 当前 workflow 的工时估算现状

* `工作流总纲.md` 已在 §1.3 写出：
  * 工作量评估
  * 时间成本分析
  * 风险预判
  * 报价输出
* 但可执行脚本 `commands/shell/feasibility-check.py` 的 `ASSESSMENT_TEMPLATE` 里：
  * 没有强制性的“预估工时 / 预计工期 / 交付窗口 / 报价区间 / 估算置信度”字段
  * `--step estimate` 目前只是创建/打印 `assessment.md` 模板，并未生成结构化估算框架
  * `--step validate` 也不会校验这些估算字段
* `plan` 阶段文档与模板里已有“单任务预估工时”，但这是设计之后的任务拆分级估时，不能替代前期报价所需的项目级粗估
* 用户进一步确认：实际应在“需求与客户讨论清楚之后”立刻得到大致耗时，这意味着项目级粗估的主落点应从 `feasibility` 调整到 `brainstorm` 收敛尾声，而不是需求尚未清晰时

### CLI 原生适配观察

* Claude Code：
  * `trellis init` 基线仍使用 `.claude/commands/trellis/*.md`
  * Anthropic 最新文档说明：自定义 commands 已并入 skills，但现有 `.claude/commands/` 仍继续可用
* OpenCode：
  * `trellis init` 基线生成 `.opencode/commands/trellis/*.md` 与 `.opencode/plugins/`
  * OpenCode 官方文档仍将 `opencode.json` / `opencode.jsonc` 作为配置与 `instructions` 承载入口
  * 说明当前 workflow 若修改阶段语义，重点应保持命令内容与文档说明同步；不一定要求本次改动去重构 OpenCode 整体配置模型
* Codex：
  * `trellis init` 基线生成 `.agents/skills/*/SKILL.md`，未默认生成项目级 `.codex/` 目录
  * OpenAI 官方文档确认 Codex 原生支持 `AGENTS.md` 指令链与 `.agents/skills` 技能目录
  * 结论：本次若调整阶段能力，应继续以 skill 形式承接 Codex，而不是引入项目级 `/trellis:xxx` 命令目录

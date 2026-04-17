# brainstorm: 修复新项目开发工作流外部项目交付与收款防护

## Goal

在当前仓库内，仅针对 `docs/workflows/新项目开发工作流/` 对应 workflow 做分析与方案设计，
先基于 `/tmp` 中通过 `trellis init` 初始化得到的纯净 Trellis 基线，理解 Trellis 原生工作机制、
安装边界和多 CLI 适配方式，再提出一套以 Trellis 核心为前提、同时原生适配 Claude Code /
OpenCode / Codex 的 workflow 修正方案，重点补强“外部项目场景下如何避免无法收到尾款、如何在未结清前不交付源码与最终上线能力”的流程与证据链控制。

## What I already know

* 用户要求本轮只做分析和修改方案，不直接改 workflow 文件，待确认后再实施。
* 本次修改边界限定在 `docs/workflows/新项目开发工作流/` 目录。
* 用户要求先在 `/tmp` 中新建临时项目并运行 `trellis init`，先理解 Trellis 原生机制再判断方案。
* 现有 workflow 已明确支持 `Claude Code / OpenCode / Codex` 三种原生适配，且强调“以 Trellis 核心为前提”的多 CLI 同装模型。
* `.trellis/spec/docs/index.md` 明确要求：维护基于 Trellis 的 workflow 兼容性时，必须参考 `/tmp` 临时项目中 `trellis init` 产生的纯净基线，而不能把当前仓库自己的 `.trellis/` / `.claude/` / `.opencode/` / `.codex/` 当作基线。
* `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` 明确：workflow 的 source of truth 是 `docs/workflows/<name>/commands/**` 与 helper scripts，目标项目中的 `.claude/.opencode/.agents/.codex/.trellis/scripts/workflow` 都是派生状态。
* `docs/workflows/新项目开发工作流/命令映射.md` 已写明当前默认安装模型是“同一目标项目内多 CLI 同装”，并区分 Claude/OpenCode 的项目命令入口与 Codex 的 `AGENTS + hooks + skills + subagents` 承载方式。
* `docs/workflows/新项目开发工作流/commands/install-workflow.py` 当前已经校验目标项目为 Git 仓库、执行过 `trellis init`、`origin` 至少有两个 push URL，并根据 CLI 类型部署适配层。

## Assumptions (temporary)

* 外部项目收款与交付风险更适合建模为 workflow 的强门禁、交付控制脚本、文档话术模板、以及必要的源码/密钥/仓库移交前置条件，而不是单纯写在说明文字里。
* 该优化点很可能会影响 `feasibility / design / plan / delivery` 至少四个阶段，以及与之相连的 walkthrough、命令映射、CLI 平台说明、helper validator 和测试。
* 若要做到“未收到尾款前不能交付源码/最终上线能力”，需要同时定义流程侧控制、文档侧话术、以及代码/配置侧的最低防护策略。
* 当前 workflow 不是“只给外包项目用”的专用流程，而是通用主链；外包/外部项目只是附加启用付款与交付控制分支。

## Open Questions

* 当前 workflow 中，外部项目与内部项目的边界是如何判定与持久化的？
* 现有 delivery / ownership-proof / watermark / 验收控制链路，哪些已经能复用，哪些还不足以覆盖“尾款未结清不交付”？
* Trellis 原生初始化后的 Claude/OpenCode/Codex 基线入口结构，与当前 workflow 假设之间是否存在偏差？

## Requirements (evolving)

* 必须先基于 `/tmp` 纯净 Trellis 基线完成机制理解，再给出方案。
* 必须优先遵循 Trellis 核心机制，再讨论三种 CLI 的原生适配。
* 本轮输出仅包含分析、风险判断、可选修改方案、推荐方案，不实施代码变更。
* 方案需要覆盖外部项目场景下的付款门禁、源码交付门禁、对客沟通口径，以及可行的代码层/配置层预防措施。
* 代码层面的预防手段必须单独补强，不能只停留在流程和文档门禁。
* 对客沟通不需要固定模板，但 workflow 应要求在友善沟通时明确说明：尾款确认前不能完成最终源码/控制权移交。
* 任何项目都必须从第一个阶段开始，先进入 `feasibility`，不能跳过主链前置阶段。
* 需要在开始阶段补充对目标项目是否属于外包/外部项目的判断；若不是，workflow 仍继续使用，但不启用首/尾款与交付控制相关手段。
* 一旦判断为外包/外部项目，就不能跳过本 workflow 已定义的前置执行流程，尤其不能绕过 feasibility、付款门禁和阶段确认。
* 对外包/外部项目的新增控制手段必须定义为“强制执行”，不是可选建议；即“先判断项目类别，再执行对应的有效控制手段”。

## Acceptance Criteria (evolving)

* [ ] 明确列出当前 workflow 中与外部项目交付/收款控制相关的现状、缺口、以及受影响文件层面。
* [ ] 明确说明 `/tmp` 纯净 `trellis init` 基线与当前 workflow 假设之间的关键对照结果。
* [ ] 给出 2-3 个可行修正方案，含推荐方案、取舍、影响范围、需要同步传播的文档/脚本/测试。
* [ ] 在实施前向用户清楚说明“准备怎么修、为什么这样修、改动会落到哪里”。

## Definition of Done (team quality bar)

* 分析基于实际仓库上下文与 `/tmp` Trellis 基线，不凭记忆推断。
* 方案覆盖跨层传播面：命令文档、walkthrough、平台 README、helper scripts、测试。
* 明确区分本仓库 source workflow 规则与目标项目安装后的派生产物。
* 用户确认前不做 workflow 正式修改。

## Out of Scope (explicit)

* 本轮不直接修改 `docs/workflows/新项目开发工作流/` 内的正式内容。
* 本轮不处理其他 workflow 目录。
* 本轮不进入真实客户项目执行收款或交付控制操作。

## Technical Notes

* 关键约束来源：
  * `.trellis/spec/docs/index.md`
  * `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
  * `docs/workflows/自定义工作流制作规范.md`
* 已定位的高相关文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/feasibility.md`
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/commands/plan.md`
  * `docs/workflows/新项目开发工作流/commands/delivery.md`
  * `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
  * `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`

## Research Notes

### `/tmp` 纯净 Trellis 基线对照

* 已在 `/tmp/trellis-workflow-baseline-20260417` 执行 `git init`、切到 `main`，再执行：
  * `/ops/softwares/nodeNpm/nodejs/bin/trellis init --claude --opencode --codex -y -u xzc`
* 当前本机 `trellis` CLI 实际运行版本为 `0.4.0-beta.9`，执行时提示可升级到 `0.4.0-beta.10`。
* 纯净初始化结果确认：
  * Claude Code 侧基线命令目录是 `.claude/commands/trellis/*.md`
  * OpenCode 侧基线命令目录是 `.opencode/commands/trellis/*.md`
  * Codex 侧不是项目级 slash command，而是 `AGENTS.md + .agents/skills + .codex/hooks.json + .codex/agents/*.toml`
* 结论：当前 workflow 对三种 CLI 的“承载模型判断”整体没有跑偏，不需要推翻多 CLI 同装设计。

### 官方格式与当前 workflow 的一致性判断

* Claude Code 官方格式支持 `.claude/commands/*.md` 的 Markdown + YAML frontmatter 命令文件，agents/hook/settings 也属于原生承载层；当前 workflow 继续把阶段命令部署到 `.claude/commands/trellis/` 是合理的。
* OpenCode 官方格式支持 `.opencode/commands/*.md` 或 `opencode.json(c)` 中定义 command/agent/instructions；当前 workflow 使用 `.opencode/commands/trellis/` 作为主入口，与原生能力兼容。
* Codex 官方格式强调 `AGENTS.md`、project-scoped skills、hooks、agents/subagents；当前 workflow 把阶段入口映射为 `.agents/skills/*/SKILL.md`，并依赖 `.codex/hooks.json`、`.codex/agents/*.toml`，方向正确。

### 当前 workflow 已有能力

* 已有“外部项目双轨交付控制”：
  * `delivery_control_track`
  * `delivery_control_handover_trigger`
  * `delivery_control_retained_scope`
  * `trial_authorization_terms.*`
* 已有“尾款前不交源码/不交最终控制权”的总规则与交付门禁：
  * `工作流总纲.md`
  * `commands/feasibility.md`
  * `commands/plan.md`
  * `commands/delivery.md`
  * `commands/shell/delivery-control-validate.py`
* 已有“源码水印与归属证明链”，并明确禁止隐藏后门、远程关停、伪源码交付。

### 当前缺口

* 缺少“首款未到账不得开工”的强门禁；当前更多是在 feasibility 的谈判项里提到付款结构，但没有贯穿到 `start` / `implementation` 前置校验。
* `assessment.md` 当前缺少可被脚本强校验的“启动款比例 / 开工触发条件 / 启动款到账状态”机器字段。
* `delivery-control-validate.py` 会校验尾款触发和最终移交边界，但不会校验“30%-40% 首款先到、不满足不开工”。
* `workflow-state.py` 当前只对项目级粗估、正式 PRD 边界、执行授权做校验，不会阻止“外部项目在未满足商务前提时进入 implementation/test-first”。
* `plan.md` 会拆交付任务，但不会显式拆出或强制记录“商务启动门禁 / 开工授权”。
* walkthrough 与通俗版强调尾款前保留控制权，但没有把“首款→开工、尾款→最终移交”形成对称的双门禁叙事。
* 代码层预防目前仍偏弱：虽有 trial authorization / hosted deployment 轨道，但还缺少对“源码仓库权限、生产密钥、正式发布工件、最终上线控制开关”这些资产的透明技术隔离策略说明。
* `start` 阶段当前缺少“项目类型判断”：
  * 还没有在通用主链里明确区分“非外包项目继续走普通主链”与“外包项目附加启用商务/交付控制门禁”
  * 也没有在识别为外部项目后强制“不得跳过 feasibility 与商务门禁”
* 当前 workflow 还没有把“项目类别判断”与“控制手段执行”绑定成同一个强门禁链：
  * 还缺少“判定为外包项目后，必须执行全部新增控制动作”的明确口径
  * 还缺少对应脚本/状态校验来阻止只做分类、不做控制

### 可复用资产

* `trellis-library/specs/universal-domains/project-governance/delivery-control/normative-rules.md` 已要求：
  * handover work 必须 payment-gated
  * final transfer 不能早于 agreed trigger
* `trellis-library/templates/universal-domains/project-governance/external-project-delivery-tasks/control-handover.md` 已把 “Payment received (if control transfer is payment-triggered)” 写进依赖条件。
* 结论：本次更适合在 workflow 目录内补强“前置商务门禁 + 字段契约 + 校验 + 文档传播”，不必新增 trellis-library 资产才能落地第一版修复。

### 用户新增偏好

* 代码层面的预防手段需要补充并纳入推荐方案。
* 不需要固定对客模板，只需要把“友善说明尾款前不能最终移交”作为 workflow 沟通原则写清。
* 需要在 `start`/阶段入口处先判断目标项目是否为外包/外部项目；若不是，继续走通用 workflow 但不启用首/尾款控制；若是，则不得跳过既定流程。
* 判断项目是外包项目之后，新增的控制操作都需要执行；项目类别判断和合理有效手段执行都属于正式规则，不是提示性文案。

# brainstorm: 升级新项目开发工作流适配 trellis 版本

## Goal

在仅修改 `docs/workflows/新项目开发工作流/` 的前提下，完成该工作流对当前 Trellis 版本的自适应升级，明确 Claude Code、Codex、OpenCode 三类 CLI 的原生适配口径，并在实际修改前先形成可确认的修正方案。

## What I already know

* 用户已明确范围只限 `docs/workflows/新项目开发工作流/`
* 修改目标不是泛化重写，而是针对当前 Trellis 升级后的 workflow 适配校准
* 所有 CLI 适配都必须按对应官方原生格式表达，不接受“伪兼容”或跨 CLI 混写
* 具体修改前需要先与用户确认，并说明修正方式
* 现有文档已存在三套平台展开层：
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
* 现有总览文档已把主链与 CLI 入口拆开：
  * `工作流总纲.md`
  * `命令映射.md`
  * `多CLI通用新项目完整流程演练.md`
  * `工作流全局流转说明（通俗版）.md`
* 仓库内现有文档已明确：
  * Claude Code 以 `.claude/commands/trellis/*.md`、`AGENTS.md`、`.claude/settings*.json`、`.claude/agents/*.md` 承载
  * OpenCode 以 `.opencode/commands/trellis/*.md`、`.opencode/agents/*.md`、`AGENTS.md`、`opencode.json.instructions` 承载
  * Codex 不走项目级 slash command 目录，当前文档将其描述为 `AGENTS.md`、`.codex/config.toml`、`.codex/hooks.json`、skills、`.codex/agents/*.toml` 等组合承载

## Assumptions (temporary)

* 当前需要优先修正的是 workflow 文档表述、入口映射和平台展开层说明，而不是先重构技能目录或打乱现有 Trellis 技能分层
* 现有文档中可能已经部分跟上新版本，但仍存在与最新官方格式或当前 Trellis 口径不完全一致的地方
* 本轮 brainstorm 先收敛“修哪些文档、怎么修、修到什么深度”，再进入具体改文

## Open Questions

* 这次升级是只做文档口径与结构修正，还是也要同步补充示例片段、命令树和安装后目标目录示意？
* 用户希望本轮优先修正“准确性偏差”，还是顺带做“阅读路径与信息分层”的整理？

## Requirements (evolving)

* 只修改 `docs/workflows/新项目开发工作流/` 下文件
* 修正内容必须与 Claude Code / Codex / OpenCode 的原生使用方式一致
* 在正式修改前，先输出修正思路并获得用户确认
* 保持多 CLI 同装主叙事与阶段主链的一致性
* Codex 相关修正不得把 `.agents/skills/` 简单改写为唯一推荐路径，避免影响其他 CLI 的共享技能含义
* Codex 文档采用分层说明：
  * `.agents/skills/` = Trellis 共享技能层
  * `.codex/skills/` = Codex 本地生效 / Codex 专属技能层
  * workflow 在 Codex 中可同时依赖两层，但职责不同
* 当文档说明“当前工作流如何判断 Trellis 版本升级后的兼容升级”时，参考基线必须定义为：
  * 在 `/tmp` 下新建临时项目
  * 执行 `trellis init`
  * 以该纯净初始化产物作为“初始 Trellis 框架代码”参考
* 禁止把当前仓库内已被项目化修改过的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 资产直接当作“初始 Trellis 基线”

## Acceptance Criteria (evolving)

* [ ] 给出当前 workflow 文档中需要升级的关键点清单
* [ ] 给出 Claude Code / Codex / OpenCode 各自的原生适配修正方案
* [ ] 用户确认方案后，才进入具体修改
* [ ] 修改后文档之间的入口、术语、安装时序和承载关系保持一致
* [ ] Codex 文档能清楚区分 Trellis 共享技能层与 Codex 生效层，不误伤其他 CLI 的技能语义
* [ ] 文档明确写出：兼容升级判断所用的“初始 Trellis 基线”来自 `/tmp` 临时项目中的 `trellis init` 纯净产物，而不是当前仓库

## Definition of Done (team quality bar)

* 方案说明清楚修正范围、修正理由、影响文件
* 文档变更只发生在目标目录内
* 相关文档交叉引用不自相矛盾
* 如有可验证命令，完成相应校验

## Out of Scope (explicit)

* 修改 `docs/workflows/新项目开发工作流/` 之外的仓库文件
* 直接改目标项目的 `.claude/`、`.opencode/`、`.codex/` 实际部署产物
* 在未确认方案前直接批量重写 workflow 文档

## Technical Notes

* 已检索到与三套 CLI 适配直接相关的现有文档：
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
* 外部原生格式证据已初步查到：
  * Anthropic Claude Code 官方 slash command 文档说明项目命令位置是 `.claude/commands/`，且**命令名来自 markdown 文件名本身**；子目录只影响描述展示，不改变命令名
  * OpenCode 官方命令文档说明项目命令位置是 `.opencode/commands/`，且**命令名来自 markdown 文件名本身**，在 TUI 中以 `/name` 触发；官方 rules 文档说明 `AGENTS.md` 是原生规则入口；官方 skills 文档说明原生技能目录优先是 `.opencode/skills/`
  * Codex 官方文档已明确提供 `AGENTS.md`、hooks、skills、subagents、built-in slash commands；官方 skills 文档当前列出的 repo 级技能目录是 `.agents/skills/`，未见 `.codex/skills/` 作为原生项目路径

## Research Notes

### What similar tools do

* Claude Code：
  * 项目命令放在 `.claude/commands/`
  * 命令名来自文件名，例如 `review.md -> /review`
  * 子目录只是组织用途，不会把命令变成 `/namespace:review`
* OpenCode：
  * 项目命令放在 `.opencode/commands/`
  * 命令名来自文件名，例如 `test.md -> /test`
  * 原生规则入口是 `AGENTS.md`
  * 原生 skills 目录是 `.opencode/skills/`，同时兼容 `.claude/skills/` 和 `.agents/skills/`
* Codex：
  * workflow 入口依赖 `AGENTS.md`、hooks、skills、subagents
  * repo 级 skills 原生发现路径是 `.agents/skills/`
  * slash commands 是 Codex 自身 built-in 控制命令，不等于项目自定义 workflow 命令目录

### Constraints from our repo/project

* 当前 workflow 大量文档把 Claude / OpenCode 的阶段入口写成 `/trellis:<phase>` 或 `trellis/<phase>`
* 当前安装器把 Claude / OpenCode 阶段文件部署到 `.claude/commands/trellis/<phase>.md` 与 `.opencode/commands/trellis/<phase>.md`
* 进一步核对后确认：当前 Trellis 框架本身已经把 `.claude/commands/trellis/`、`.opencode/commands/trellis/` 视为稳定命名空间约定，且该约定贯穿：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  * 当前仓库已部署的 `.claude/commands/trellis/`、`.opencode/commands/trellis/` 资产
* 因此本轮升级不能简单把 `/trellis:*` 叙事判定为“必须删除的旧写法”；更合理的做法是把它定义为 **Trellis 在官方自定义命令能力之上建立的项目级 namespace 约定**
* 当前 Codex 安装器与文档仍保留 `.codex/skills/` 兜底口径，这与官方当前公开项目路径不完全一致
* OpenCode 现有文档强调 `.opencode/commands/` 与 `opencode.json.instructions`，但尚未把 `.opencode/skills/` 作为原生技能目录讲清楚
* 仓库当前实际状态是：
  * `.agents/skills/` 中承载 `start`、`brainstorm`、`finish-work` 等 Trellis 共享技能
  * `.codex/skills/` 中存在 Codex 侧技能资产（当前至少有 `parallel`）
* 因此更合理的修法不是“用 `.agents/skills/` 替换 `.codex/skills/`”，而是把两层职责边界写清：
  * 哪些是 Trellis 共享技能
  * 哪些是 Codex 本地生效或 Codex 专属技能
* 当前仓库内的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 已经承载了本项目自己的项目化修改，因此只能作为“当前已落地实现参考”，不能被文档表述成“初始 Trellis 基线代码”
* 若要判断 Trellis 升级后 workflow 是否仍兼容，正确参考对象应是 `/tmp` 临时项目执行 `trellis init` 后得到的纯净基线，再与 workflow 需要注入的补丁点做比对

## Decision (ADR-lite)

**Context**: 需要决定 Codex workflow 技能目录在文档中如何表述，既要符合当前 Trellis 的多 CLI 技能结构，又不能因为收敛到单一路径而误导或影响其他 CLI。

**Decision**: 采用“双层职责说明”：

* `.agents/skills/` 作为 Trellis 共享技能层
* `.codex/skills/` 作为 Codex 本地生效 / Codex 专属技能层
* 文档中不把任一目录简单写成“唯一正确路径”，而是明确 workflow 在 Codex 中可同时依赖两层，但承担不同职责

**Consequences**:

* Codex README、总纲、命令映射需要补齐两层边界说明
* 安装脚本文案如有涉及路径优先级，应改为“共享层 + Codex 生效层/兼容层”的表述
* 可以保留当前 Trellis 技能结构，不引入对其他 CLI 的副作用

## Decision (ADR-lite) - Compatibility Baseline

**Context**: 需要定义“当 Trellis 版本升级时，当前工作流拿什么作为兼容升级判断的初始 Trellis 框架代码”。若直接引用当前仓库内的 `.trellis/`、`.claude/`、`.opencode/`、`.codex/`，会把本项目已经做过的项目化修改误当成 Trellis 原始基线。

**Decision**: 兼容升级判断的 Trellis 初始基线统一定义为：

* 在 `/tmp` 下新建临时项目
* 对该临时项目执行 `trellis init`
* 以初始化后得到的纯净 Trellis 产物作为参考基线

当前仓库内的 Trellis 相关目录只用于理解“本项目当前实际落地实现”，不作为“初始 Trellis 框架代码”基线。

**Consequences**:

* 工作流文档需要明确区分“纯净 Trellis 基线”与“当前项目已项目化资产”
* 兼容升级描述应说明：判断流程基于 `/tmp` 纯净基线、目标项目当前安装状态、以及 workflow 自身补丁三者的对照
* 后续如补充验证步骤，优先写成 `/tmp` fixture / smoke test，而不是拿当前仓库直接当基线样本

### Feasible approaches here

**Approach A: 与当前 Trellis 兼容的严格原生对齐** (Recommended)

* How it works:
  * 保留当前 Trellis 已经稳定使用的 `.claude/commands/trellis/`、`.opencode/commands/trellis/` 命名空间与阶段主链，不打乱既有安装器、测试和 hooks 假设
  * 在文档中明确区分两层：
    * CLI 官方原生能力：项目命令 / rules / hooks / skills / agents
    * Trellis 项目级约定：在官方能力之上统一收敛为 `trellis` workflow namespace
  * 修正真正过时或不准确的口径，例如：
    * OpenCode 原生 `.opencode/skills/` 的说明缺位
    * Codex 文档未清楚区分 `.agents/skills/` 的 Trellis 共享层与 `.codex/skills/` 的 Codex 生效层
  * 如有必要，同步调整 `install-workflow.py` / `uninstall-workflow.py` 的提示文案，使其反映“共享层 + Codex 生效层/兼容层”的关系，而不是粗暴收敛为单一路径
* Pros:
  * 既保持与当前 Trellis 一致，又能修掉真正落后的原生适配口径
  * 不会打乱现有 workflow 主叙事、安装器和测试资产
  * 后续维护时更容易说明“哪些是 CLI 原生能力，哪些是 Trellis 统一约定”
  * 能避免把 Codex 的技能目录调整误伤到其他 CLI 的共享技能体系
* Cons:
  * 文档表述会更讲究分层，不能简单写成“这就是 CLI 官方默认入口”
  * 仍需要决定 Codex 兼容 fallback 是否保留

**Approach B: 文档纠偏 + 安装器暂不动**

* How it works:
  * 先在文档中明确哪些入口是“当前 workflow 约定”，哪些是“官方原生入口”
  * 不立即调整安装器目录结构，只修正文档里的错误官方表述与证据边界
* Pros:
  * 改动更小，风险更低
  * 能先把最明显的误导收口
* Cons:
  * 仍会保留目录结构与官方口径之间的张力
  * 严格来说不算完全原生适配

**Approach C: 分层修正**

* How it works:
  * 先严格修正 Codex 与 OpenCode 的原生路径和调用表述
  * Claude 部分先标注“当前采用团队约定命令层，需单独验证是否继续维持 `/trellis:*` 叙事”
* Pros:
  * 先解决证据最明确、偏差最大的部分
  * 便于分阶段推进
* Cons:
  * 三个 CLI 的改法不完全同步
  * 会让这一轮升级留下一部分未闭环项

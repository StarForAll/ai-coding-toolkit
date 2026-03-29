# brainstorm: 评估并优化 trellis spec 适配性

## Goal

站在本项目“实际承担的工作内容”角度，评估 `.trellis/spec/` 中现有规范是否合适、哪些规范过泛或失焦、哪些规范对当前仓库是真正必要的，并在真正修改前先形成统一说明与改动边界，供用户确认。

## What I already know

* `README.md` 明确本仓库是“AI 编程工具箱”，沉淀可复用资产：规范、模板、agent、命令、skills、多工具配置。
* `README.md` 同时将 `.trellis/spec/` 描述为“本仓库自己的维护规范层，不是 `trellis-library/specs/` 的镜像目录”。
* `.trellis/spec/index.md` 将 `.trellis/spec/` 定义为“repository-local maintenance layer”，强调这里只应保留仓库本地维护规范。
* 实际目录中除 `library-assets/`、`scripts/`、`agents/`、`commands/`、`skills/`、`docs/`、`guides/` 外，还存在大量 `universal-domains/`、`templates/`、`checklists/`、`examples/`、`platforms/` 内容。
* `docs/workflows/**`、历史任务 PRD、任务上下文文件已经在引用其中一部分通用规范与模板，说明这些内容并非纯粹噪音。
* 当前 `task_context.py` 已做兼容：在本 meta-project 中优先回退到真实存在的 `.trellis/spec/index.md`，说明项目工作流确实依赖 `.trellis/spec/` 作为实际规范入口。
* 用户已确认：`docs/workflows/**` 也是本项目的一等资产，`.trellis/spec/` 必须正式覆盖这类工作流资产的规范需求。
* `docs/workflows/自定义工作流制作规范.md` 与 `docs/workflows/新项目开发工作流/工作流总纲.md` 明确把 `product-and-requirements` 相关 spec/template/checklist 作为工作流嵌入后的最低门禁集合。
* `ai-execution/tool-call-policy` 与 `verification/evidence-requirements` 的适用范围直接面向 AI-assisted workflows，与本项目“AI 工作流工具箱”的实际职责高度吻合。

## Assumptions (temporary)

* 当前主要问题不只是“定位说明不统一”，还可能存在“规范集合超出当前项目真正需要的最小闭包”。
* 用户希望从“本项目实际作用”出发判断规范是否合适，而不是从导入机制角度讨论。
* 若要优化，应按项目职责筛选规范：保留真正支撑资产库维护、工具资产编写、工作流资产编写的部分；收缩与当前仓库职责弱相关的内容。

## Open Questions

* 评估“当前项目实际作用”时，是否应把 `docs/workflows/**` 这类工作流资产也视为 `.trellis/spec/` 必须覆盖的正式范围？

## Requirements (evolving)

* 给出 `.trellis/spec/` 当前状态的事实判断。
* 从项目实际职责出发，对规范进行“必要 / 可选 / 过泛”分类。
* 识别当前说明、实际用法、资产类型三者之间的冲突点。
* 在修改前先输出统一说明和可选改法，等待用户确认。

## Preliminary Fit Assessment

### 必要（与当前项目职责直接匹配）

* `library-assets/`：直接服务 `trellis-library/` 资产库维护
* `scripts/`：直接服务 `.trellis/scripts/` 与 `trellis-library/scripts/`
* `agents/`、`commands/`、`skills/`、`docs/`、`guides/`：直接服务本仓库源资产与文档维护
* `universal-domains/ai-execution/*`：直接服务 AI 工作流命令与工具调用规则
* `universal-domains/context-engineering/*`：直接服务多轮 AI 工作流、上下文注入、摘要与污染控制
* `universal-domains/agent-collaboration/*`：直接服务 agent / subagent / handoff 类工作流设计
* `universal-domains/verification/*`：直接服务验证门禁、证据约束、自审与交付检查
* `universal-domains/project-governance/*` 中与 change / decision / risk / library sync 相关部分：直接服务工作流治理与库同步治理
* `universal-domains/product-and-requirements/*`：已被 `docs/workflows/**` 明确作为需求发现与 PRD 阶段的规范基线

### 可选（有价值，但需要收敛表述或入口）

* `templates/**`、`checklists/**`、`examples/**`：对工作流资产有支持作用，但更像“配套资产导航层”，不一定都应在 `.trellis/spec/index.md` 顶层被等价呈现
* `platforms/cli/command-interface/*`：如果工作流资产持续产出 CLI 命令规范，则保留合理；否则需要更清楚说明它服务的是“工作流/命令设计”而非普通应用 CLI

### 需要审视（不一定删除，但可能失焦）

* 首页把 `.trellis/spec/` 仅定义成“仓库本地维护规范层”过窄，无法覆盖工作流资产实际依赖的通用规范
* 顶层入口没有区分“仓库维护规范”与“工作流设计/方法论规范”，导致读者误以为 `product-and-requirements` 等内容越界
* 一部分模板/示例/清单如果没有在当前仓库工作流中形成明确入口，容易显得过泛

## Acceptance Criteria (evolving)

* [ ] 能明确指出 `.trellis/spec/` 当前承担的实际角色，而不是只复述 index 文案。
* [ ] 能从项目职责出发，把规范分成至少“必要 / 可选 / 过泛”三类。
* [ ] 能列出至少 2-3 个有证据支撑的冲突点或优化点。
* [ ] 能给出可执行的改动边界选项，便于用户确认。
* [ ] 在用户确认前，不直接修改 `.trellis/spec/` 内容。

## Definition of Done (team quality bar)

* 结论有仓库内证据支撑
* 修改边界和风险明确
* 用户完成方向确认后再进入实施

## Out of Scope (explicit)

* 本轮不直接改写所有 `.trellis/spec/**` 文件
* 本轮不处理 `trellis-library/` 上游资产内容本身是否优劣
* 本轮不讨论“是否再次导入”
* 本轮不设计新的同步脚本实现

## Technical Notes

* 关键证据文件：
  * `.trellis/spec/index.md`
  * `.trellis/spec/guides/index.md`
  * `.trellis/spec/agents/index.md`
  * `.trellis/spec/commands/index.md`
  * `README.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `.trellis/scripts/common/task_context.py`
* 当前从项目职责看，仓库至少覆盖三类工作：
  * `trellis-library/` 资产库维护
  * `agents/commands/skills` 等工具资产与部署规范维护
  * `docs/workflows/**` 工作流资产编写与验证
* 因此，适配性判断应围绕三类规范价值：
  * 是否直接支撑本仓库资产编写
  * 是否直接支撑工作流文档与命令设计
  * 是否只是“概念上通用但在本仓库内没有明确落点”

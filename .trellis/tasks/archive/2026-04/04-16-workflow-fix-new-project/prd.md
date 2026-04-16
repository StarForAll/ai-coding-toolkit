# brainstorm: 修复新项目开发工作流

## Goal

基于 `docs/workflows/新项目开发工作流` 当前实现，分析并提出一套面向 Claude Code / Codex / OpenCode 的修复完善方案，优先保持 Trellis 框架核心约束，并在涉及 Trellis 联动时先用 `/tmp` 纯净初始化项目对照真实基线。本轮仅输出分析与修改方案，不直接落地修改。

## What I Already Know

* 分析与后续修改范围限定在 `docs/workflows/新项目开发工作流/`
* 涉及 Trellis 联动时，需要先在 `/tmp` 创建临时项目并执行 `trellis init`
* 需要按 Claude Code / Codex / OpenCode 官方原生格式适配，但以 Trellis 框架核心为前提
* 待优化点：
* A. 任务开发阶段新开任务前，需要先向用户说明该任务信息
* B. `feasibility` 阶段首次进入 workflow 时必须执行；若已形成有效 `assessment.md` 且仍在有效上下文内，则不需要重复执行
* C. 无论项目是否外包，法律风险分析都必须在一开始的 feasibility 阶段执行
* `工作流总纲.md` 已明确：维护 workflow 源内容时，Trellis 兼容基线必须来自 `/tmp` 临时项目 + `trellis init`
* `commands/brainstorm.md` 当前仍把 `/trellis:feasibility` 写成“新项目默认前置”，但需要继续核对是否有其他入口允许绕过
* `commands/start-patch-phase-router.md` 当前在“无 `.current-task` + 新项目/新客户/首次立项”时路由到 `/trellis:feasibility`

## Assumptions (Temporary)

* 需要同时修改规则文档、walkthrough、命令映射，以及可能触发该行为的命令补丁或 helper script 说明
* “先说明任务信息”主要影响 `plan` / `start` / 任务创建前的交互文案与门禁，不一定需要改 `task.py` 本身
* “法律风险分析”应成为所有项目在 feasibility 起始处的通用硬门禁，而不是仅外包场景附加项
* `feasibility` 允许复用已完成且仍有效的评估结果，但不允许在首次入口时被绕过

## Open Questions

* `/tmp` 纯净 Trellis 初始化产物与当前 workflow 安装后的入口差异，具体会影响哪些文档和补丁点

## Requirements (Evolving)

* 梳理当前 workflow 中与 `feasibility`、任务创建说明、法律风险、CLI 原生适配、Trellis 联动相关的真实现状
* 对照 `/tmp` 纯净 Trellis 基线，识别当前 workflow 文档/补丁是否存在与 Trellis 主链冲突或遗漏
* 输出针对优化点 A/B/C 的修改方案，并说明涉及文件与改法
* 明确 `feasibility` 的复用条件：已执行且 `assessment.md` 有效时不重跑，首次入口时不得跳过
* 明确法律风险分析必须位于 feasibility 最开头，而不是后置到外部项目分支或交付控制分析之后
* 本轮不进行具体修改，需等待用户确认方案后再实施

## Acceptance Criteria (Evolving)

* [ ] 已明确 A/B/C 三项问题在当前 workflow 中的根因位置
* [ ] 已给出兼顾 Trellis 核心与 Claude Code / Codex / OpenCode 原生适配的修改方案
* [ ] 已说明建议修改的文件范围与修改原因
* [ ] 本轮未直接改动 workflow 源文件

## Definition of Done (team quality bar)

* 方案基于当前仓库证据与 `/tmp` 纯净 Trellis 基线
* 明确哪些已完成分析、哪些仍待用户确认
* 修改建议能映射到具体文档/命令/脚本承载点

## Out of Scope (explicit)

* 本轮不直接编辑 `docs/workflows/新项目开发工作流/` 中的文件
* 本轮不处理当前项目中其他 workflow 目录
* 本轮不做提交、安装到真实目标项目或兼容升级落地

## Technical Notes

* 关键入口文档：`工作流总纲.md`、`命令映射.md`、`多CLI通用新项目完整流程演练.md`
* 关键命令：`commands/feasibility.md`、`commands/brainstorm.md`、`commands/start-patch-phase-router.md`
* 关键 helper：`commands/shell/feasibility-check.py`
* 需进一步检查 Claude / OpenCode / Codex 适配 README、安装脚本与阶段状态机协议

## Workflow Decisions

* Accuracy Status: analyzing
* Complexity: L1
* Need More Divergence: yes
* Need Sub Tasks: no
* Next Step: inspect Trellis baseline and workflow source files

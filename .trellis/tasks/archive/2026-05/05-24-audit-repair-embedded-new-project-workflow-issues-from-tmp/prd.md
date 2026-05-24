# audit and repair embedded new project workflow issues from tmp fixture

## Goal

以 `/tmp/trellis-0.5.17-2` 作为已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目样本，逐条验证候选问题是否真实存在；若存在，仅在 `docs/workflows/新项目开发工作流/` 范围内设计并实施安全修复，使后续嵌入该 workflow 的目标项目不再复现同类问题。

## What I already know

- 用户明确要求：判断对象是 `/tmp/trellis-0.5.17-2`，修复落点只能在 `docs/workflows/新项目开发工作流/`，其他目录不能修改；当前任务目录可写且无需删除。
- 当前仓库是 workflow authoring source repo，不是被修复的目标项目；`docs/workflows/**` 下内容属于产品资产。
- `workflow-repair` 要求：所有候选问题都必须先在 temp project 取证，再回到 workflow source 判断根因和修复方式；Treillis-native 问题只能通过 workflow 内补丁/安装逻辑修复。
- `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` 显示当前嵌入记录包含：
  - `initial_pack = pack.requirements-discovery-foundation`
  - `patched_shared_docs = ["workflow.md"]`
  - `patched_codex_skills = ["trellis-continue", "trellis-finish-work", "trellis-start"]`
  - `critical_runtime_patches` 7 项
  - `bootstrap_task_removed = true`
  - `bootstrap_cleanup_status = "removed"`
- `/tmp/trellis-0.5.17-2/.trellis/` 中确实存在 `library-assets/`、`checklists/`、`templates/`、`.backup-original/workflow.md`、`.trellis/scripts/workflow/workflow-state.py` 与两张 execution cards。
- 历史 `tmp/workflow-issues/*.md` 已记录多轮同类 scan/repair，说明必须避免重复修复同一个“伪问题”，并优先关注仍未闭环的真实缺陷。

## Assumptions (temporary)

- 用户当前轮要求先完成分析并给出修复方案，得到确认后再动 `docs/workflows/新项目开发工作流/`。
- 候选问题中会混杂三类项：
  - 真实 defect，且属于 workflow source 可修复范围
  - 真实现象，但属于 Trellis native 或当前合同的刻意设计，不应修复
  - 文档/记录不透明或联动面不足，属于 contract/documentation gap，需要补强记录与校验

## Open Questions

- `workflow-state.json` 的版本字段与 repair/recovery 支路，哪些是“文档描述缺少闭环”，哪些是“脚本行为真实缺失”？
- `workflow.md` patch、library asset 导入、bootstrap cleanup 等现象，当前安装记录与 uninstall/upgrade 逻辑是否足以支撑恢复和升级，还是缺少必要 schema / docs / tests？
- finish-work checklist、NL routing、task.py start 行为、execution cards 绑定等是否还有未被历史修复覆盖的同类漂移点？

## Requirements (evolving)

- 逐条核验用户列举的候选问题，不得直接采信。
- 一旦确认某问题存在，必须在 `docs/workflows/新项目开发工作流/` 内扫描同类模式，一并修复安全 sibling。
- 若问题属于 `trellis-native`，需要在 workflow 内通过安装/补丁/校验逻辑闭环，而不是修改 repo 其他位置。
- 修复前必须先向用户提交“确认存在的问题 + 修复方案”，等待同意。
- 修复后需要做相关测试/校验，并如实报告 pass / fail / not run。

## Acceptance Criteria (evolving)

- [ ] 形成一份基于 `/tmp/trellis-0.5.17-2` 证据的候选问题判定清单，区分真实问题、非问题、证据不足。
- [ ] 对每个真实问题给出根因、修复落点、同类扫描范围与副作用控制。
- [ ] 用户确认后，仅修改 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- [ ] 修复完成后运行相关测试/校验，结果可追溯。

## Definition of Done (team quality bar)

- 真实问题与伪问题有清晰证据边界
- 修复不越界到 `docs/workflows/新项目开发工作流/` 之外
- 相关测试/静态校验已运行或明确说明未运行原因
- 需要同步的文档、脚本、测试、安装记录合同面已在同一修复批次内保持一致

## Out of Scope (explicit)

- 修改 `/tmp/trellis-0.5.17-2` 目标项目内容本身
- 修改当前仓库 `docs/workflows/新项目开发工作流/` 之外的产品源码
- 仅因为“看起来不优雅”而进行无证据优化

## Technical Notes

- 关键约束来源：
  - `.agents/skills/workflow-audit/SKILL.md`
  - `/ops/data/ai/skills/workflow-repair/SKILL.md`
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  - `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  - `.trellis/spec/docs/index.md`
- 已读取 temp-project 核心证据：
  - `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `/tmp/trellis-0.5.17-2/.trellis/.backup-original/workflow.md`
  - `/tmp/trellis-0.5.17-2/AGENTS.md`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`

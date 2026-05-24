# audit and repair embedded new-project workflow

## Goal

审计 `docs/workflows/新项目开发工作流/` 作为源工作流在目标项目 `/tmp/trellis-0.5.17-2` 中的实际嵌入行为，判断用户列出的候选问题是否真实存在，并识别同类问题。只在确认真实缺陷后提出源侧修复方案；在得到用户同意前，不修改 `docs/workflows/新项目开发工作流/`。

## What I Already Know

- 当前仓库是 workflow authoring source project，修复范围必须限制在 `docs/workflows/新项目开发工作流/`。
- `/tmp/trellis-0.5.17-2` 是 `trellis init` 后嵌入当前工作流的目标项目，可用于判断安装后真实行为。
- 版本门禁已通过：
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`
  - `trellis -v` 输出 `0.5.17`
- 当前嵌入工作流的强门禁核心由 `workflow-state.py route`、`workflow-state.json`、patch helpers、validators 和命令/skill 文档共同构成。
- `/tmp/trellis-0.5.17-2` 里 `task.py list` / `common.tasks` 已被补丁改造成基于 `workflow-state.json.stage` 的展示与过滤，不再直接把 `task.json.status` 当作活动阶段真相源。
- `workflow-state.py repair` 已对执行阶段缺失 `--execution-authorized true` / `--transition-from` 的场景实现 `manual_confirmation_required` 硬阻断。
- personal 首次入口补 assessment 的规则，当前已在 `brainstorm.md`、`workflow-state.py route/validate`、`state_utils.is_personal_brainstorm_bootstrap_allowed()` 中落地为“允许在 brainstorm 内补齐，但离开前强制补齐”。
- `plan` / `design` 的 `Context7` 相关文档，已把“直接相关 spec”进一步限定为“能被第三方官方文档约束的 spec 必须复核；纯内部流程/团队约定/项目私有约束不强制 Context7”。

## Assumptions (Temporary)

- 可以在 `/tmp/trellis-0.5.17-2` 中创建最小测试任务用于运行时验证；这些临时任务不需要在本轮结束后删除。
- 用户希望本轮先得到“真实问题 + 修复方案 + 影响面”，确认后再执行源侧修复。

## Open Questions

- `embed_integrity.py` 的 marker-based 检查是否在当前合同下构成真实误报/误阻断，而不是有意的完整性门禁。
- `_workflow_display_extra` 是否仅存在“文档未说明”的可维护性问题，还是会造成用户可见行为歧义。
- “触发词”文案是否只是命名不理想，还是已经和实际自动路由规则发生真实错配。
- 在显式禁用 agent/subagent 路径后，implementation 内部 research 的能力边界是否仍存在遗漏文档或运行时缺口。

## Requirements (Evolving)

- 对用户列出的每个候选问题做“真实存在 / 不成立 / 已被当前实现覆盖 / 部分成立”的分类。
- 结论必须同时包含 source repo 证据与 `/tmp/trellis-0.5.17-2` 目标项目证据。
- 若发现同类问题，纳入同一修复批次。
- 在用户同意前，只输出修复方案，不修改 `docs/workflows/新项目开发工作流/`。

## Acceptance Criteria (Evolving)

- [ ] 给出逐项候选问题的审计结论和证据。
- [ ] 给出真实问题的修复方向、影响面和同类问题合并策略。
- [ ] 明确哪些问题不应修、原因是什么，避免引入回归。

## Out of Scope

- 不修改 `docs/workflows/新项目开发工作流/` 之外的源仓库目录。
- 不处理超出该工作流 source 侧合同的 Trellis 原生上游缺陷，除非需要在工作流安装器/补丁层做兼容修复。
- 不在本轮未获批准前直接实施源侧修复。

## Technical Notes

- 审计重点文件：
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/embed_integrity.py`
  - `docs/workflows/新项目开发工作流/commands/{brainstorm,plan,start-patch-phase-router}.md`
  - `docs/workflows/新项目开发工作流/{工作流总纲.md,命令映射.md,需求变更管理执行卡.md,工作流全局流转说明（通俗版）.md}`
- 目标项目已验证文件：
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/common/{tasks.py,task_queue.py}`
  - `/tmp/trellis-0.5.17-2/AGENTS.md`
- 关键已知运行结果：
  - `trellis -v` => `0.5.17`
  - `workflow-state.py route --project-root /tmp/trellis-0.5.17-2` => `entry_choice_required`, `target=feasibility`, `profile_hint=outsourcing`

## Audit Status

- Current phase: evidence gathering
- Candidate issues under validation:
  - status 双真相源
  - repair/route/profile/assessment 行为
  - Context7 复核范围定义
  - embed_integrity marker 误报/阻断
  - validators 调用链与 `_workflow_display_extra` 文档化
  - Baseline compatibility / 触发词 / 纯澄清规则
  - 禁用 subagent 后 implementation research 能力边界

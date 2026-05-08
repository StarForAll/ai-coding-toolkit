# 修正 workflow-capability-audit 与当前 trellis 机制对齐

## Goal

修正 `workflow-capability-audit` 对当前 Trellis 运行时机制的理解偏差，使其脚本、skill、spec、runbook、测试与本仓库真实实现保持一致。重点覆盖会话级 active task、平台 hook/config carrier、共享/次级 skills carrier、Trellis hooks script carrier，以及更细粒度的“存在但受 gate 控制”分类。

## What I already know

* 当前仓库的 active task 已经是会话级模型，状态写入 `.trellis/.runtime/sessions/`，而不是旧的 `.trellis/.current-task`。
* `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py` 仍直接读写 `.trellis/.current-task`，与当前 Trellis 机制不一致。
* 当前 Codex 只有 `UserPromptSubmit` hook 载体，且还受用户级 feature gate 和 hook 审批控制，不应再被建模为固定具备 `session-start.py`。
* 当前仓库没有 `.trellis/hooks/` 目录，实际存在的是 `.trellis/scripts/hooks/linear_sync.py` 等生命周期 hook 脚本载体。
* `.agents/skills/` 不只是 OpenCode/Codex 的 shared skills carrier，也承担 repo-local shared deployment layer 角色。

## Assumptions

* 本次改动范围包含脚本、测试、repo-local maintainer skill、spec 和 references。
* 现有测试 `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py` 是主要回归入口。
* 不需要改动 workflow 根路径或版本锚点语义，本次重点是机制对齐和增强分类。

## Requirements

* `workflow-capability-audit.py` 必须改为复用 `.trellis/scripts/common/active_task.py` 的会话级 active task API。
* full audit 失败回滚时必须恢复当前会话任务状态，不能再依赖 `.trellis/.current-task`。
* dependent carrier 定义必须与当前仓库实际接线一致。
* capability matrix 需支持更细粒度的条件化分类，至少覆盖 Codex hook/config 的 present-but-gated 场景。
* 相关 skill/spec/runbook/template 文档必须同步更新，避免协议漂移。
* 测试必须覆盖任务恢复、carrier 重新定义、增强分类与说明文字。

## Acceptance Criteria

* [ ] `workflow-capability-audit.py` 不再直接读写 `.trellis/.current-task`。
* [ ] 测试能够证明 full audit 创建/回滚时按会话上下文恢复 active task。
* [ ] Codex carrier 相关矩阵输出不再错误要求 `.codex/hooks/session-start.py`。
* [ ] `.trellis/scripts/hooks` 被正确建模为 Trellis-side hooks script carrier。
* [ ] 能在 capability report 中区分至少一种 feature-gated / conditional presence 状态。
* [ ] `.agents/skills/workflow-capability-audit/` 与 `.trellis/spec/skills/workflow-capability-audit.md` 同步描述新机制。

## Definition of Done

* 相关 Python 测试通过
* 相关技能结构校验通过
* 脚本、skill、spec、reference 同步完成
* 最终说明中明确实际验证结果与剩余风险

## Out of Scope

* 改动 `COMPATIBLE_TRELLIS_VERSION` 版本锚点语义
* 扩展到 `docs/workflows/*` 多 workflow 通用支持
* 重写整个 capability audit 报告格式

## Technical Notes

* 关键实现文件：
  * `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py`
* 关键规范文件：
  * `.trellis/spec/skills/workflow-capability-audit.md`
  * `.agents/skills/workflow-capability-audit/SKILL.md`
  * `.agents/skills/workflow-capability-audit/references/execution-runbook.md`
* 关键 Trellis API：
  * `.trellis/scripts/common/active_task.py`

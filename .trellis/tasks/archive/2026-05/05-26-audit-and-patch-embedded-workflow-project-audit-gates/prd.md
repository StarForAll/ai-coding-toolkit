# audit and patch embedded workflow project-audit gates

## Goal

修复 `docs/workflows/新项目开发工作流/` 中与 `check` / `project-audit` / `delivery` 联动相关的真实门禁缺陷，确保嵌入到目标项目后，任务级 `check` 与项目级 `project-audit` 保持维度分离，但进入 `delivery` 前需要满足一致的双门禁约束。

## What I already know

- 审计对象是 `docs/workflows/新项目开发工作流/` 的源资产，运行对照样本是 `/tmp/trellis-0.5.17-2`。
- 当前已确认的真实问题包括：transition gate 与 delivery gate 对 formal `PROJECT-AUDIT` 的要求不一致、`project_audit_code_changes` 出口约束过窄、`review-gate` capability-gap 没有合法闭环、`workflow-state.py init --stage implementation` 会生成非法状态、`awaiting_user_confirmation` 冗余字段仍会落盘、native `finish-work` 缺少可执行 delivery gate 校验入口。
- 已确认的误判包括：把“delivery 同时需要当前 active task 的 `check.md` 与 formal `PROJECT-AUDIT` carrier”误判为 carrier 混用。

## Requirements

- 只修改 `docs/workflows/新项目开发工作流/` 与当前任务目录。
- 修复不能把 `check` 与 `project-audit` 混成同一维度。
- 需要补测试，避免修复引入新的 gate 漏洞。
- 需要补 spec，避免下次再误判“维度分离但门禁联动”的场景。

## Acceptance Criteria

- [ ] `workflow-state.py set` 在 `check/review-gate -> delivery` 时会预先拦截 formal `PROJECT-AUDIT` 未满足的情况。
- [ ] `project-audit -> delivery` 与 `delivery validate` 对 formal `PROJECT-AUDIT` 的判定一致。
- [ ] `project_audit_code_changes = yes` 不再允许绕开任务级 `check` 直接去 `review-gate` / `delivery`。
- [ ] `review-gate` 对 `recommended + lite` capability-gap 存在合法、受控、可审计的 `not_run` 闭环。
- [ ] `workflow-state.py init --stage implementation` 不再生成非法状态。
- [ ] `awaiting_user_confirmation` 不再作为持久化状态字段写入 `workflow-state.json`。
- [ ] workflow / skill spec 明确区分任务级 `check` 与项目级 `project-audit`，避免重复误判。

## Out of Scope

- 不扩展新的 workflow schema 字段，例如 `project_audit_required` / `project_audit_carrier`。
- 不修改 `docs/workflows/新项目开发工作流/` 以外的源码目录。

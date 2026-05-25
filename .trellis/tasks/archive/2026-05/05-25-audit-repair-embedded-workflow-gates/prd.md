# 审计并修复新项目开发工作流嵌入后门禁问题

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的临时目标项目，对当前 workflow 源目录中的门禁、文档契约、计划校验与交付控制逻辑做证据优先审计。先判断用户列出的候选问题哪些真实存在、哪些是误报或已修复；仅在用户确认修正方案后，才在 `docs/workflows/新项目开发工作流/` 范围内实施补丁，并补齐同类问题与回归测试。

## What I already know

- 目标 workflow 根目录固定为 `docs/workflows/新项目开发工作流/`。
- 证据目标项目固定为 `/tmp/trellis-0.5.17-2`。
- 修复范围仅允许落在 `docs/workflows/新项目开发工作流/`；当前任务目录例外，可用于任务记录。
- 用户要求先给出“问题裁决 + 修正方案”，得到同意后再继续改动 workflow 源文件。
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = 0.5.17`，本机 `trellis -v` 也是 `0.5.17`，满足 same-version audit 前提。

## Assumptions

- `/tmp/trellis-0.5.17-2` 中的已嵌入脚本与命令文档可作为 workflow 当前实际安装结果的有效证据。
- 本轮先不修改 workflow 源文件；若用户确认方案，再进入实现阶段并补齐测试。
- 若发现候选问题已经在源 workflow 中部分修复，仍需判断是否存在残留逻辑漏洞或文档/脚本漂移。

## Open Questions

- 候选问题 1-8 中哪些是真实 defect，哪些需要收窄描述后再修。
- 除用户列出的 1-8 外，是否存在同类未覆盖问题，应在同一轮一起修复。
- 哪些修复应同时覆盖：脚本文档契约、模板、单测、嵌入后产物一致性。

## Requirements

- 分析对象是 `/tmp/trellis-0.5.17-2` 的真实嵌入结果，不把当前仓库自身运行态误当目标。
- 只允许修改 `docs/workflows/新项目开发工作流/`，不得触碰其他源目录。
- 必须先做证据审计，再给出逐项裁决与补丁方案。
- 若某类问题存在变体或相邻缺陷，需要一起纳入修复方案。
- 最终修复不得引入新的门禁漂移、文档契约漂移或测试空洞。

## Acceptance Criteria

- [ ] 对用户列出的 1-8 每一项给出“真实存在 / 不成立 / 需收窄”的明确裁决，并附证据位置。
- [ ] 给出一套仅修改 `docs/workflows/新项目开发工作流/` 的修正方案，覆盖必要的脚本、文档、模板与测试。
- [ ] 在用户确认前，不修改 workflow 源目录中的任何文件。
- [ ] 若进入修复阶段，补丁需包含相应回归测试，能证明问题被修复且未扩大误报。

## Definition of Done

- 证据链完整：源 workflow、嵌入后目标项目、相关测试三者已交叉验证。
- 输出明确区分：已证实问题、证据不足项、误报项、潜在同类项。
- 用户确认后再进入实现；未确认前不触碰 workflow 源文件。
- 修复后需要运行相关单测/验证脚本，并如实汇报 pass / fail / not run。

## Out of Scope

- 修改当前仓库正在使用的 Trellis runtime（除 workflow 源目录以外）。
- 直接修复 Trellis 原生上游仓库；若需要，只能在 workflow 中放置补丁或安装器逻辑。
- 删除当前任务目录或清理任务记录。

## Technical Notes

- 关键源码：`commands/shell/validators_gates.py`、`commands/shell/plan-validate.py`、`commands/shell/delivery-control-validate.py`、`commands/project-audit.md`、`commands/review-gate.md`、`commands/delivery.md`、`阶段状态机与强门禁协议.md`。
- 关键实装证据：`/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/*.py` 与 `.claude/commands/trellis/*.md`。
- 关键测试：`commands/shell/test_workflow_state.py`、`commands/shell/test_delivery_control_validate.py`、`commands/shell/test_plan_validate.py`。

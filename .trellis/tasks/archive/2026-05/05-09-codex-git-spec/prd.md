# 补充 codex git 提权 spec

## Goal

为当前仓库补充一条明确的项目级平台规则：在 Codex 中执行 `git add` / `git commit` 时，优先直接使用提权方式，避免先在受限写入环境里失败再重试；该规则仅适用于 Codex，本仓库中的其他 CLI 不需要套用这条约束。

## What I already know

- 当前仓库已有 `.trellis/spec/platforms/codex-workflow-behavior.md`，用于承载 Codex 专属运行规则。
- 最近一次收尾中，Codex 下 `git add` / `git commit` 因 `.git/index.lock` 只读失败，需要改为提权重试。
- `record-session-helper.py` 已被明确收敛为 Codex 特化 close-out helper，不应自动传播到其他 CLI。
- 仓库里还没有“Codex 中 git 元数据写入直接提权”的项目级 spec 说明。

## Assumptions (temporary)

- 这次只补项目级 spec 和任务材料，不改 workflow 产品目录。
- 规则目标是指导 Codex 在本仓库中的执行习惯，不是修改 Trellis 通用脚本行为。

## Open Questions

- 无阻塞问题；规则意图明确。

## Requirements (evolving)

- 在 `.trellis/spec/platforms/codex-workflow-behavior.md` 中增加 Codex 的 git 元数据写入提权规则。
- 明确该规则仅适用于 Codex，不自动推广到 Claude / OpenCode / Qoder / Kiro。
- 如果需要，补充验证说明，便于后续 review 时检查该规则是否被遵守。

## Acceptance Criteria (evolving)

- [ ] Codex 平台 spec 明确写出：在本仓库中执行 `git add` / `git commit` 时，优先直接提权，避免先失败再重试
- [ ] 文案明确声明该规则不是其他 CLI 的通用规则
- [ ] `./scripts/validate-skills.sh` 与 `git diff --check` 通过

## Definition of Done (team quality bar)

- 平台 spec 更新完成
- 规则边界清晰，无跨平台误导
- 验证命令通过

## Out of Scope (explicit)

- 不修改 `.trellis/scripts/*`
- 不修改 `docs/workflows/新项目开发工作流/**`
- 不修改其他 CLI 的默认收尾/提交逻辑

## Technical Notes

- 主要修改文件：`.trellis/spec/platforms/codex-workflow-behavior.md`
- 参考边界：`AGENTS.md`、`docs/Trellis自动提交失败恢复与提权修复指南.md`

# 修订多 CLI 兼容矩阵与共用文案

## Goal

修订 `docs/workflows/` 下共享文档中的多 CLI 兼容矩阵、支持级别和共用措辞，使 Claude Code、OpenCode、Codex 的平台定位与当前官方能力保持一致。

## Requirements

* 更新共享兼容矩阵，不再把 OpenCode/Codex 笼统归为“基础”
* 将 Codex 与 Gemini 从同一兼容描述中拆开
* 统一修正各命令文件中的 `Cross-CLI` 行
* 共享文档只保留总原则，不写平台私有细节

## Acceptance Criteria

* [x] `自定义工作流制作规范.md` 的跨 CLI 矩阵已按平台真实能力修正
* [x] `命令映射.md` 的共用表述已区分 OpenCode 与 Codex 的参与方式
* [x] 主要命令文件的 `Cross-CLI` 标签已不再沿用旧模板

## Out of Scope

* 平台专属 README 的大篇幅重写
* hooks 或脚本实现


## Session Handoff

### Current State

* 已修订 `docs/workflows/自定义工作流制作规范.md` 的跨 CLI 矩阵与文件结构说明。
* 已修订 `docs/workflows/新项目开发工作流/命令映射.md` 的共享兼容口径。
* 已统一修订主命令文件的 `Cross-CLI` 行：
* `docs/workflows/新项目开发工作流/commands/brainstorm.md`
* `docs/workflows/新项目开发工作流/commands/check.md`
* `docs/workflows/新项目开发工作流/commands/delivery.md`
* `docs/workflows/新项目开发工作流/commands/design.md`
* `docs/workflows/新项目开发工作流/commands/feasibility.md`
* `docs/workflows/新项目开发工作流/commands/plan.md`
* `docs/workflows/新项目开发工作流/commands/self-review.md`
* `docs/workflows/新项目开发工作流/commands/test-first.md`

### Verification Evidence

* 已通过 `rg` 检索确认共享文档中不再残留 `Codex/Gemini`、`⚠️ 基础`、`当前文档适配待升级`、`当前承载方式待独立适配` 等旧模板。
* 当前工作区 diff 已显示共享文档与主命令头部文案均已切换到 OpenCode / Codex / Gemini 分列口径。

### Remaining Closure

* 尚未进行人工测试后的 commit。
* 尚未执行正式 `$record-session`。
* 子任务应视为“文档已落地，待人工收尾”。

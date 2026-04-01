# 重写 Codex 原生适配说明

## Goal

拆分并重写 `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md` 中的 Codex 部分，按 Codex 当前官方 `AGENTS.md + hooks + skills + subagents + built-in slash commands` 能力重建适配说明。

## Requirements

* 将 Codex 与 Gemini 的适配说明拆开
* 删除“没有统一的命令扩展机制”之类的过时表述
* 明确 Codex 的原生 workflow 承载模型不是照搬 Claude `.claude/commands/`
* 将仓库当前 `.codex/` 下的实际实践映射回说明文档

## Acceptance Criteria

* [x] Codex 有独立适配文档，不再与 Gemini 混写
* [x] 文档明确说明 Codex 的 AGENTS、hooks、skills、subagents 角色
* [x] 文档对“slash commands 能力”和“自定义 workflow 命令分发方式”做了边界区分

## Out of Scope

* Gemini 适配文档的完整重写
* Codex hooks 或 skills 的代码改造

## Session Handoff

### Current State

* 已新增 `docs/workflows/新项目开发工作流/commands/codex/README.md`
* 已新增 `docs/workflows/新项目开发工作流/commands/gemini/README.md`
* 已将 `docs/workflows/新项目开发工作流/commands/codex-gemini/README.md` 改为过渡说明，指向拆分后的文档
* 已同步更新共享引用：
* `docs/workflows/自定义工作流制作规范.md`
* `docs/workflows/新项目开发工作流/命令映射.md`

### Verification Evidence

* `/tmp/codex-workflow-smoke/run-report.md`
* `/tmp/opencode-workflow-smoke/run-report.md`
* `codex exec -c 'mcp_servers={}' --skip-git-repo-check -C /tmp/codex-workflow-smoke/project ...` 已验证：
* 非交互 `exec` 可正常执行模型请求
* 项目级 `AGENTS.md` 已被加载
* `SessionStart` hook 文件协议可单独执行
* 非交互 `exec` 下不应默认假设模型能看到 hook 注入的 `<ready>` 块

### Record-Session Status

* 本次未执行正式 `$record-session`
* 原因：用户要求“不进行 commit”，而 `record-session` 技能要求“人类已测试且已提交”，并且相关脚本会自动提交 `.trellis/` 元数据
* 当前保留为无提交交接状态，等待下次对话继续当前任务

### Recommended Next Step

* 回到父任务 `03-31-analyze-workflow-multi-cli-support`，整合共享层、OpenCode、Codex 三个子任务的结论
* 若仍需平台补充，可继续处理 Gemini 兼容层说明，但不要再与 Codex 混写

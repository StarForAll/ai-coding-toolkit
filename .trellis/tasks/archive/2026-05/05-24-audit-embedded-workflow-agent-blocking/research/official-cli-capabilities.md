# 官方 CLI 能力边界摘录

> 目的：证明问题不在平台“能不能”，而在当前 workflow “该不该继续暴露/鼓励”。

## Codex

来源：
- https://developers.openai.com/codex/cli
- https://developers.openai.com/codex/guides/agents-md

关键点：
- 官方 CLI 文档明确列出 `Use subagents`。
- 官方 `AGENTS.md` 文档明确说明 Codex 会在项目范围读取 `AGENTS.md`。

对应判断：
- Codex 平台本身支持 `AGENTS.md` 和 subagents。
- 因此若当前 workflow 需要禁用 subagent 路径，必须由 workflow 自己在路由/补丁层显式收口，不能把“平台支持”误当“workflow 应默认允许”。

## OpenCode

来源：
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/rules/

关键点：
- OpenCode 官方文档明确区分 `primary agents` 与 `subagents`。
- 官方文档明确说明 subagents 可被 primary agents 自动调用，也可手动 `@` 调用。
- 官方规则文档明确支持项目根 `AGENTS.md`。

对应判断：
- OpenCode 平台本身支持 agents/subagents/AGENTS 规则。
- 因此当前 workflow 如果决定不适合 subagent，必须由 installer patch 或运行时策略主动阻断，而不是只写“不建议”。

## Claude Code

来源：
- https://www.anthropic.com/news/claude-code-plugins

关键点：
- Anthropic 官方文章明确把 `slash commands`、`agents`、`hooks`、`subagents` 都列为 Claude Code 插件扩展点。

对应判断：
- Claude Code 平台本身支持这些扩展点。
- 因此本任务中需要修的是 workflow 产品层的执行约束，而不是去论证 Claude Code 没有 agent/subagent 能力。

## 总结

三家平台的官方口径都支持 agent/subagent 或对应扩展能力；所以本次候选问题的真实含义是：

1. 当前 workflow 明明希望/要求 main-session-only。
2. 但安装器、活跃 hook、NL 路由、说明文档仍在保留或鼓励 agent/subagent 路径。
3. 这就是需要在 `docs/workflows/新项目开发工作流/` 中修复的产品层问题。

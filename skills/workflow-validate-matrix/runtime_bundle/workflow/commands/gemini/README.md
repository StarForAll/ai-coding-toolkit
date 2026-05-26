# Gemini CLI 适配

Gemini 当前在这套 workflow 中仍按兼容层处理，不与 Codex 共享同一承载模型。

当前推荐做法：

- 优先使用 `commands/shell/` 下的静态校验脚本
- 必要时通过 prompt/context 注入加载 workflow 文档
- 不把 Gemini 文档写成与 Codex 等价的 `AGENTS + hooks + skills + subagents` 方案

这份文档当前只作为拆分后的占位说明，后续若要做 Gemini 原生适配，应单独起任务，不与 Codex 混改。

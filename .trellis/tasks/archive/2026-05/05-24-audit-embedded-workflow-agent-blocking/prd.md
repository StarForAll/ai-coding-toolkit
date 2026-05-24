# workflow-audit: 嵌入式 workflow 的 agent/subagent 阻断修复

## Goal

审计 `docs/workflows/新项目开发工作流/` 在目标项目嵌入后的真实行为，重点验证“该 workflow 不适合使用 agents/subagents，需要显式阻断 Claude Code / OpenCode / Codex 使用”这一候选问题是否真实存在；若存在，后续在你确认后只修改 `docs/workflows/新项目开发工作流/` 这一源码目录，通过安装器补丁和文档同步修复目标项目落盘行为。

## What I already know

- 审计对象不是当前仓库运行态，而是 `/tmp/trellis-0.5.17-2` 这个已经执行 `trellis init` 并嵌入当前 workflow 的临时目标项目。
- 版本门禁已通过：
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`
  - `trellis -v` 输出 `0.5.17`
- 当前 workflow 安装记录显示临时目标项目启用了 `claude/opencode/codex` 三种 CLI，并已落下 `inject-workflow-state`、`session-start-strong-gate`、`opencode-inject-subagent-context` 等运行时补丁。
- 初步证据表明该候选问题是真问题，不只是“文案保守提醒不够强”：
  - Claude 运行时 startup 指引仍默认要求派发 `trellis-implement` / `trellis-check`
  - OpenCode 运行时 startup 指引同样默认要求主会话 dispatch 子代理
  - OpenCode `inject-subagent-context.js` 只是在部分阶段阻断，允许阶段仍继续放行 subagent
  - Codex 的 AGENTS NL 路由与 hook 文案仍保留 skill/agent 显式触发或 `sub-agent` 模式入口

## Assumptions (temporary)

- “显式阻断”不只是改文档口径，而是需要让嵌入后的目标项目在主入口和关键运行时 carrier 上都明确回到 main session。
- 不应修改 Trellis 原生仓库；若 baseline 自带错误引导，需要在 workflow 安装器/补丁层修正。
- 允许保留平台本身支持 agent/subagent 的事实说明，但 workflow 产品层必须把它们标成“禁用/不适用当前嵌入 workflow”。

## Open Questions

- 无阻塞问题；当前已具备形成修复方案的证据。

## Requirements (evolving)

- 只分析和后续修复 `docs/workflows/新项目开发工作流/`，不修改其他源码目录。
- 先完成证据化判断与修复方案；在你确认前不改 workflow 源码。
- 若确认问题真实存在，后续修复要同时覆盖同类漏口，避免只堵一个入口。
- 修复方式应优先使用安装器补丁、生成 AGENTS 路由、文档同步和测试补齐，确保后续嵌入时自动生效。

## Acceptance Criteria (evolving)

- [x] 基于 `/tmp/trellis-0.5.17-2` 给出是否存在问题的证据化结论。
- [x] 识别出至少一组真实的运行时/路由/文档漏口，而不是只给笼统判断。
- [x] 给出只修改 `docs/workflows/新项目开发工作流/` 的可执行修复方向。
- [ ] 等你确认后，再进入源码修复。

## Definition of Done (team quality bar)

- 结论、证据、修复范围、验证方式都落到任务文件中
- 后续若进入修改，需补齐相关测试
- 不把平台原生能力误判成 workflow 缺陷；只修 workflow 产品层自己的错误承载

## Out of Scope (explicit)

- 不修改当前仓库 `.trellis/`、`.claude/`、`.opencode/`、`.codex/` 的非任务文件
- 不修改 `/tmp/trellis-0.5.17-2` 中的目标项目文件作为最终修复
- 不做 Trellis 跨版本兼容审计；本任务是 same-version workflow maintenance audit

## Technical Notes

- 主要证据文件已记录到：
  - `research/embedded-agent-subagent-evidence.md`
  - `research/official-cli-capabilities.md`
- 审计模式：task-based static（已做 `/tmp` 真实落盘比对，但尚未开始源码修复）

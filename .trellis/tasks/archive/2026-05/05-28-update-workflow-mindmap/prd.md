# 更新工作流思维导图

## Goal

根据 `docs/workflows/新项目开发工作流/` 当前对应的工作流，以及临时项目 `/tmp/trellis-0.5.17-2` 中实际嵌入后的运行面，更新 `docs/workflows/新项目开发工作流/工作流思维导图.html`，使其反映当前强门禁阶段机、命令/skill 承载方式、安装边界和关键分支。

## What I Already Know

- 用户明确要求更新 `工作流思维导图.html`。
- 用户明确说明可以信任 `/tmp/trellis-0.5.17-2` 中实际嵌入的工作流分析结果。
- 目标 HTML 是自包含文件，按 `.trellis/spec/docs/workflow-mindmap-spec.md` 使用 inline `const tree = [...]` 和 vanilla JS/SVG 布局。
- 临时项目 `workflow-installed.json` 显示：`trellis_version = 0.5.17`、`workflow_version = 0.1.2803`、profile 为 `outsourcing`。
- 临时项目实际命令面包含 `feasibility`、`brainstorm`、`design`、`plan`、`project-audit`、`check`、`review-gate`、`delivery`，并 patch baseline `continue` / `finish-work`，禁用 `parallel`。
- 临时项目 `.trellis/workflow.md` 的强门禁主链为 `feasibility → brainstorm → design → plan → implementation → project-audit → check → review-gate → delivery`，native `finish-work` 在 `delivery` 之后，不作为 `workflow-state` stage。
- 当前嵌入 workflow 明确 main-session-only，禁止 dispatch `trellis-research` / `trellis-implement` / `trellis-check` 或其他 subagent。

## Assumptions

- 本次只更新 `工作流思维导图.html` 的内容与必要标题，不重写布局引擎。
- 不需要重新生成 `思维导图.png`，因为用户只指定 HTML。
- 以临时项目实际嵌入产物为高优先级证据；源目录文档用于补充命名、版本和说明口径。

## Requirements

- 保持 HTML 自包含，无外部依赖。
- 保持现有右扩展主链与左侧分支导图结构。
- 更新主链节点以覆盖实际强门禁阶段机与 public entry：安装/路由、feasibility、brainstorm、design、plan、implementation/continue、project-audit、check/review-gate、delivery/native finish-work。
- 明确 Codex 不提供项目级 `/trellis:xxx` 命令目录，而通过自然语言或 skill 路由；Claude/OpenCode 使用项目命令入口。
- 明确 `workflow-state.json.stage` / `workflow-state.py route|set|validate|repair` 是阶段路由核心，`task.json.status` 不再是阶段真相。
- 明确 `parallel` 禁用与 main-session-only 约束。
- 反映外包 profile 的关键控制：启动款、双轨交付、源码水印/归属证明。
- 修复当前 HTML 中重复/不准确节点的明显问题，例如旧路径口径、过时 agent 路由和重复 ID。

## Acceptance Criteria

- [ ] `工作流思维导图.html` 的 title/root 与当前 workflow 版本一致。
- [ ] `const tree` 中无重复 `id`。
- [ ] HTML 能被脚本静态解析出 `const tree`，并校验节点 ID 唯一。
- [ ] 不引入外部 `<script src>` / CDN 依赖。
- [ ] 至少运行一次相关静态检查或项目验证命令，并记录真实结果。

## Out of Scope

- 不修改 workflow 源命令、安装器、skills 或临时项目。
- 不重新设计思维导图布局算法。
- 不生成或更新 PNG 版本，除非后续用户另行要求。

## Technical Notes

- 规范：`.trellis/spec/docs/index.md`、`.trellis/spec/docs/workflow-mindmap-spec.md`、`.trellis/spec/guides/cross-layer-thinking-guide.md`。
- 证据：`/tmp/trellis-0.5.17-2/.trellis/workflow.md`、`/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`、`/tmp/trellis-0.5.17-2/AGENTS.md`、`/tmp/trellis-0.5.17-2/.claude/commands/trellis/*.md`、`/tmp/trellis-0.5.17-2/.agents/skills/*/SKILL.md`、`/tmp/trellis-0.5.17-2/.codex/config.toml`。
- Tool evidence gap：本会话未暴露 `ace.search_context` / `context7` MCP，已降级为本地文件检索与读取。

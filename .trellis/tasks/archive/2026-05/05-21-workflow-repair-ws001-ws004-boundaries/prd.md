# PRD

## Goal

基于 `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` 复核本轮
`workflow-scan` 对 `WS-001` 到 `WS-004` 的判断，确认哪些属于真实缺陷，
哪些属于承载边界、已知限制或误报，并在 `docs/workflows/新项目开发工作流/`
内补齐文档说明，避免后续再次把同类现象误判成 workflow 问题。

## What I Already Know

- 用户已明确指出：
  - `WS-001`/`WS-002` 不是“真实缺失”，需要说明 Claude/OpenCode 的命令入口、
    `.agents/skills/` 的共享承载边界，以及 Codex 可直接使用 `.agents/skills/`
  - `WS-003`/`WS-004` 需要说明 Codex 当前默认 `inline`，sub-agents 默认不作为
    正常执行路径；`start` 主要由 hook 机制触发，而不是必须依赖某个特定的
    `SessionStart` 接线
- `docs/workflows/新项目开发工作流/commands/codex/README.md` 和
  `CLI原生适配边界矩阵.md` 已经包含部分相关边界说明，但需要核对是否足以
  让扫描器/维护者不再把这些现象识别成问题
- 本次 repair 的允许修改范围仅限：
  `docs/workflows/新项目开发工作流/`、当前 repair task 目录、
  `tmp/workflow-issues/`

## Required Outcomes

1. 逐条复核 `WS-001` 到 `WS-004` 的 temp project 证据与 source workflow 说明，
   给出 `adopted` / `ignored` / `manual-decision` / `trellis-native` 等结论。
2. 若问题实为文档边界不清，则在 workflow 源文档中补齐说明，明确：
   - Claude/OpenCode 的 `continue` / `finish-work` 命令承载面
   - `.agents/skills/` 作为共享 skills 主承载面时的适用范围
   - `.codex/skills/` 作为 secondary carrier 的边界
   - Codex `start` 的 hook 触发与 `SessionStart` 非强依赖边界
   - Codex `dispatch_mode = inline` 下默认不使用 sub-agents 的已知限制
3. 对其它 findings 按实际情况判断是否仍成立，但本轮执行重点放在上述承载边界
   相关问题，不无谓扩修无关条目。
4. 产出 correction plan、repair log、issue history，并按 `--auto` 规则判断
   是否可继续进入当前 repair task 的正常 close-out 流程。

## Non-Goals

1. 不修改 `docs/workflows/新项目开发工作流/` 之外的源码或平台目录。
2. 不把 Codex 平台自身的默认限制伪装成 workflow-source 缺陷后再“修复”。
3. 不为了满足扫描器而引入与当前真实安装边界相矛盾的冗余承载面。

## Acceptance Criteria

1. 相关 workflow 源文档能清楚解释 `WS-001` 到 `WS-004` 涉及的真实边界。
2. 变更后的说明与现有 `codex/README.md`、`CLI原生适配边界矩阵.md`、
   Claude/OpenCode 命令承载事实、以及 temp project 实际落盘情况保持一致。
3. 严格 source-side review 后，没有留下明显的跨文档矛盾或重复误导表述。
4. 相关验证命令通过，或不能运行时明确记录为 `not run` 并说明原因。

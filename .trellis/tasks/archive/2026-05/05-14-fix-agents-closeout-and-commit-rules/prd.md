# 修正 AGENTS close-out 与 commit 规则

## Goal

将项目根 `AGENTS.md` 与当前 Trellis 工作流对齐：删除与当前提交流程冲突的 `git commit` 禁令，补足与工作流直接相关但确实遗漏的本地摘要规则，并把 close-out 规则改写为主路径/底层脚本层级清晰的表述；同时修正仓库内相同层级混淆的近邻文案。

## What I already know

- 当前 `AGENTS.md` 非托管区段包含 `Do not execute git commit.`，与 `.trellis/workflow.md` Phase 3.4 的 AI 驱动 commit 流程冲突。
- 当前 `AGENTS.md` 把 `finish-work / add_session.py` 并列描述为 close-out 行为，容易混淆正常入口与底层脚本/手动 fallback。
- 当前 `AGENTS.md` 只笼统描述 sub-agent context push/pull，未点出 workflow 对人工调度时 `Active task: <task path>` 前导行的硬要求。
- 当前 `AGENTS.md` 也没有提醒：当本仓库 Trellis 工作流/平台集成行为变化时，需要同步复查非托管 AGENTS 摘要文案是否漂移。
- `.agents/skills/record-session/SKILL.md` 仍有与 close-out 层级关系类似的旧并列表述。
- 当前仓库是 workflow authoring source project，不是目标项目安装态；文案需要保持 source/deploy boundary 清晰。
- 本仓库 Codex 默认 inline，但这次修正不需要改动 dispatch_mode 规则。

## Assumptions (temporary)

- 本次主要改项目根 `AGENTS.md` 的非托管区段，必要时顺手修正仓库内与同一层级问题直接相关的近邻文案。
- 不改 Trellis 托管区段、workflow.md、hooks。
- `finish-work` 作为 close-out 主路径的既有 Trellis 规则保持不变。

## Open Questions

- 无阻塞问题；需求已在当前对话中明确。

## Requirements (evolving)

- 删除 `AGENTS.md` 中与当前工作流冲突的 `git commit` 禁令。
- 将 close-out 规则改写为：正常路径使用 Trellis native `finish-work`，并明确它运行在工作流要求的代码提交步骤之后；`add_session.py` 属于该流程使用的底层 journal 记录脚本/手动 fallback 组成部分，而非并列主入口。
- 在 `AGENTS.md` 中补一条人工调度 Trellis sub-agent 时必须遵循 `.trellis/workflow.md` 的 `Active task: <task path>` 前导行约束。
- 在 `AGENTS.md` 中补一条工作流演进后的非托管 AGENTS 同步检查提醒，降低长期漂移风险。
- 修正 `.agents/skills/record-session/SKILL.md` 中与 close-out 层级关系相同的旧并列表述。
- 保持其他项目级长期规则不被无关改动带偏。

## Acceptance Criteria (evolving)

- [ ] `AGENTS.md` 不再保留 `Do not execute git commit.` 规则。
- [ ] `AGENTS.md` 的 close-out 描述不再把 `finish-work` 与 `add_session.py` 并列成同级入口，且不再遗漏提交前置要求。
- [ ] `AGENTS.md` 明确人工调度 sub-agent 时的 `Active task: <task path>` 前导行约束。
- [ ] `AGENTS.md` 补上 workflow 演进后的非托管摘要同步提醒。
- [ ] `.agents/skills/record-session/SKILL.md` 的相关 close-out 文案与新的层级关系保持一致。
- [ ] 修改后文案仍符合当前仓库 source-project 边界表述。

## Definition of Done (team quality bar)

- 修改范围最小且聚焦
- 关键文案已人工复核
- 相关规则与当前工作流无直接冲突

## Out of Scope (explicit)

- 不修 `no_task` / `finish-work` 命名等 Trellis baseline 自带歧义
- 不改 `.trellis/workflow.md`、hooks
- 不处理其他未请求的 AGENTS 文案优化

## Technical Notes

- 目标文件：`AGENTS.md`、`.agents/skills/record-session/SKILL.md`
- 参考规则：`.trellis/workflow.md` Phase 3.4、`.agents/skills/trellis-finish-work/SKILL.md`、`.agents/skills/record-session/SKILL.md`

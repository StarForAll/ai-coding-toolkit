# human-terminal-only-embed-execution

## Goal

将 `docs/workflows/新项目开发工作流/` 的首次嵌入合同从“限制某些 CLI 主导 formal embed”收紧并精确化为“禁止 AI agent / AI CLI 自主发起嵌入执行，首次嵌入仅支持人类操作者在系统终端中显式运行并确认命令链”，并同步脚本门禁、产品文档、维护者审计合同与场景测试。

## What I already know

- 当前首次正式安装的门禁变量为 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED`
- 当前 `install-workflow.py` 的正式安装阻断口径是“不能在 Codex 中嵌入成功，只能在 Claude Code / OpenCode（或直接 shell）中执行”
- 当前 `工作流嵌入执行规范.md`、`工作流总纲.md`、`命令映射.md`、多 CLI walkthrough、Claude/OpenCode/Codex README 都暴露了旧合同文案
- 当前 `workflow-audit` 的核心 runtime 边界是“Codex 到 formal embed 时停止并 handoff 给 Claude Code / OpenCode 主会话”
- `workflow-audit` 的行为语义有三份源面必须同步：
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
  - `.claude/skills/workflow-audit/SKILL.md`
- 对应 reference templates 与 scenario tests 也需要一起更新
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` 已对 embed confirm env 有测试覆盖

## Assumptions (temporary)

- 当前仓库的 workflow 目标仍然是多 CLI 装后共存，但“首次嵌入动作”需要升级为 human-terminal-only 合同
- 这次改动不改变装后运行形态，只改变首次嵌入执行主体与审计验证边界
- `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` 可以安全更名为 `WORKFLOW_EMBED_HUMAN_CONFIRMED`，同时需要同步 capability-audit / installer tests / docs
- 仅靠脚本无法 100% 证明“真的是人类在键盘输入”，所以实现应采用“显式环境确认 + TTY 检测 + 人类确认串”作为最佳努力门禁

## Open Questions

- 是否需要保留对旧环境变量 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` 的临时兼容读取
- `workflow-capability-audit.py` 中用于 temp project formal install 的测试/验证路径，是否也需要同步切到“人类 transcript required”语义，还是仅做静态能力分析
- `workflow-audit` 的 reference 名称 `codex-handoff-template.md` 是否继续沿用文件名，还是改成更中性的 “human-terminal-required-template”

## Requirements (evolving)

- 正式安装必须只接受人类操作者在系统终端中的显式执行与确认
- 任何 AI agent、AI CLI 主会话、skills、slash commands、subagents、自动编排链路都不得作为首次嵌入执行主体
- `install-workflow.py` 在非 `--dry-run` 时必须执行明确的人类终端门禁
- workflow 产品文档必须统一改写为 `human-terminal-only` 口径，不能再写 “Claude Code / OpenCode 可以执行 formal embed”
- `workflow-audit` 必须取消“handoff 到另一个 AI CLI 执行 formal embed”的路径，改成“停止并要求人类返回终端 transcript”
- `workflow-audit` 的 spec、skill surfaces、references、tests 必须同改
- 需要保留多 CLI 适配范围结论，但要明确这只适用于“装后使用”，不适用于“首次嵌入执行主体”

## Acceptance Criteria (evolving)

- [ ] `install-workflow.py` 对 formal install 实现 human-terminal-only 门禁
- [ ] 安装器测试覆盖新环境变量与门禁行为
- [ ] 首次嵌入相关产品文档全部改为统一新口径
- [ ] `workflow-audit` 三份行为源面与 references/tests 已同步
- [ ] 不再存在“Claude Code / OpenCode 主会话可继续 formal embed”的正式合同表述

## Definition of Done (team quality bar)

- 脚本、文档、spec、skill、tests 同步完成，无明显合同漂移
- 至少运行相关单元测试/验证命令，真实报告 pass / fail
- 若某些 runtime 审计脚本因新合同需要后续人工验证，必须在结果中明确说明

## Out of Scope (explicit)

- 改变装后 Claude/OpenCode/Codex 的日常 workflow 使用模型
- 扩展到 `.kiro/`、`.qoder/` 等当前不在该 workflow managed surface 内的平台
- 设计真正不可绕过的人类证明机制
- 对整个 workflow 做新一轮 capability audit

## Technical Notes

- 关键实现文件：
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
- 关键产品文档：
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
- 关键维护者合同面：
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
  - `.claude/skills/workflow-audit/SKILL.md`
  - `.agents/skills/workflow-audit/references/*`
  - `.claude/skills/workflow-audit/references/*`
  - `.agents/skills/workflow-audit/tests/*`
  - `.claude/skills/workflow-audit/tests/*`

# workflow-audit: 新项目开发工作流

## Goal

基于当前 Trellis `0.5.4` 原生能力，对 `docs/workflows/新项目开发工作流/` 做同版本维护审计，判断其中哪些设计已经被 Trellis 原生能力覆盖、哪些只是 workflow 的必要增强、哪些形成了重复入口或过度复杂化，并通过 `/tmp` 目标项目运行时验证而不是只做静态阅读。

## What I already know

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中的 `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.4`
- 当前环境 `trellis -v` 返回 `0.5.4`，版本闸门通过
- 当前审计目标固定为 `docs/workflows/新项目开发工作流/`
- 当前主执行器是 Codex，本会话不能使用 subagents
- `trellis-research` / `trellis-implement` / `trellis-check` 已由 Trellis 原生提供；workflow 不再 overlay agents，只做 legacy bare-name → trellis-* 迁移
- OpenCode 的正式主入口是 `.opencode/commands/trellis/`，但 `.agents/skills/*/SKILL.md` 也会被 OpenCode 扫描到，存在多入口暴露风险
- Codex 的共享 skills 主承载面是 `.agents/skills/`；`.codex/skills/` 是可能存在的次级影响面
- formal embed 受 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` 门禁保护；按 workflow-audit 合同，Codex 到达 formal install 时必须停止并 handoff

## Assumptions (temporary)

- 当前会话可以完成 `/tmp` 目标项目创建、`trellis init`、`detect-embed-state.py` 和 `install-workflow.py --dry-run`
- 当前会话无法把 formal embed 作为“已验证完成”处理，因为主执行器是 Codex
- `todo.txt`、执行卡、`pack.requirements-discovery-foundation` 导入、`AGENTS.md` routing block 都属于 workflow 附加能力，需要分别判断“必要增强”还是“过度合同化”

## Open Questions

- `/tmp` 基线下是否会同时出现 `.agents/skills/` 与 `.codex/skills/`
- OpenCode 对 `.agents/skills/` 的扫描在真实目标项目里是否造成重复入口副作用
- `todo.txt` 是否只是低价值协作提醒，却被提升成正式安装合同产物
- `parallel` 移除、dual-skills 清理、legacy `record-session` 兼容链，是否仍被当前 `trellis init` 现实产物所迫
- 当前会话结束前是否具备可用的非 Codex handoff 执行器

## Requirements (evolving)

- 对照 Trellis 原生能力与 workflow managed subset，区分“原生继承”“必要增强”“重复暴露”“非必要合同资产”
- 审计必须覆盖 Claude Code / OpenCode / Codex 三个平台的 carrier boundary
- 审计必须覆盖脚本行为契约：`detect-embed-state.py`、`install-workflow.py`、`upgrade-compat.py`
- 审计必须进入 `/tmp` 运行时验证，不能只做静态分析
- formal install 到达 Codex handoff 边界时必须停止，不能伪造已验证状态
- 当前回合不做 workflow 源文件修改，只输出证据化判断与后续修复方向

## Acceptance Criteria (evolving)

- [ ] 版本闸门、目标绑定、A/B/C 静态证据已记录
- [ ] `/tmp` 目标项目运行时验证至少覆盖 `trellis init`、`detect-embed-state.py`、`install-workflow.py --dry-run`
- [ ] 所有结论区分 confirmed issue / false alarm / blocked / evidence gap
- [ ] 每条关键证据都带 source-layer 标签
- [ ] 对“多余 / 错误 / 重复 / 不需要”的结论给出明确边界，而不是笼统评价

## Definition of Done (team quality bar)

- 审计结论基于真实证据，不以猜测替代
- 运行过能证明当前结论的命令，并记录 pass / fail / blocked
- 若存在未验证边界，明确写出原因和下一步
- 若发现 durable contract drift，指出后续应更新的 spec / docs / tests 范围

## Out of Scope (explicit)

- Trellis 跨版本兼容性分析（这属于 `workflow-capability-audit`）
- 当前回合直接修复 workflow 源文件
- `.kiro/`、`.qoder/` 等不在当前 workflow managed surface 内的平台
- 与 workflow 无关的业务代码或普通实现质量审查

## Technical Notes

- 核心契约文件：
  - `.trellis/spec/skills/workflow-audit.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- 关键脚本：
  - `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- 关键候选项：
  - OpenCode `.opencode/commands` 与 `.agents/skills` 双入口重复暴露
  - `todo.txt` 被提升为安装合同产物
  - Codex dual-skills 目录与 duplicate shared skill 清理复杂度
  - `parallel` 备份后移除的必要性
  - legacy `record-session` 兼容链在 fresh baseline 下的残余负担

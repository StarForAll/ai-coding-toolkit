# workflow-audit: 新项目开发工作流嵌入补丁与验活缺口修复

## Goal

以 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的目标项目为验收对象，验证用户列出的嵌入补丁、运行时回退路径、安装完成判定与验证覆盖问题是否真实存在；若确认为工作流源缺陷，则仅在 `docs/workflows/新项目开发工作流/` 内修复，并补齐同类缺口，确保后续安装器嵌入时不再复发同类问题。

## What I Already Know

- 审计目标固定为 `docs/workflows/新项目开发工作流/`，不是当前仓库自身运行中的 `.trellis/` 工作流。
- 修复范围只允许落在 `docs/workflows/新项目开发工作流/`；其他目录不能修改。
- 用户已提供 6 类候选问题，重点指向 `task.py` strong-gate 补丁、OpenCode `inject-workflow-state` 补丁、安装后健康校验盲区、Codex 残留旧逻辑，以及自动化验证不足。
- 当前仓库的 `workflow-audit` 技能要求先做版本门禁、再做 A/B/C 证据主线；本次因用户明确要求 `/tmp` 运行验证，属于 task-based runtime 审计场景。
- `COMPATIBLE_TRELLIS_VERSION` 为 `0.5.17`，当前 `trellis -v` 输出也为 `0.5.17`，版本门禁通过。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 保留了足够的安装后状态，可用于复现已嵌入目标项目中的真实问题。
- 相关缺陷如果源自工作流补丁器或安装校验链，应能在 `docs/workflows/新项目开发工作流/commands/` 和其测试/文档层中找到同构缺口。
- 如果需要修复 Trellis 原生脚本问题，应通过该工作流的补丁器或安装阶段生成物修复，而不是改当前仓库或上游 Trellis 源。

## Open Questions

- `/tmp/trellis-0.5.17-2` 中哪些问题是当前工作流源码必然导致，哪些只是一次安装中断或历史残留？
- 现有回归测试/安装器测试是否已经覆盖这些场景，还是需要在工作流目录内新增针对性测试？

## Requirements (evolving)

- 必须先验证用户列出的候选问题是否真实存在，不能把假设直接当结论。
- 必须在分析时搜索类似问题并一并修复，不能只修单个报错点。
- 仅允许修改 `docs/workflows/新项目开发工作流/` 及当前任务目录。
- 若补丁有新增依赖、调用签名变更或安装完整性判定新增约束，必须保证补丁器、安装器、校验器、测试/文档同步更新。
- 修复后需用可执行验证证明：至少包括目标脚本的运行/编译验证、相关单元测试或回归测试，以及必要的安装后检查逻辑验证。

## Acceptance Criteria (evolving)

- [ ] 在 `/tmp/trellis-0.5.17-2` 完成对候选问题的复现或排除，并把证据记录到 `audit-report.md`。
- [ ] 对所有确认存在的问题，在 `docs/workflows/新项目开发工作流/` 内完成源修复，覆盖相关同类缺陷。
- [ ] 更新后的补丁器/安装器/校验器不会再把缺失关键依赖或调用链不完整的产物误判为“已安装完成”。
- [ ] 运行与本次变更相关的验证命令，并据实记录 pass/fail/not run。

## Definition of Done (team quality bar)

- 仅修改允许范围内文件
- 相关验证命令已执行并记录真实结果
- 变更未引入新的已知运行时断裂
- 必要的文档或测试同步更新

## Out of Scope (explicit)

- 修改当前仓库实际运行的 `.trellis/`、`.codex/`、`.opencode/` 等非工作流源目录
- 修复与 `docs/workflows/新项目开发工作流/` 无关的仓库其他功能
- 在本轮直接修改上游 Trellis 发布物，而不通过工作流补丁/安装链落地

## Technical Notes

- 审计工作流技能：`.agents/skills/workflow-audit/SKILL.md`
- 相关规范：`.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`、`.trellis/spec/scripts/python-conventions.md`、`.trellis/spec/docs/index.md`
- 当前执行模式：Codex inline；根据仓库规则不能使用子 agent。

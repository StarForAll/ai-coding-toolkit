# 修复新项目开发工作流残留门禁与收尾路由问题

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行 `trellis init` 并嵌入当前工作流的目标项目，确认 `docs/workflows/新项目开发工作流/` 是否仍存在残留旧语义、错误收尾路由、repair 恢复分支不一致、finish-work 边界泄漏、以及跨 CLI 同步未彻底收口等真实问题；若问题成立，只在 `docs/workflows/新项目开发工作流/` 内修复，并补齐同类缺口，确保后续嵌入目标项目时默认行为正确且不引入新的状态机问题。

## What I already know

- 用户明确要求分析判断对象是 `/tmp/trellis-0.5.17-2` 的已嵌入结果，而不是当前仓库自身运行态。
- 用户明确要求实际修复只能发生在 `docs/workflows/新项目开发工作流/`；任务目录可正常写入。
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 当前 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`。
- 本机 `trellis -v` 输出 `0.5.17`，版本门通过，不属于版本漂移审计。
- `ace.search_context` 已定位到与 SessionStart 强门禁补丁、finish-work / record-session 边界、repair 分支说明、以及 Claude/OpenCode/Codex 安装补丁相关的关键源文件。
- 用户给出的 5 个候选问题都必须视为假设，不能直接当成已确认缺陷；需要回到源工作流和 `/tmp` 已嵌入状态上逐项验证。
- 当前仓库 Codex 处于 inline dispatch 模式，不能使用 agents；本任务需要在主会话内完成审计、修复和验证。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 的嵌入状态足够代表当前工作流一次真实安装后的目标项目形态。
- 如果同类问题出现在多个工作流源文件、安装补丁、测试或说明文档中，应在本次修复中同步收口，而不是只修最显眼的一处。
- 若需要修改 Trellis 原生行为，应通过当前工作流的安装器/补丁脚本在目标项目落补丁，而不是修改当前仓库的 Trellis 基线文件。

## Open Questions

- `/tmp/trellis-0.5.17-2` 中暴露的 READY 自动续跑语义，源头究竟来自安装补丁未覆盖、源文档仍保留旧语义，还是测试/回归面缺失导致的再引入。
- finish-work 与 record-session 的最终职责边界，是否在命令文档、技能摘要、NL 路由、安装补丁和测试中已经出现不一致。
- `workflow-state.py repair` 缺失状态文件时是否仍存在将任务粗暴重置到 `feasibility` 的错误提示或同类路径。

## Requirements (evolving)

- 审计必须区分四层证据：`source repo`、`generated target project` baseline、`generated target project` workflow-installed state、`runtime command output`。
- 必须先确认问题真实存在，再修复。
- 修复范围只能落在 `docs/workflows/新项目开发工作流/`。
- 修复时要主动扫描并一并处理同类问题，避免只修单点。
- 不能引入新的状态机冲突、收尾退化或跨 CLI 漂移。
- 需要补充足够的验证手段，至少覆盖相关脚本/补丁/测试/文档契约。

## Acceptance Criteria (evolving)

- [ ] 已用源工作流和 `/tmp/trellis-0.5.17-2` 的证据确认每个候选问题是真问题、假警报或未证实。
- [ ] 真实问题的修复全部限制在 `docs/workflows/新项目开发工作流/`。
- [ ] READY 自动续跑旧语义、错误收尾路由、repair 错误提示、finish-work 边界残留、以及发现的同类问题都已在源工作流内收口。
- [ ] 相关测试或可执行验证已覆盖修复点，结果被真实记录为 pass / fail / not run。
- [ ] 未修改 `docs/workflows/新项目开发工作流/` 以外的产品源资产。

## Definition of Done (team quality bar)

- 相关测试已补充或更新，并实际运行
- lint / typecheck / CI 范围内可运行项已执行或明确说明不能执行的原因
- 文档、补丁脚本、测试、安装契约保持一致
- 回归风险和未覆盖边界已明确记录

## Out of Scope (explicit)

- 修改当前仓库自身正在使用的 `.trellis/`、`.codex/`、`.claude/`、`.opencode/` 运行态资产
- 修改 `docs/workflows/新项目开发工作流/` 之外的工作流目录
- 做版本兼容性升级审计（这不是 `workflow-capability-audit` 任务）
- 删除当前任务目录

## Technical Notes

- Workflow root: `docs/workflows/新项目开发工作流/`
- Evidence target project: `/tmp/trellis-0.5.17-2`
- Current CLI: `codex`
- Audit mode: task-based runtime
- Initial key source files:
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`


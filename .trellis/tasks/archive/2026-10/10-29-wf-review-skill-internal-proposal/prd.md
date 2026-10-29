# wf 审查 skill 内部化与新方案提案

## Goal

把 `multi-cli-review` / `multi-cli-review-action` 从仓库全局通用 skill 改为 wf 工作流**内部 skill**，并把它定为具体任务 check 阶段多 agent 辅助审查的**基础默认实现**（后续允许新增其他实现）。本轮只产出新方案供人审查，通过后才写入 `docs/workflows/workflow-implementation.md`。

## Requirements

1. 新方案必须给出内部化的完整形态：skill 命名（**`wf-task-review` / `wf-task-review-action`**）与落点、模块源位置、平台投放矩阵、frontmatter 渲染、安装/卸载归属、与 `wf` / `wf-repair` 的职责边界。
2. 新方案必须给出审查编排契约：**只在具体任务 check 阶段**使用、**人工主动调用不自动化**、reviewer 只接收**任务标识**并从任务里自取信息、轮次自解、报告产物落点与命名、失败语义、降级规则。
3. 新方案必须写明权威关系：报告只是辅助证据，主 agent 须逐条复核，可改法可驳回并记录偏离，报告不构成指令。
4. 新方案必须说明与既有约束的关系：不变量 3（不新增记录类型）、5（图内任务只走机制入口）、6（完成 = 人判 + 归档）、9（不依赖单一 CLI），以及 plan 文档 §9.6 G7 已登记的五条边界是否需放宽、放宽到哪。
5. 新方案必须逐条给出相对现有通用协议的**适配改动**，每条带验收方式。
6. 新方案必须说明全局版 skill 的处置（保留 / 改造 / 退役）及 `.trellis/spec/skills/index.md` 中 paired-contract 段落的同步改述。
7. 新方案只作过程约定：不得让审查进入状态机（不改 `task.json.status`、不写账本、不构成 `wf close` 的完成判据）。
8. 通过后写入实现方案文档时，落点为 §8.3 + 新 §8.5、§9.6 G7 状态更新、附录 B 路径、探针表新增 R 系列。

## Non-goals

- 本轮不改 `docs/workflows/workflow-implementation.md` 正文（等提案通过）。
- 本轮不实现内部 skill 本体、不改安装器。
- 不引入 `trellis channel` 作为并列编排候选（已由本轮判据排除，详见提案 §7）。

## Acceptance Criteria

- [x] `proposal.md` 覆盖 Requirements 1–8；人审后所有裁决项均已定值并写回提案。
- [x] 提案中每条适配项都能对应一个可执行验收（A1–A23，探针 R1–R11）。
- [x] 提案通过后已按约定落点写入（§8.3 改述、新 §8.5、附录 C、探针 R 系列、§9-C17、§9.5 留痕、§9.6 G7 定稿），且与既有编号无冲突。

## 结果

- 落地提交：`ae0eeef`。
- 同批修掉缺口清单里的 A4–A10、B1–B3、C1–C10、D1–D2、E1–E5。
- 留待本任务完结后另开任务：A1（基线流程与 `wf baseline --light` 矛盾）、A2（`wf check`/`route` 标只读却写账本）、A3（§9.7 在 normative 清单外）、A11（裸 `§x` 撞号）。
- 待实施阶段（P1）才做实体资产：`review-protocol.md`、两个内部 skill、全局版移除。

## Notes

- 决策来自 2026-10-29 会话：审查实现只考虑 `multi-cli-review-action` / `multi-cli-review`，且二者要改造为工作流内部 skill。
- 现状证据：两个 skill 位于 `skills/`，未被 `trellis-library/manifest.yaml` 登记，也未部署到 `.agents/skills/`、`.claude/skills/`。

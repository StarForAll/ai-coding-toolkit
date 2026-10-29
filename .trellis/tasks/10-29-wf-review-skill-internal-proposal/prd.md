# wf 审查 skill 内部化与新方案提案

## Goal

把 `multi-cli-review` / `multi-cli-review-action` 从仓库全局通用 skill 改为 wf 工作流**内部 skill**，并把它定为具体任务 check 阶段多 agent 辅助审查的**基础默认实现**（后续允许新增其他实现）。本轮只产出新方案供人审查，通过后才写入 `docs/workflows/workflow-implementation.md`。

## Requirements

1. 新方案必须给出内部化的完整形态：skill 命名与落点、模块源位置、平台投放矩阵、frontmatter 渲染、安装/卸载归属、与 `wf` / `wf-repair` 两个 skill 的职责边界。
2. 新方案必须给出审查编排契约：触发点、派发者、审查者身份规格、轮次与人数默认、报告产物落点与命名、失败语义、降级规则。
3. 新方案必须说明与既有约束的关系：不变量 3（不新增记录类型）、5（图内任务只走机制入口）、6（完成 = 人判 + 归档）、9（不依赖单一 CLI），以及 plan 文档 §9.6 G7 已登记的五条边界是否需放宽、放宽到哪。
4. 新方案必须逐条给出相对现有通用协议的**适配改动**，每条带验收方式。
5. 新方案必须说明全局版 skill 的处置（保留 / 改造 / 退役）及 `.trellis/spec/skills/index.md` 中 paired-contract 段落的同步改述。
6. 新方案只作过程约定：不得让审查进入状态机（不改 `task.json.status`、不写账本、不构成 `wf close` 的完成判据）。
7. 通过后写入实现方案文档时，落点为 §8.3 + 新 §8.5、§9.6 G7 状态更新、附录 B 路径、探针表新增 R 系列。

## Non-goals

- 本轮不改 `docs/workflows/workflow-implementation.md` 正文（等提案通过）。
- 本轮不实现内部 skill 本体、不改安装器。
- 不引入 `trellis channel` 作为并列编排候选（已由本轮判据排除，详见提案 §7）。

## Acceptance Criteria

- [ ] `proposal.md` 覆盖 Requirements 1–7，且每个待裁决项都显式标为待决而不是默认取值。
- [ ] 提案中每条适配项都能对应一个可执行验收（命令或夹具场景）。
- [ ] 提案与人审通过后，文档写入点与现有章节编号不冲突。

## Notes

- 决策来自 2026-10-29 会话：审查实现只考虑 `multi-cli-review-action` / `multi-cli-review`，且二者要改造为工作流内部 skill。
- 现状证据：两个 skill 位于 `skills/`，未被 `trellis-library/manifest.yaml` 登记，也未部署到 `.agents/skills/`、`.claude/skills/`。

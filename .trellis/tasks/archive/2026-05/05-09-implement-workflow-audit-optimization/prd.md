# implement-workflow-audit-optimization

## Goal

根据 `05-09-backfill-workflow-audit-optimization-task-info` 的任务结论，实际收敛并优化
`workflow-audit` 的 same-version maintainer contract，使其更准确反映当前仓库
Trellis 0.5.9 的运行机制与证据模型，同时保持既有职责边界不扩张到
`workflow-capability-audit` 或 workflow product surface 变更。

## What I already know

* `workflow-audit` 当前的 version gate、固定 workflow root、Claude/OpenCode/Codex
  支持面、Codex handoff 边界已经基本正确，不需要重做。
* 现有缺口主要在机制表达精度：
  * Step 2a 对当前 Trellis 运行机制描述过粗
  * 三层证据模型没有被足够显式地表达
  * `.agents/skills/` 的双重角色需要澄清
  * Codex `.codex/skills/` 需要继续被描述为条件性次级 surface
  * task-based wording 需要更明确地绑定 session-scoped task runtime
* 变更面至少包括：
  * `.trellis/spec/skills/workflow-audit.md`
  * `.agents/skills/workflow-audit/SKILL.md`
  * `.claude/skills/workflow-audit/SKILL.md`
  * 受影响的 references/tests

## Assumptions

* 本次实现优先做 contract alignment，不默认改 `workflow_assets.py`。
* 只有在 evidence 显示 maintainer-facing references/tests 已经无法表达新合同时，
  才同步修改它们。
* workflow product docs 只有在本轮合同修正后仍存在明确 wording drift 时才进入本次改动。

## Open Questions

* 哪些 references/tests 需要最小同步，才能覆盖机制精度提升而不引入范围蔓延？

## Requirements

* 扩展 `workflow-audit` 的 Step 2a 机制地图，明确：
  * `.trellis/` 是 runtime truth layer
  * hidden platform directories 是 carrier layers
  * `.agents/skills/` 的 repo-local / target-project dual role
  * Codex hook/config carrier present-but-runtime-gated
  * session-scoped task runtime 在 `.trellis/.runtime/sessions/`
* 明确三层证据模型：
  * `source repo`
  * `generated target project` baseline / installed state
  * `runtime command output`
* 保持 `.kiro/` / `.qoder/` 仍然 out of scope，除非 `workflow_assets.py`
  明确扩面。
* 保持 `.codex/skills/` 为 conditional secondary carrier，而不是默认必备产物。
* 在 spec / `.agents/` / `.claude/` 三个行为面保持一致。
* 如合同变化影响 references/tests，必须同改并保持 `.agents/` 与 `.claude/` 同步。

## Acceptance Criteria

* [ ] `.trellis/spec/skills/workflow-audit.md` 明确表达当前 Trellis 机制地图与三层证据模型
* [ ] `.agents/skills/workflow-audit/SKILL.md` 与 `.claude/skills/workflow-audit/SKILL.md`
      同步到相同行为语义
* [ ] 相关 references/tests 已补足到能体现新增合同，不存在明显语义漂移
* [ ] `./scripts/validate-skills.sh` 通过
* [ ] 关键同步差异通过 `diff` / targeted review 复核

## Definition of Done

* `workflow-audit` same-version maintainer contract 与当前仓库 Trellis 机制保持一致
* 不引入对 `workflow-capability-audit` 的职责侵入
* 不无证据扩大 workflow managed surface
* 技能验证通过，且 `.agents/` / `.claude/` 语义一致

## Out of Scope

* 修改 `workflow_assets.py` 的 managed surface 定义
* 把 `.kiro/` / `.qoder/` 纳入 workflow-audit 支持面
* 重构 `workflow-capability-audit`
* 无明确证据时批量修改 workflow product docs

## Technical Notes

* 上游分析来源：
  * `.trellis/tasks/05-09-backfill-workflow-audit-optimization-task-info/info.md`
  * `.trellis/tasks/05-09-backfill-workflow-audit-optimization-task-info/prd.md`
* 需遵守的 repo-local 约束：
  * `.trellis/spec/skills/index.md`
  * `.trellis/spec/guides/code-reuse-thinking-guide.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`

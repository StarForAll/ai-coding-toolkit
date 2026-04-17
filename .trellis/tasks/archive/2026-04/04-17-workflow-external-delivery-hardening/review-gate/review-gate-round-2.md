# Review Gate - Round 2

## Decision

- result: `required`
- round: `2`
- task-id: `04-17-workflow-external-delivery-hardening`
- protocol: `task-level`

## Why Round 2 Is Running

本轮不是重复 round 1，而是对 round 1 修复后的结果做**收敛性复核**。

继续进入 round 2 的原因：

- round 1 已修复 3 个功能性问题，需确认修复后没有新的回归或遗漏
- 本次任务仍属于跨层 workflow 门禁变更，blast radius 高
- 当前 workflow 的活动版本号、外包项目门禁、非外包路径、repo-local `.trellis/spec` 规则同步都需要再次交叉确认
- 用户明确要求继续第二轮

## Scope Of Round 2

本轮 reviewer 只复核以下点：

1. round 1 修复后，`delivery-control-validate.py` 对非外包项目是否已经完全不误伤
2. `workflow-state.py` 对外包项目的 `delivery_control_handover_trigger` / `delivery_control_retained_scope` 校验是否已与其他 validator 对齐
3. 版本规则是否已完整传播到：
   - `docs/workflows/自定义工作流制作规范.md`
   - `.trellis/spec/docs/index.md`
   - `docs/workflows/新项目开发工作流/**`
   - `commands/test_workflow_installers.py`
4. round 1 忽略项里是否有被修复后放大成“当前仍成立”的问题

## Required Context For Reviewers

执行 round 2 前，reviewer 必须同时读取：

- `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/summary-round-1.md`
- `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/action.md`

要求：

- 只报告修复后**仍然成立**的新问题或遗漏
- 不重复 round 1 已关闭项
- 不输出低价值风格建议
- reviewer 只审查，不修改代码

## Exit Rule

- 若 round 2 无新的高价值问题，则当前任务可视为多 CLI 审查已收敛
- 若仍发现功能性问题，则先修复并重新验证，再决定是否需要 round 3

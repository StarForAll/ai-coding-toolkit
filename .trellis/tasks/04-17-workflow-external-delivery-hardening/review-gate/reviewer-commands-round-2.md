# Reviewer Commands - Round 2

## Task Summary

- task-id: `04-17-workflow-external-delivery-hardening`
- target path: `.`
- review round: `2`
- task-dir: `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening`
- reviewer count: `2`
- protocol: `task-level`

## Review Focus

- round 1 修复后的非外包项目路径是否已经完全不被外包门禁误伤
- `workflow-state.py` 新增的外包项目强门禁字段校验是否与其他 validator 完全对齐
- “未正式可用 workflow 版本不得大于 1.0”的规则是否已在 repo-local spec、source workflow docs、generated docs、installer assertions 中同步到 `0.1.24`
- 只报告当前仍成立的高价值问题，不输出低价值风格建议

## Round 1 Context

执行 round 2 前，reviewer 应同时读取：

- `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/summary-round-1.md`
- `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/action.md`

要求：

- 只报告修复后**仍然成立**的高价值问题
- 不重复 round 1 已关闭项
- 不输出低价值风格建议
- reviewer 只审查，不修改代码

## Reviewer Commands

### Claude

```text
/multi-cli-review "复核当前针对‘外包项目分类与开工款门禁 + 预正式版本号收敛到 0.1.24’的 workflow 修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) `delivery-control-validate.py` 对 `non_outsourcing` 项目在 plan、delivery、--all 三种模式下是否已经完全提前返回；2) `workflow-state.py` 对 `delivery_control_handover_trigger`、`delivery_control_retained_scope` 的强门禁是否已与 feasibility-check / delivery-control-validate 保持一致；3) `docs/workflows/自定义工作流制作规范.md`、`.trellis/spec/docs/index.md`、`docs/workflows/新项目开发工作流/**`、安装器测试中的当前生效版本是否都已统一为 `0.1.24`；4) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。" . --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --reviewer-id claude --round 2 --review-focus "round-1 修复回归、非外包路径、外包项目强门禁字段对齐、预正式版本号同步；同时读取 summary-round-1.md 与 action.md 作为 round-1 决策上下文"
```

### OpenCode

```text
/multi-cli-review "复核当前针对‘外包项目分类与开工款门禁 + 预正式版本号收敛到 0.1.24’的 workflow 修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) `delivery-control-validate.py` 对 `non_outsourcing` 项目在 plan、delivery、--all 三种模式下是否已经完全提前返回；2) `workflow-state.py` 对 `delivery_control_handover_trigger`、`delivery_control_retained_scope` 的强门禁是否已与 feasibility-check / delivery-control-validate 保持一致；3) `docs/workflows/自定义工作流制作规范.md`、`.trellis/spec/docs/index.md`、`docs/workflows/新项目开发工作流/**`、安装器测试中的当前生效版本是否都已统一为 `0.1.24`；4) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。" . --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --reviewer-id opencode --round 2 --review-focus "round-1 修复回归、非外包路径、外包项目强门禁字段对齐、预正式版本号同步；同时读取 summary-round-1.md 与 action.md 作为 round-1 决策上下文"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/review-round-2/claude.md`
  - `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/review-round-2/opencode.md`
- aggregator command after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --round 2
```

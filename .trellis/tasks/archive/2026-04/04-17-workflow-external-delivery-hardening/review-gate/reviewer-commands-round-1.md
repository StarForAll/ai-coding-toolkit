# Reviewer Commands - Round 1

## Task Summary

- task-id: `04-17-workflow-external-delivery-hardening`
- target path: `.`
- review round: `1`
- task-dir: `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening`
- reviewer count: `2`
- protocol: `task-level`

## Review Focus

- 外包项目分类与开工款门禁是否在 `feasibility / workflow-state / plan / delivery` 全链路一致
- 非外包项目是否仍能正常走通用主链，不被新门禁误伤
- “未正式可用 workflow 版本不得大于 1.0” 是否已在 source docs、generated docs、installer assertions 中同步到 `0.1.24`
- 只报告当前仍成立的高价值问题，不输出低价值风格建议

## Key Files

- `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`
- `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/feasibility.md`
- `docs/workflows/新项目开发工作流/commands/plan.md`
- `docs/workflows/新项目开发工作流/commands/delivery.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/完整流程演练.md`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/自定义工作流制作规范.md`
- `.trellis/spec/docs/index.md`

## Reviewer Commands

### Claude

```text
/multi-cli-review "对当前‘新项目开发工作流’改动做第1轮补充审查。重点检查：1) `project_engagement_type`、`kickoff_payment_ratio`、`kickoff_payment_received` 与 `delivery_control_*` 是否在 feasibility、workflow-state、plan、delivery 的规则与脚本中保持一致；2) 非外包项目是否仍能正常走通用主链，未被新的外包门禁误伤；3) 当前 workflow 作为未正式可用版本，所有活动引用是否都已同步到 `0.1.24`，不存在仍使用 `1.x` 的生效版本漂移；4) 只报告当前仍成立的高价值问题，不做代码修改。" . --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --reviewer-id claude --round 1 --review-focus "外包项目强门禁一致性、非外包路径回归风险、预正式版本号同步、跨文档与脚本契约漂移"
```

### OpenCode

```text
/multi-cli-review "对当前‘新项目开发工作流’改动做第1轮补充审查。重点检查：1) `project_engagement_type`、`kickoff_payment_ratio`、`kickoff_payment_received` 与 `delivery_control_*` 是否在 feasibility、workflow-state、plan、delivery 的规则与脚本中保持一致；2) 非外包项目是否仍能正常走通用主链，未被新的外包门禁误伤；3) 当前 workflow 作为未正式可用版本，所有活动引用是否都已同步到 `0.1.24`，不存在仍使用 `1.x` 的生效版本漂移；4) 只报告当前仍成立的高价值问题，不做代码修改。" . --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --reviewer-id opencode --round 1 --review-focus "外包项目强门禁一致性、非外包路径回归风险、预正式版本号同步、跨文档与脚本契约漂移"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/review-round-1/claude.md`
  - `tmp/multi-cli-review/04-17-workflow-external-delivery-hardening/review-round-1/opencode.md`
- aggregator command after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-17-workflow-external-delivery-hardening --round 1
```

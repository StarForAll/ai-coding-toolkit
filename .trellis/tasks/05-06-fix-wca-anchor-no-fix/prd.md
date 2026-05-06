# fix(workflow-capability-audit): anchor write-back 在已兼容无修复场景下无法触发

## Problem

`workflow-capability-audit.py` 第 527-528 行：

```python
if confirmed_fix_scope and compatible_anchor_value:
    update_compatible_anchor(compatible_anchor_value)
```

`--confirm-fix-scope` 使用 `action="append"`，当用户确认审计结论为"已兼容、无需修复"时，不传任何 `--confirm-fix-scope` 项，列表为空，anchor 无法写回。

Spec 第 467-477 行明确要求：

> After a confirmed successful audit, COMPATIBLE_TRELLIS_VERSION must be set... this rule applies even if the final conclusion is the workflow is already compatible as-is or no workflow source edits were needed beyond the initialization exception.

## Impact

当 Trellis 升级后审计发现完全兼容、无需任何修复时，`COMPATIBLE_TRELLIS_VERSION` 无法推进，导致下次运行时仍会触发全量审计。

## Requirements

1. 在 `update_fix_lifecycle()` 中分离 anchor 写回条件：当 `compatible_anchor_value` 非空时即可写回，不再要求 `confirmed_fix_scope` 非空
2. 在 `main()` 的 fix-lifecycle 分支中，只要进入了 fix-lifecycle 更新路径（即用户确认了审计结论），就应解析当前版本并传入 `compatible_anchor_value`，无论 `--confirm-fix-scope` 是否有值
3. 确保已有测试（特别是 scenario 10: final-compatibility-promotion-mandatory）不受影响
4. 补充测试：验证"已兼容无修复"场景下 anchor 仍能写回

## Scope

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py` — 修改 anchor 写回条件
- `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py` — 补充测试
- 同步更新 SKILL.md 和 references 中关于 anchor 写回的描述（如有差异）

## Out of Scope

- carrier seed list 扩展（属于另一个任务）
- supplemental validation 路径的改动

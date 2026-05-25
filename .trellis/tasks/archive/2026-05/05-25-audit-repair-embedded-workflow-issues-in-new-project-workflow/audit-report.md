# Audit Report

## Audit Boundary

- Workflow root: `docs/workflows/新项目开发工作流/`
- Runtime target: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`

## Confirmed Issues

1. `project-audit -> delivery` 与任务级 `check` 的串联关系缺失；当前文档与门禁容易把任务级 `check` 和项目级 `project-audit` 混为一谈。
2. 正式 `project-audit` 不校验 `task_plan.md` 中代码相关任务是否全部完成。
3. 多个阶段命令文档只写“等待用户确认”，但没有明确要求写入 `workflow-state.json.status=awaiting_user_confirmation`。
4. `completed` 是合法 `status`，但既不能正常推进切阶段，也不会被 route 识别为等待确认态。
5. `--allowed-next` 会写入状态，但不会约束后续实际阶段切换。
6. `review-gate` 可用 `Decision=required + Mode=lite` 和仅 reviewer 指令包通过门禁，缺少 full 聚合与 reviewer 实际产物校验。
7. `brainstorm -> implementation (L0)` 允许绕过 design/plan 工程化基线，和自动化检查矩阵/finish-work 项目化来源脱节。

## Refined Interpretation

- `check` 是任务级质量关，服务于当前 active task / 当前实施轮。
- `project-audit` 是项目级总复核，服务于“全部代码相关任务完成后的全局回看”或中途预审。
- 因此真实缺陷不是“`project-audit` 替代 `check`”，而是：
  - 当前 workflow 允许 `project-audit -> delivery`，但没有把“当前任务级 `check` 是否已闭环、project-audit 本轮是否发生代码修改、delivery 需要消费哪些层级证据”定义清楚并落实到 validator。

## Runtime Evidence

- 在 `/tmp/trellis-0.5.17-2` 中最小复现：
- issue1: `project-audit` 仅有 `project-audit.md` 即可切到 `delivery`，未要求补充任务级 `check` 串联证据
  - issue2: 即使 `task_plan.md` 明示仍有未完成代码任务，也可从 `project-audit` 切到 `delivery`
  - issue4: `status=completed` 时切阶段被拒，`route` 返回 `reenter`
  - issue5: `--allowed-next plan` 仍可从 `brainstorm` 切到 `design`
  - issue6: `review-gate` 仅 `required + lite + reviewer-commands` 即可切到 `delivery`
  - issue7: `L0 brainstorm` 可直接切到 `implementation`

## Likely Fix Surface

- `commands/shell/state_utils.py`
- `commands/shell/validators_gates.py`
- `commands/shell/workflow-state.py`
- `commands/shell/test_workflow_state.py`
- `commands/workflow-patch-projectization.md`
- `commands/project-audit.md`
- `commands/check.md`
- `commands/review-gate.md`
- `commands/brainstorm.md`
- `commands/feasibility.md`
- `commands/plan.md`
- `commands/delivery.md`
- `工作流总纲.md`
- `阶段状态机与强门禁协议.md`

## Pending User Confirmation

- 是否继续按上述问题清单进入源码修复。

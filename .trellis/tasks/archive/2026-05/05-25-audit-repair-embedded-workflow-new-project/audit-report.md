# Audit Report

## Audit Boundary

- Workflow Root: `docs/workflows/新项目开发工作流/`
- Target Project: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Current CLI: `codex`
- Runtime Validation Mode: `task-based runtime`

## Candidate Issues

1. 多任务 plan -> implementation 缺少合法交接路径
2. 正式 PROJECT-AUDIT 的完成判定存在循环依赖
3. 独立 PROJECT-AUDIT task 错误要求自身具备 check.md
4. delivery 是项目级阶段，但运行时按 leaf-only 阶段处理
5. `workflow-state.py validate` 同时承担入口校验和出口门禁
6. review-gate -> delivery 没有重新确认任务级 check.md 仍有效
7. `review_gate_decision=recommended` 的跳过条件缺少结构化确认
8. PROJECT-AUDIT 声明解析过脆，可能漏校验
9. “性能回归与优化任务” 被硬编码为所有 plan 必需
10. 部分能力路由指向当前不可用或参数不匹配的工具/skill

## Findings

### Confirmed Issues

1. `delivery` 被运行时当作 leaf-only 阶段，而文档与 skill 将其定义为项目级阶段。
   - source repo: `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
   - generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/state_utils.py`
   - 证据：`COORDINATION_STAGES` 不包含 `delivery`，因此 `delivery ∈ LEAF_REQUIRED_STAGES`；同时 `delivery` skill 和阶段状态机文档都将其定义为项目级/交付级阶段。

2. `plan -> implementation` 的文档/技能/运行时约束存在真实断裂。
   - source repo: `commands/plan.md`、`阶段状态机与强门禁协议.md`、`commands/shell/validators_core.py`、`commands/shell/workflow-state.py`
   - generated target project: 对应 `.agents/skills/plan/SKILL.md`、`.trellis/workflow.md`、`.trellis/scripts/workflow/*.py`
   - 证据：quick reference 仍写 `workflow-state.py set <dir> --stage implementation`，但 plan skill、continue/start skill 与 leaf validator 又明确要求切换到真实 leaf task，父任务带 `children` 时不能作为 implementation 承载者。

3. formal `PROJECT-AUDIT` carrier 被错误要求自身具备任务级 `check.md`。
   - source repo: `commands/shell/validators_gates.py`
   - generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/validators_gates.py`
   - 证据：`_validate_project_audit_delivery_linkage()` 直接 `validate_check_gate(task_dir, ...)`；若 formal project-audit 是独立 task，则该 task 本身被要求有 `check.md`。

4. formal `PROJECT-AUDIT` 完成判定与 `archive -> completed` 形成真实循环依赖。
   - source repo: `commands/shell/validators_gates.py`
   - generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/validators_gates.py`、`/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_store.py`
   - runtime command output: `/tmp/trellis-0.5.17-2` 当前无 active tasks，说明状态流转依赖真实 task runtime，而不是摘要文档
   - 证据：`_validate_project_audit_task_plan_completion()` 要求代码相关任务 `task.json.status == completed`；`cmd_archive()` 又只有在 `workflow-state` 到 `delivery` 且 `finish-work-checklist.md` 存在并通过 `workflow-state.py validate` 后才会写入 `completed`。

5. `workflow-state.py validate` 同时承担“阶段内自检入口”和“阶段出口 gate”，被早期阶段命令直接调用时会提前阻塞。
   - source repo: `commands/brainstorm.md`、`commands/plan.md`、`commands/shell/validators_gates.py`
   - generated target project: 对应 `.agents/skills/*.md` 与 `.trellis/scripts/workflow/validators_gates.py`
   - 证据：skill 文档把 `validate <task-dir>` 放在阶段开始就执行；而 `validate_stage_exit_artifacts()` / `validate_plan_gate()` / `validate_brainstorm_exit_gate()` 等会直接检查 exit gate。

6. `review-gate -> delivery` 转场没有重新验证任务级 `check.md` 仍然有效。
   - source repo: `commands/shell/validators_gates.py`、`commands/delivery.md`
   - generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/validators_gates.py`、`/tmp/trellis-0.5.17-2/.agents/skills/delivery/SKILL.md`
   - 证据：转场逻辑在 `current_stage == "review-gate"` 时只执行 `validate_review_gate_gate()`；不再执行 `validate_check_gate(..., for_delivery=True)`，与 delivery skill 的消费契约不一致。

7. `review_gate_decision = recommended` 的跳过缺少结构化“用户接受风险”证据。
   - source repo: `commands/review-gate.md`、`commands/shell/validators_gates.py`
   - generated target project: `/tmp/trellis-0.5.17-2/.agents/skills/review-gate/SKILL.md`、`.trellis/scripts/workflow/validators_gates.py`
   - 证据：文档允许 `recommended` 在用户接受风险后跳过，但 validator 只校验 `Decision/Mode/review_gate_closure_status`，没有要求任何 acceptance 字段。

8. `PROJECT-AUDIT` 声明解析前后不一致，确实存在漏校验窗口。
   - source repo: `commands/shell/validators_gates.py`
   - generated target project: `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/validators_gates.py`
   - 证据：`_task_plan_declares_project_audit()` 用全文字符串判断，而 `_project_audit_tasks_from_plan()` 又只接受表格列精确 `type=project-audit` 的行。

9. “性能回归与优化任务” 被硬编码为所有 plan 的固定必选任务。
   - source repo: `commands/plan.md`、`commands/shell/plan-validate.py`、`工作流总纲.md`、`阶段三四：设计与任务模板.md`
   - generated target project: `/tmp/trellis-0.5.17-2/.agents/skills/plan/SKILL.md`、`.trellis/scripts/workflow/plan-validate.py`
   - 证据：`plan-validate.py` 强制 `performance_task_count == 1`，并继续要求依赖关系和任务图都必须包含该任务。

10. 能力路由存在真实失配，且不止一处。
   - source repo: `commands/design.md`、`commands/feasibility.md`、`commands/plan.md`、`工作流总纲.md`
   - generated target project: 对应 `.agents/skills/*.md`
   - 证据：
     - `exa_web_search_advanced_exa(type=deep-reasoning)` 不符合当前可用工具 schema
     - `api-design-principles`、`postgresql-table-design` 不在当前会话技能列表中

### Similar Issues Worth Fixing Together

- 与问题 10 同类：`deep-reasoning` 的 Exa type 在 `design`、`feasibility`、`plan`、`工作流总纲` 多处重复出现。
- 与问题 9 同类：性能任务“固定必选”在模板、总纲、通俗版说明、plan 文档中多点传播，需要统一改为条件触发。
- 与问题 5 同类：多个阶段文档把 `workflow-state.py validate` 描述成“阶段开始先跑一次”的通用健康检查，需要统一改为“默认校当前阶段 artifact/exit gate，不适合作为未产生产物时的空跑入口检查”。

### Not Yet Proven / Needs Care During Fix

- 问题 1 的根因不是“完全没有路径”，而是“文档 quick reference、leaf 约束、active task 切换协议没有收敛成单一合法路径”。修复时应补齐合法 handoff，而不是简单放宽 leaf 限制。

## Proposed Repair Directions

1. 重划阶段语义：
   - 将 `delivery` 纳入协调阶段，而不是 leaf-only 阶段。
   - 明确 `plan -> implementation` 的唯一合法路径：若存在 children，必须切到已确认的 leaf task，再进入 implementation。

2. 拆开 formal project-audit 与任务级 check 的职责：
   - formal project-audit carrier 不再要求自身持有 `check.md`
   - `project_audit_delivery_linkage` 改为消费“当前 active leaf task 的 check 证据 + formal carrier 的项目级证据”
   - formal project-audit 完成判定不再依赖 task 已 archive 才能写出的 `status=completed`

3. 收紧转场验证：
   - `review-gate -> delivery` 重新校验任务级 `check.md`
   - `recommended` 跳过必须有结构化 user acceptance 字段
   - `PROJECT-AUDIT` 声明解析改为单一路径、结构化解析

4. 把入口检查和出口门禁分离：
   - 保留 `validate` 的强 gate 作用
   - 为阶段开始时的“上下文/健康检查”提供更窄的检查口径，或调整文档只在合适时机调用 `validate`

5. 统一条件化约束和能力路由：
   - 把性能任务从“固定必选”改成“条件触发且可证明为何需要/不需要”
   - 批量修正技能名和 Exa 参数失配，并扩搜同类引用

## Notes

- 未经用户确认前，不修改 `docs/workflows/新项目开发工作流/` 源文件。

## Notes

- 未经用户确认前，不修改 `docs/workflows/新项目开发工作流/` 源文件。

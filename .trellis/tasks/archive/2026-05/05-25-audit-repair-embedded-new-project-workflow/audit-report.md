# Audit Report

## Audit Boundary

- Workflow Path: `docs/workflows/新项目开发工作流/`
- Generated Target Project: `/tmp/trellis-0.5.17-2`
- Mode: task-based runtime validation
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: passed

## Candidate Issues

1. `.runtime` 目录缺失但工作流文档与脚本仍引用
2. `task.py start` 行为变更未完整文档化
3. brainstorm 阶段 bootstrap 与 feasibility 职责可能重叠
4. `quality-guidelines.md` 被清空后缺少填充路径

## Findings

### Confirmed Issues

#### 1. Personal-profile bootstrap 字段契约在已嵌入 `workflow.md` 与强门禁真实校验之间不一致

- Status: confirmed
- Severity: medium
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
- Evidence:
  - 已嵌入 `workflow.md` 把 personal first-entry 的 minimum bootstrap fields 写成 `project_engagement_type`、`法律/合规风险结论`、`source_watermark_level`、`source_watermark_channels`、`zero_width_watermark_enabled`、`subtle_code_marker_enabled`、`ownership_proof_required`，缺少 `是否允许进入 brainstorm`。
  - 同一份已嵌入 `workflow.md` 的 `no_task -> B Create a task` 分支又进一步缩减成 `project_engagement_type=non_outsourcing + source_watermark_* + ownership_proof_required`，缺少 `法律/合规风险结论`、`zero_width_watermark_enabled`、`subtle_code_marker_enabled`、`是否允许进入 brainstorm`。
  - `brainstorm.md` 与 `validators_gates.py` 都要求 personal bootstrap 至少补齐 `project_engagement_type`、`法律/合规风险结论`、`source_watermark_level`、`source_watermark_channels`、`zero_width_watermark_enabled`、`subtle_code_marker_enabled`、`ownership_proof_required`、`是否允许进入 brainstorm`。
- Impact:
  - 用户若按已嵌入 `workflow.md` 的字段列表执行，会在离开 `brainstorm` 时被门禁拦下。
  - 这不是职责重叠问题，而是同一工作流不同入口的字段契约不一致。
- Validation action:
  - 对比 `/tmp/trellis-0.5.17-2/.trellis/workflow.md` 与 `brainstorm.md`、`validators_gates.py` 的字段枚举。

#### 2. `check` 阶段读取 spec 的说明依赖一个安装后并不存在的 `Quality Check` 导航结构

- Status: confirmed
- Severity: medium
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/check.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/spec/backend/index.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/spec/frontend/index.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/spec/backend/quality-guidelines.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/design.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Evidence:
  - `check.md` 要求先读 `.trellis/spec/<package>/<layer>/index.md`，再“跟随 `Quality Check` section 找到实际 guideline 文件”。
  - `/tmp/trellis-0.5.17-2` 中 backend/frontend index 仍是通用模板，只列出 `Quality Guidelines` 条目，并没有 `Quality Check` section，也没有工作流级导航语义。
  - 安装器只是把 `quality-guidelines.md` 从 Trellis 原生 “To be filled” 占位替换成“设计阶段 §3.7 决定矩阵”的说明，并没有同步让 layer index 具备 `check.md` 所要求的导航结构。
  - design 阶段虽然要求完成 spec 对齐和自动化检查矩阵，但当前验证只检查 task 工作底稿中的工程化联动关键词，不校验 index/guideline 导航是否可执行。
- Impact:
  - 用户在目标项目进入 `check` 阶段时，按文档无法稳定定位权威规则来源。
  - 这会导致“知道不能瞎猜命令”，但仍找不到应该从哪读取项目化验证矩阵与质量规则。
- Validation action:
  - 对比 `check.md` 的步骤说明与 `/tmp/trellis-0.5.17-2/.trellis/spec/backend/index.md`、`frontend/index.md` 的实际结构，并结合安装器 `patch_spec_quality_guidelines()` 行为核查。

### False Alarms / Non-Defects

#### A. “`.runtime` 目录缺失”不是安装缺陷

- Status: false alarm
- Source layers:
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/.gitignore`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/scripts/common/active_task.py`
  - `runtime command output`: `task.py start` 后按需生成 `.trellis/.runtime/sessions/codex_audit-probe.json`
- Evidence:
  - `.runtime/` 被显式纳入 `.gitignore`。
  - `active_task.py` 以 `.trellis/.runtime/sessions/` 作为 session-scoped active task 存储位置，并在写入时按需创建。
  - 在 `/tmp/trellis-0.5.17-2` 中执行 `CODEX_SESSION_ID=audit-probe python3 ./.trellis/scripts/task.py start 05-25-audit-probe` 后，`.trellis/.runtime/sessions/codex_audit-probe.json` 被即时创建。
- Conclusion:
  - `.runtime` 是运行时懒创建目录，不是嵌入安装时必须预置的托管资产。
  - 真问题如果要修，只能是“文档需要更清楚说明按需创建”，而不是“补建一个安装时常驻目录”。

#### B. “`task.py start` 缺少缺失 `workflow-state.json` 时的修复路径文档”不成立

- Status: false alarm
- Source layers:
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `runtime command output`: `workflow-state.py route .trellis/tasks/05-25-audit-probe --project-root /tmp/trellis-0.5.17-2`
- Evidence:
  - `workflow.md` 已明确：缺少 `workflow-state.json` 时会显示 `repair_needed`，而不是沿用 legacy planning 语义。
  - `workflow-state:repair_needed` 区块与 `workflow-state.py route` 的 JSON reason 都给出了 `workflow-state.py repair <task-dir>` 的修复路径，并区分 `repair_ready` 与 `manual_confirmation_required`。
  - 运行时验证中，缺少 `workflow-state.json` 的新建任务确实返回了带修复说明的 `repair_needed`。
- Conclusion:
  - 问题不是“没有文档化”，而是相关说明分散在 current-task 机制段、repair 状态块和 route helper 输出中。

#### C. “brainstorm bootstrap 与 feasibility 职责重复”不成立

- Status: false alarm
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/feasibility.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/validators_core.py`
- Evidence:
  - `feasibility` 负责完整评估、风险分析、`assessment.md` 正式输出与是否允许进入 `brainstorm` 的项目级决策。
  - personal first-entry 只是一个受控例外：允许先进入 `brainstorm`，但只能补最小 assessment 基线，而且离开 `brainstorm` 前仍要被正式门禁校验。
  - `is_personal_brainstorm_bootstrap_allowed()` 只在 `stage=brainstorm`、`status=in_progress`、无 `assessment.md`、安装记录 `profile=personal` 时返回 true，属于严格限定而不是重复流程。
- Conclusion:
  - 这里的真实问题不是职责重复，而是上面的“最小字段契约列举不一致”。

#### D. “`quality-guidelines.md` 被清空”表述不准确

- Status: false alarm
- Source layers:
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/spec/backend/quality-guidelines.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/spec/frontend/quality-guidelines.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Evidence:
  - 文件并未被清空，而是被安装器替换成“设计阶段 §3.7 决定 Verification Matrix，finish-work 阶段冻结”的工作流感知占位说明。
  - `工作流总纲 §3.7` 与 `design.md` 对“自动化检查矩阵”的主定义是存在的。
- Conclusion:
  - 真问题不在于文件为空，而在于 `check.md` 仍假设存在一个安装后可导航的质量规则入口。

## Proposed Repair Scope

- `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - 统一 personal-profile bootstrap 最小字段清单。
  - 统一 `no_task -> B Create a task` 中对 personal 直入 brainstorm 的字段要求。
- `docs/workflows/新项目开发工作流/commands/check.md`
  - 改写 Step 2，移除对不存在的 `Quality Check` section 的硬依赖。
  - 明确 `check` 阶段的权威读取顺序：项目化 spec index / quality-guidelines → design §3.7 沉淀的自动化检查矩阵与 `context7-review.md` → `finish-work-checklist.md` / task 产物。
  - 缺少项目化导航时要求标记 `[Evidence Gap]`，而不是假定 layer index 已被完善。
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - 视实现方式决定是否同步增强 installer 生成的 `quality-guidelines.md` 占位文案，使其与新的 `check.md` 读取顺序一致。
  - 若 `workflow.md` 的相关段落来自安装期字符串替换而非 markdown patch，还需同步更新对应 patch 常量，确保下次嵌入后的目标项目文本一致。
- `docs/workflows/新项目开发工作流/commands/shell/workflow_common.py`
  - 抽取 watermark / ownership / placeholder / yes-no 共享解析逻辑，作为低风险维护优化。
- `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`
  - 复用共享解析 helper，减少与其他 validator 的重复实现。
- `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`
  - 复用共享解析 helper，同时保留兼容别名，避免现有测试和外部调用断裂。

## Runtime Validation Summary

- `trellis -v` = `0.5.17`
- `COMPATIBLE_TRELLIS_VERSION` = `0.5.17`
- 在 `/tmp/trellis-0.5.17-2` 中创建并启动 `05-25-audit-probe`：
  - `task.py start` 会按需创建 `.trellis/.runtime/sessions/codex_audit-probe.json`
  - 缺少 `workflow-state.json` 时，`workflow-state.py route` 返回 `repair_needed` 且附带明确修复路径
- 本轮修复后验证：
  - `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_feasibility_check` → `41` tests, `OK`
  - `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state` → `132` tests, `OK`
  - `cd docs/workflows/新项目开发工作流/commands && /ops/softwares/python/bin/python3 -m unittest test_workflow_installers` → `139` tests, `OK`

## Additional Candidate Review

### Optimization Only

#### E. workflow 辅助脚本存在可收敛的验证逻辑重叠，但不是“没有统一验证框架”的真实缺陷

- Status: optimization-only
- Severity: low
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/validators_core.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/state_utils.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/delivery-control-validate.py`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`
- Evidence:
  - `workflow-state.py` 已把共享校验层拆分到 `validators_core.py` 与 `validators_gates.py`。
  - `validators_gates.py` 通过 `run_gate_validator()` 统一编排 `plan-validate.py`、`delivery-control-validate.py`、`ownership-proof-validate.py` 等阶段脚本。
  - `workflow_common.py`、`state_utils.py` 已承担字段提取、placeholder 判断、assessment lineage、validator subprocess 包装等公共工具职责。
  - 仍存在可继续抽取的重复逻辑，例如 yes/no 归一化、channels 解析、placeholder 规则、部分 assessment 字段校验散落在多个专用脚本中。
- Conclusion:
  - “没有统一验证框架或共享验证工具层”这个说法不成立。
  - 但“部分验证逻辑仍可进一步收敛，降低维护成本”成立，适合作为后续优化项。
  - 本轮已先做一轮低风险收敛：把 watermark / ownership / placeholder / yes-no 解析下沉到 `workflow_common.py`，并让 `feasibility-check.py`、`ownership-proof-validate.py` 复用。

### False Alarms / Non-Defects

#### F. `workflow-state.py route` 入口决策逻辑并不缺文档

- Status: false alarm
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
- Evidence:
  - `start-skill-patch-phase-router.md` 已给出 `route` 的调用方式、JSON `action` 表、各 action 的处理规则。
  - 已嵌入 `workflow.md` 中也保留了 route-only action blocks：`awaiting_confirmation`、`awaiting_confirmation_with_blockers`、`blocked`、`recovery_needed`、`repair_needed`、`embed_invalid`、`workflow-state.route_failed`，并有首次入口与 no-task 路由说明。
- Conclusion:
  - 更准确的说法是“route 文档分散在 workflow patch / workflow.md 中”，而不是“缺文档，只能读源码”。

#### G. allowed-next 约束与阶段命令执行面并不矛盾

- Status: false alarm
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `source repo`: `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
- Evidence:
  - `workflow-state.py set` 在阶段切换时执行 canonical transition 校验、`awaiting_user_confirmation` 校验、执行授权校验和 gate 校验。
  - 强门禁协议明确规定阶段命令只是当前阶段入口/执行面，不等于自动推进 `workflow-state.json.stage`。
  - 已嵌入 `workflow.md` 也明确写了 `task.py start` 不推进阶段，阶段切换仍需 `workflow-state.py set`。
- Conclusion:
  - 这里是“命令入口”和“状态切换”两个层级，不是约束失效。

#### H. `workflow-state.json` 生命周期不会在 archive 后污染新任务

- Status: false alarm
- Source layers:
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_store.py`
  - `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_utils.py`
- Evidence:
  - `cmd_archive()` 在归档前清理指向当前任务的 session 文件，然后把整个任务目录移动到 `archive/YYYY-MM/`。
  - `workflow-state.json` 位于任务目录内，因此会随目录一起归档，而不是留在活动任务区。
  - `task.py create` 创建的是新的任务目录，不会回读归档任务里的 `workflow-state.json`。
- Conclusion:
  - “archive 后残留的 workflow-state.json 会被下次 create 读到”这一前提不成立。

#### I. `review-gate -> delivery` 不要求 `project-audit` 通过是设计分层，不是漏门禁

- Status: false alarm
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `source repo`: `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/review-gate.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
- Evidence:
  - 强门禁协议明确定义：`review-gate` 是任务级补充审查，`project-audit` 是项目级全局审查，两者不是同一层。
  - `review-gate` 文档的设计就是“完成后在确认后转 delivery”。
  - 项目级条件满足时，`工作流总纲` 另外要求必须进入 `project-audit`；`validators_gates.py` 也对 `project-audit -> delivery` 单独做了 `project-audit.md` 校验。
- Conclusion:
  - 这不是“缺少 project-audit 前置条件”，而是任务级与项目级门禁分层。

### Confirmed And Fixed Documentation Gaps

#### J. `repair_needed -> workflow-state.py repair` 的恢复说明此前不够完整

- Status: confirmed and fixed
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- Evidence:
  - 原有 route 文案只提到 `repair_ready` / `manual_confirmation_required`，但没有把 inspect/apply 的推荐顺序、`repair_blocked` 的含义、以及恢复后的复核动作讲清。
  - `workflow-state.py repair` 本身已经输出 `repair_ready`、`manual_confirmation_required`、`repair_blocked`，而摘要层文档解释不足。
- Fix:
  - 在 `workflow-patch-projectization.md` 的 `[workflow-state:repair_needed]` block 中补全用法、状态含义和恢复步骤。
  - 同步增强 `start-skill-patch-phase-router.md` 与 `start-patch-phase-router.md` 的 `repair_needed` 行说明。

#### K. personal `brainstorm` bootstrap 与完整 `feasibility` 的关系说明此前不够清楚

- Status: confirmed and fixed
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/feasibility.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/brainstorm.md`
- Evidence:
  - 架构上并不存在“重复流程 defect”，但之前没有明确写清：personal 最小 baseline 只用于合法停留/离开 `brainstorm`，不等于完整 feasibility 评估；何时需要回到 `feasibility` 也不够明确。
- Fix:
  - 在 `workflow-patch-projectization.md` 的 `brainstorm` block 中补全“minimum baseline vs full feasibility assessment”与“何时回到 feasibility”的边界。
  - 在 `feasibility.md`、`brainstorm.md` 同步加上相同边界说明。

#### L. design 阶段 A/B/C/D 在嵌入 `workflow.md` 的摘要层定义不完整

- Status: confirmed and fixed
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/design.md`
- Evidence:
  - `design.md` 已有块 B/C/D 的详细产物定义，但嵌入 `workflow.md` 的强门禁摘要层此前只说 “block A/B/C/D”，没有给出最小文件映射，也没把 block D 与自动化检查矩阵明确关联。
- Fix:
  - 在 `workflow-patch-projectization.md` 的 `design` block 中新增 block/file mapping summary，并明确 block D 是冻结 automation/quality verification matrix 的区域。
  - 同时把 “每个 design block 都要停下来确认” 补到摘要层，避免与 `design.md` 的强门禁定义脱节。

#### M. `no_task` 下 A+ 分析模式的写入边界此前过于模糊

- Status: confirmed and fixed
- Source layers:
  - `source repo`: `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `source repo`: `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- Evidence:
  - 原文写 “analysis docs (research/, temp files)” 容易把项目根普通 docs/spec/workflow 资产误当作可写 scratch。
  - “Creates a task only if the user explicitly asks to act on findings” 也没把“从只读分析切换到 durable asset edits / implementation”这一类情况说清。
- Fix:
  - 在 `workflow-patch-projectization.md` 的 `[workflow-state:no_task]` block 中收紧为：仅允许写 disposable `tmp/` 或显式 analysis-only scratch 路径；明确普通 docs/spec/workflow 资产不算 temp files。
  - 同时明确：当下一步从只读分析转为 implementation / source editing / durable workflow asset updates 时，也必须创建 task。

## Additional Validation

- `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state docs.workflows.新项目开发工作流.commands.shell.test_feasibility_check docs.workflows.新项目开发工作流.commands.shell.test_ownership_proof_validate` → `173` tests, `OK`

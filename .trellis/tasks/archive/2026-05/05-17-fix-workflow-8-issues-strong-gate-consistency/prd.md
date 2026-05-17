# PRD: 修复新项目开发工作流强门禁8项一致性问题

## 背景

以 `/tmp/trellis-0.5.16-2` 为参照（已执行 `trellis init` + 工作流嵌入的目标项目），深入分析 `docs/workflows/新项目开发工作流` 嵌入后的实际运行一致性。发现8项问题：旧三阶段与新强门禁并存、面包屑与真实状态不一致、set 不执行完整门禁、状态机与文档矛盾、personal profile 路径不可达、收尾链路冲突、continue 旧路由优先、route/validate 职责边界不稳。

## 修复范围

仅修改 `docs/workflows/新项目开发工作流` 目录内的文件。修改后经 `install-workflow.py` 嵌入目标项目时，应确保8项问题均被修复，且不引入新问题。

## 8项问题及修复方案

### 问题1: 两套 workflow 并存，get_context --mode phase --step 仍返回旧三阶段步骤

**现象**: `workflow_phase.py` 的 `get_step()` 通过 `#### X.Y` 匹配步骤，嵌入后的 `workflow.md` 仍保留旧 Phase 1/2/3 的 `#### 1.0`/`#### 2.1` 等步骤标题。`get_context.py --mode phase --step 1.1` 返回旧 brainstorm 步骤而非强门禁阶段。

**修复方案**:
1. 在 `commands/shell/` 新增 `patch-workflow-phase.py`，安装器嵌入时打补丁到 `.trellis/scripts/common/workflow_phase.py`，使 `get_step()` 在检测到强门禁面包屑块存在时，拒绝返回旧 `#### X.Y` 步骤并提示使用 `workflow-state.py route`
2. 在 `workflow-patch-projectization.md` 中增加补丁指令：在 `## Phase 1: Plan` / `## Phase 2: Execute` / `## Phase 3: Finish` 三个旧节标题前加 `<!-- DEPRECATED: strong-gate model supersedes this section -->` 注释

### 问题2: 面包屑状态块与真实状态不一致

**现象**: `inject-workflow-state.py` hook 只读 `task.json.status`（planning/in_progress/completed），但强门禁模式下真实状态在 `workflow-state.json.stage`（feasibility/brainstorm/design 等）。hook 找不到 `[workflow-state:planning]` 等旧标签，退化到通用 "Refer to workflow.md" 提示。

**修复方案**:
1. 在 `commands/shell/` 新增 `patch-inject-workflow-state.py`，安装器嵌入时打补丁到各平台的 `inject-workflow-state.py`/`.js`，使其优先读取 `workflow-state.json.stage` 作为面包屑标签名，仅在无 workflow-state 时回退到 `task.json.status`
2. 补丁逻辑：如果 `$TASK_DIR/workflow-state.json` 存在且 `stage` 字段合法（在 STAGES 集合内），用 `stage` 值作为 `[workflow-state:TAG]` 匹配键

### 问题3: workflow-state.py set 并没有真正执行文档承诺的完整门禁

**现象**: `cmd_set` 只调用 `validate_state_shape` + `validate_execution_boundary`，不调用 `validate_external_project_controls` / `validate_ownership_policy_controls` / `validate_project_doc_boundary`。导致阶段可以 `set` 过去但门禁产物未齐。

**修复方案**:
1. 在 `commands/shell/workflow-state.py` 的 `cmd_set` 中，当 `--force` 未使用且发生阶段切换时，新增 `validate_stage_transition_gates()` 函数，根据目标阶段调用相关校验器：
   - 目标阶段 >= brainstorm: 调用 `validate_external_project_controls` + `validate_ownership_policy_controls`
   - 目标阶段 >= design: 额外调用 `validate_project_doc_boundary`
   - 目标阶段 in EXECUTION_STAGES: 额外检查 `execution_authorized`
2. 如果新增校验器报错，拒绝写入并提示缺失产物，与 `--force` 逻辑一致

### 问题4: 状态机和阶段文档互相打架

**现象**:
- check skill 说普通任务可直接进入 finish-work，但 STAGE_TRANSITIONS 只允许 check → review-gate 或 check → implementation
- implementation → test-first 的示例命令缺少 `--transition-from implementation`

**修复方案**:
1. 在 `commands/shell/workflow-state.py` 的 `STAGE_TRANSITIONS` 中，将 `"check": ["review-gate", "implementation"]` 改为 `"check": ["review-gate", "implementation", "finish-work"]`
2. 在 `workflow-patch-projectization.md` 的 Stage Transition Quick Reference 表中，修正 `implementation → test-first` 的 Step B 命令，加上 `--transition-from implementation`
3. 同步更新 breadcrumb block `[workflow-state:check]` 的描述，增加 "或直接进入 finish-work（无需 review-gate 的条件）"

### 问题5: no_task 入口的"personal profile 可跳过 feasibility"与脚本行为冲突

**现象**: no_task 面包屑说 personal profile 可以 `task.py create → brainstorm → task.py start`，但 `route` 无任务时固定返回 `first_entry → feasibility`，`validate` 对任何项目都要求 `assessment.md`。

**修复方案**:
1. 在 `commands/shell/workflow-state.py` 的 `cmd_route` 中，当 `action=first_entry` 时，检查项目根目录是否存在 `assessment.md`，若不存在且项目没有外包特征（无 `project_engagement_type` 记录），输出增加 `profile_hint` 字段：`"personal"` 或 `"outsourcing"`
2. 在 no_task 面包屑中明确：personal profile 可以跳过 feasibility 但必须在 brainstorm 阶段补齐 `assessment.md` 的核心字段（`project_engagement_type=non_outsourcing` + `source_watermark_*` + `ownership_proof_required`），否则无法通过后续阶段的门禁校验
3. 在 `validate_external_project_controls` 中，当 `assessment_file` 缺失时，如果当前阶段是 `brainstorm`，降级为 warning 而非 error（允许 personal profile 在 brainstorm 中补齐）

### 问题6: 收尾链路存在严重残留冲突

**现象**:
- finish-work SKILL.md 正文 Step 3 是 "Archive task(s)"，Step 4 是 "Record session journal"，但项目化补丁说 finish-work 不执行 archive / add_session
- workflow 引入了 record-session 终态，但 .agents/skills / .claude/commands / .opencode/commands 下没有 record-session 入口

**修复方案**:
1. 修改 finish-work-patch-projectization.md，明确声明 **覆盖** SKILL.md 正文中的 Step 3-4，替换为："Step 3: 确认 finish-work-checklist.md 已落盘 → 进入 delivery 阶段"
2. 新增 `commands/record-session.md` 命令文件，定义 record-session 阶段的具体操作：执行 `task.py archive` + `add_session.py`
3. 新增 `commands/delivery.md` 命令文件（若不存在）或确认已有
4. 确保安装器将 record-session.md 嵌入到 .claude/commands/trellis/ 和 .opencode/commands/trellis/ 和 .agents/skills/ 下

### 问题7: trellis-continue 入口仍先讲旧 status 路由

**现象**: continue 命令/技能文件前半段按 planning/in_progress/completed 路由到旧 Phase 1/2/3，后半段才追加强门禁 Phase Router。模型可能先执行旧路由。

**修复方案**:
1. 修改 `start-patch-phase-router.md`（continue 命令补丁），删除 Step 1-4 中的旧 status 路由逻辑（planning→1.1, in_progress→2.1 等），保留 Step 1 (get_context) 作为上下文收集，Step 2 直接进入 Phase Router
2. 修改 `start-skill-patch-phase-router.md`（continue 技能补丁），同样删除旧路由逻辑
3. 保留 "Reference" 段指向 workflow.md，但不作为路由决策依据

### 问题8: route 和 validate 的职责边界不稳

**现象**: route 只做部分 readiness 检查（collect_route_readiness_blockers），不调用 validate_external_project_controls / validate_ownership_policy_controls / validate_project_doc_boundary。route=reenter 不代表阶段真的满足门禁。

**修复方案**:
1. 在 `commands/shell/workflow-state.py` 的 `cmd_route` 中，当 action=reenter 且阶段 >= brainstorm 时，追加调用：
   - `validate_external_project_controls`（仅收集 errors，不阻止路由，但加入 `warnings` 字段输出）
   - `validate_ownership_policy_controls`（同上）
2. 路由结果 JSON 新增 `warnings` 字段，存放非阻断性门禁缺失提醒
3. 当 `action=reenter` 但存在 warnings 时，AI 仍可重入当前阶段，但需在输出中提示用户补齐

## 约束

1. 修复范围仅限 `docs/workflows/新项目开发工作流`，不修改其他目录
2. 修改 `workflow-state.py` 时不能破坏现有测试（`test_workflow_state.py`）
3. 新增补丁文件需确保安装器能正确嵌入
4. 不能引入新的状态不一致或门禁绕过路径
5. 所有补丁需与现有 `install-workflow.py` 的嵌入机制兼容

## 验证方式

1. 在 `/tmp/trellis-0.5.16-2` 上重新执行嵌入，验证8项问题是否修复
2. 运行 `commands/shell/test_workflow_state.py` 确保无回归
3. 手动验证 `get_context.py --mode phase --step 1.1` 不再返回旧步骤
4. 手动验证 `workflow-state.py route` 在 personal profile 场景下的行为
5. 验证 finish-work 命令不再包含 archive 步骤
6. 验证 record-session 命令/技能存在且可执行

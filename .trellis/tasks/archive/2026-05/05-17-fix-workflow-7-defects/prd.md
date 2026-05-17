# 修复新项目开发工作流 7 项结构性缺陷

## Goal

修复 `docs/workflows/新项目开发工作流/` 目录下的 7 项已验证的结构性缺陷，使嵌入目标项目后的工作流运行正常。修复范围仅限该目录，不修改其他目录。对于涉及 Trellis 原生文件的问题，通过在工作流中新增或完善补丁脚本来解决，由安装器在嵌入时应用。

## In Scope

1. **Stage Transition Quick Reference 缺少 `--execution-authorized true`**：`workflow-patch-projectization.md` 中 `check → implementation`（行157）和 `review-gate → implementation`（行160）缺少 `--execution-authorized true`；此外 `implementation → test-first`（行149）和 `test-first → implementation`（行151）虽然因前置状态已为 true 不会阻断，但文档应自洽地显式标注。`project-audit → review-gate` 的 `allowed-next` 包含 `implementation` 也需要对应命令行加上 `--execution-authorized true`。

2. **SessionStart hook 仍用旧 `task.json.status + prd/jsonl` 逻辑**：`.claude/hooks/session-start.py` 的 `_get_task_status()` 函数按 PLANNING/READY 判断路由，不使用 `workflow-state.py route`。安装器目前只补丁了 no-task 段的 NL 路由引用，没有让 `_get_task_status()` 委托给 workflow-state。需要在工作流中新增补丁脚本 `patch-session-start-strong-gate.py`，让安装器在嵌入时将 `_get_task_status()` 中有 active task 时的路由逻辑改为：优先读取 `workflow-state.json.stage`，存在时返回对应阶段的状态描述；不存在时 fallback 到旧逻辑。

3. **Plan 阶段出口门禁偏弱**：`workflow-state.py` 的 `validate_plan_gate()` 只检查 `task_creation_checklist.md` 存在且确认、`task_plan.md` 存在，不调用 `plan-validate.py` 的全面结构校验。需要在 `validate_plan_gate()` 中增加对 `plan-validate.py` 的调用（通过 subprocess），或在函数内扩展校验项（至少校验 task_plan.md 的关键章节和 leaf task prd.md 存在性）。

4. **Check 和 delivery 状态机门禁偏浅**：
   - `validate_check_gate()` 只要求 `check.md` 存在，不验证内容结构。需要增加最低内容校验（至少包含 "Changed Scope" 和 "Verification Results" 章节）。
   - `validate_delivery_gate()` 的 `DELIVERY_ARTIFACTS` 只包含 `acceptance.md` 和 `deliverables.md`，缺少 `transfer-checklist.md`。对于外包 profile 还缺少 `ownership-proof.md` 和 `source-watermark-verification.md`。需要扩展 `DELIVERY_ARTIFACTS`，并对外包 profile 增加额外产物门禁。

5. **finish-work 残留旧语义**：`.agents/skills/trellis-finish-work/SKILL.md` 原始 Step 2 文本仍说"current active task is always archived in Step 3 regardless"和"archive them too in this round"。补丁只替换了 Step 3/4，没有修正 Step 2 的误导语言。需要在 `finish-work-patch-projectization.md` 中增加 Step 2 语言的修正指令，让安装器在嵌入时清理 Step 2 中的 archive 误导表述。

6. **AGENTS.md NL 路由把"记录/保存进度"路由到 finish-work**：`install-workflow.py` 的 `_NL_ROUTING_SECTION` 行232 将"记录、保存进度、收工、结束工作"全部路由到 `/trellis:finish-work`。在强门禁模型中，"记录"和"保存进度"应路由到 `/trellis:record-session`，"收工"和"结束工作"保留路由到 `/trellis:finish-work`。需要拆分这行路由，并新增独立的 `record-session` 路由行。

7. **workflow_phase.py 的旧 step 查询返回值语义不清**：`patch-workflow-phase.py` 让 `get_step()` 在强门禁模式下返回 `None`，但函数签名返回 `str`，调用者不处理 `None`。需要修改补丁让 `get_step()` 返回空字符串加一个 stderr 提示信息（建议使用 workflow-state.py route），而不是 `None`。同时检查是否有其他类似调用者处理 None 的遗漏。

## Out of Scope

- 不修改 `docs/workflows/新项目开发工作流/` 之外的任何文件
- 不修改 Trellis 原生文件（只在工作流内新增/完善补丁脚本）
- 不修改安装器的核心安装流程逻辑（只调整 NL 路由表内容和补丁调用）
- 不做性能优化或与当前 7 项缺陷无关的任何改动
- 不对目标项目 `/tmp/trellis-0.5.16-2/` 做任何修改

## Acceptance Anchors

- 所有 7 项修复均在 `docs/workflows/新项目开发工作流/` 目录内完成
- Stage Transition Quick Reference 中所有进入 execution stage 的转换行均包含 `--execution-authorized true`
- `patch-session-start-strong-gate.py` 新脚本存在且能正确补丁 session-start.py 的 `_get_task_status()` 函数
- `workflow-state.py` 的 `validate_plan_gate()` 增加了 plan-validate.py 调用或等效扩展校验
- `validate_check_gate()` 增加了 check.md 最低内容校验
- `DELIVERY_ARTIFACTS` 包含 `transfer-checklist.md`；外包 profile 有额外产物门禁
- `finish-work-patch-projectization.md` 包含 Step 2 误导语言修正指令
- `install-workflow.py` 的 NL 路由表拆分了"记录/保存进度"和"收工/结束工作"
- `patch-workflow-phase.py` 的 `get_step()` 返回空字符串（而非 None），并在 stderr 打印提示

## Preferred CLI

Claude Code (主执行)
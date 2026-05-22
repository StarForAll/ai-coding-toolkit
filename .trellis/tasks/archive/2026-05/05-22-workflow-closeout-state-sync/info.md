# 实施说明

## 当前任务定位

这是一次 source workflow 收敛修复任务，目标是为后续新对话提供可直接执行的上下文，而不是在本轮完成全部实现。

## 下一对话应优先执行的工作

1. 先读本任务 `prd.md`
2. 读取并核对以下关键文件：
   - `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
   - `docs/workflows/新项目开发工作流/commands/delivery.md`
   - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
   - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
   - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
   - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
   - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
   - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
   - `docs/workflows/新项目开发工作流/完整流程演练.md`
   - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
   - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
   - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
   - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
   - `docs/workflows/新项目开发工作流/commands/shell/patch-task-status-view-strong-gate.py`
3. 先设计“单一 close-out 合同”，再统一回改所有引用文档和测试，不要先零散改文件。
4. 完成 source 修复后，至少执行与 close-out、record-session、workflow-state schema、test-first 直接相关的测试。

## 建议修复顺序

1. 确认单一 close-out 合同
   - 以 Trellis baseline `finish-work = archive + add_session` 为主
   - 明确 `delivery` 只负责验收/交付
   - 明确 `record-session` 是否仅保留为 legacy 兼容语义
2. 修 source contract
   - `finish-work-patch-projectization.md`
   - `delivery.md`
   - `workflow-patch-projectization.md`
   - `工作流总纲.md` / walkthrough / matrix / checklist 类文档
3. 修 installer / upgrade / assets / drift check
   - `workflow_assets.py`
   - `install-workflow.py`
   - `upgrade-compat.py`
4. 修 `workflow-state` 外围 schema 漂移
   - `patch-task-status-view-strong-gate.py`
   - `shell/workflow-state.py` 中相关调用/参数不一致
5. 修 `test-first` 定位漂移
   - 以《阶段状态机与强门禁协议》为主合同
   - 清理仍将其当独立 stage 的 source 说明
6. 更新测试并执行验证

## 风险提醒

* close-out 文档、测试和 installer 之间已经存在历史漂移，必须一次性全文同步，不要只修一个入口。
* `record-session` 若被收缩为 legacy 兼容入口，需要同步调整 source 文档、test fixture、upgrade drift 检查，避免留下新的假阳性。
* `test-first` 与 `finish-work` 都属于多载体反复引用的高传播规则，任何修订都必须做全文 grep 传播。

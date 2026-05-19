# Embedded Workflow Audit Notes

## Boundary

- Audit target: `docs/workflows/新项目开发工作流/`
- Generated target project sample: `/tmp/trellis-0.5.17-2`
- Version gate: `COMPATIBLE_TRELLIS_VERSION = 0.5.17`, `trellis -v = 0.5.17`

## Initial Evidence Summary

### 1. `project-audit` 编排缺口仍然真实存在

- `commands/project-audit.md` 把正式模式定义为“全部代码相关任务完成后，在最终质量门禁前做项目级统一回看”。
- `commands/workflow-patch-projectization.md` 与 `commands/shell/workflow-state.py` 的 transition graph 只允许 `implementation/test-first -> project-audit`，没有 `check/review-gate -> project-audit`。
- `commands/shell/workflow-state.py` 还把 `project-audit` 纳入 `LEAF_REQUIRED_STAGES`，会阻止带子任务的聚合 task 持有该阶段。

### 2. 任务列表状态展示仍然只显示裸 `stage`

- `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py` 的 `_display_status()` 只读取 `workflow-state.json.stage`，未消费 `workflow-state.py route` 的 `action/target/reason/blockers`。
- 与此相对，`patch-inject-workflow-state.py` 已把这些字段注入到 hooks breadcrumb，说明当前产品表意不一致。

### 3. `check-quality.py` 的证据表达仍偏弱

- 当前 helper 只接受 `--test-cmd` / `--lint-cmd` / `--typecheck-cmd`。
- 未提供命令时输出“跳过”，但没有标准化的 `not run` 结果文本。
- 失败时只打印 stdout，stderr 丢失；这会削弱证据链。

### 4. `task.py` 的旧语义残留仍存在

- `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` 仍保留 “Still flip task.json status: planning → in_progress...” 注释。
- 同文件帮助示例仍写 `python3 task.py list --mine --status in_progress`，与强门禁 stage-based display 已不一致。

## Likely Fix Surfaces

- `commands/shell/workflow-state.py`
- `commands/project-audit.md`
- `commands/workflow-patch-projectization.md`
- `commands/shell/check-quality.py`
- `commands/install-workflow.py`
- `commands/shell/patch-task-start-strong-gate.py`
- `commands/test_workflow_installers.py`
- `commands/shell/test_workflow_state.py`

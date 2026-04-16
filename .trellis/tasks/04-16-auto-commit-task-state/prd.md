# 让自动任务状态变更一起自动提交

## Goal

修复当前项目中任务归档等自动任务状态变更后的 metadata 提交行为，确保 `.trellis/tasks` 与 `.trellis/.current-task` 的自动修改会一起进入自动提交。

## Requirements

- 找出当前任务归档自动提交遗漏的 metadata 范围
- 修复自动提交逻辑，使 `.trellis/.current-task` 与 `.trellis/tasks` 一并提交
- 补充最小回归测试覆盖

## Acceptance Criteria

- [ ] 归档当前任务时，`.trellis/tasks` 与 `.trellis/.current-task` 一起进入自动提交
- [ ] 自动提交成功后，相关 metadata 路径保持干净
- [ ] 有针对该行为的最小回归测试

## Technical Notes

- 修改点：`.trellis/scripts/common/task_store.py`
- 回归测试：`.trellis/scripts/common/tests/test_task_store_archive_autocommit.py`

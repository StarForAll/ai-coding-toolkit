# 修复 archive auto-commit pathspec 回归

## Goal

修复本轮 `safe_commit` 收窄 staged 范围后引入的 close-out 回归：

- `task.py archive` 在任务目录已移动到 `archive/` 后，仍把已不存在的源 task path 传给 `git add`
- 导致 auto-commit 阶段出现 pathspec 未匹配，归档不会自动提交

## What I already know

* 当前问题是在真实 `finish-work` 路径中暴露的，不是纯测试问题
* 现状工作树只剩 `archive/2026-05/05-10-restore-trellis-upgrade-drift/` 未提交
* 相关实现位于 `.trellis/scripts/common/safe_commit.py` 与 `.trellis/scripts/common/task_store.py`
* 现有测试 `test_task_store_archive_autocommit.py` 已覆盖 archive auto-commit，但未覆盖“源 task 已不存在”的 pathspec 行为

## Requirements

* 修复 archive auto-commit 对已删除源 task path 的 staged 策略
* 不回退当前 `safe_commit` 的核心安全边界
* 为该场景补回归测试
* 不引入新的 close-out 回归

## Acceptance Criteria

* [ ] `task.py archive` 后 auto-commit 成功，不再出现 pathspec 未匹配
* [ ] 新增/更新测试先失败后通过
* [ ] 相关验证命令通过

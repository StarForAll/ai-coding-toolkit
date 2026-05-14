# PRD: 收敛 Trellis 运行时契约与降级路径

## Goal

修复当前项目 Trellis 运行时中两类收敛问题：

1. `task.py start` 在缺少 session identity 时仅提示 degraded mode，但不会留下任何可恢复的最小 active-task 运行时状态，导致后续 `task.py current`、statusline、部分 hook 链路能力明显折损。
2. Claude statusline 当前对 `stale` / degraded 场景不可见，运行时真实状态与用户可见反馈没有完全收敛。

本次只修复**当前项目正在使用的运行时工作流**，不修改 `docs/workflows/**` 产品化工作流 source 层。

## Scope

### In Scope

- `.trellis/scripts/task.py`
- `.trellis/scripts/common/active_task.py`
- `.claude/hooks/statusline.py`
- 与上述行为直接相关的本地回归测试
- 当前 task 的上下文文件与必要 spec 记录

### Out of Scope

- `docs/workflows/**`
- Trellis 上游 `trellis init` 基线内容
- 非当前项目运行时必须依赖的其他 CLI 目录大范围重构
- 新增复杂多会话调度或全新状态机

## Requirements

### R1: degraded mode 需要最小可恢复运行时状态

当 `task.py start <task>` 无法解析 session identity 时：

- 仍然保留当前已有行为：允许 `planning -> in_progress`
- 同时写入一个**受限的 degraded fallback active-task 状态**
- 后续无 session identity 的 `resolve_active_task()` / `task.py current` 可以在安全条件下解析该 fallback
- 该 fallback 不能破坏现有 “0 或 >=2 session files 不猜测” 的隔离原则

### R2: stale / degraded 需要在可见反馈层收敛

Claude statusline 需要：

- 正常 active task 时继续显示任务行
- `stale` 指针时给出明确可见标识，而不是静默降成“无任务”
- degraded fallback 时给出明确可见标识，让用户知道当前依赖的是降级路径

### R3: 不破坏现有 session-scoped 主路径

- 有正常 session identity 时，现有 session runtime 行为不变
- 现有 `session-fallback` 逻辑继续成立
- `clear_active_task()` / 归档清理 / stale 判断不能与新增 degraded fallback 冲突

### R4: 用测试固定契约

至少覆盖：

- degraded mode `task.py start` 会落盘 fallback 状态
- `resolve_active_task()` 能在受控条件下解析 degraded fallback
- statusline 在 normal / stale / degraded 三种路径下输出正确

## Acceptance Criteria

- [ ] `task.py start` 无 session identity 时，除提示外还会写入可恢复的 degraded fallback 状态
- [ ] `task.py current --source` 在 degraded fallback 存在且满足条件时能解析出当前任务来源
- [ ] Claude statusline 对 `stale` / degraded 不再静默隐藏
- [ ] 现有 `test_workflow_phase_contracts.py` 继续通过
- [ ] 新增或更新的 targeted tests 通过

## Risks

- degraded fallback 若设计过宽，可能在多窗口/多会话下误指向错误任务
- statusline 若输出过多，可能影响 Claude Code UI 可读性

## Mitigation

- degraded fallback 只在无 session identity 且无正常 session pointer 可用时参与解析
- 保持 fallback 为单文件、单任务、显式 source_type，并让 stale 判断继续生效
- statusline 仅增加简短标识，不扩展成长段诊断

## Verification

- `/ops/softwares/python/bin/python3 .trellis/scripts/common/tests/test_workflow_phase_contracts.py`
- 针对本次新增测试的 `unittest` 命令


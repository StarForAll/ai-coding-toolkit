# Candidate Issues To Validate

本文件记录用户提供的候选问题，作为审计假设列表，不代表已确认缺陷。

## 高优先级候选项

1. plan 阶段创建 child task 会偷偷切换当前 active task。
2. parent/child 方案与 leaf-only runtime 冲突。
3. 旧的 Phase step API 已失效，但仍有入口调用 `get_context.py --mode phase --step ...`。
4. per-turn breadcrumb 与 session-start 指引仍混用旧的 `PLANNING/READY`、`1.1/2.1` 语义。
5. `task.py start` 继续写 `task.json.status = in_progress`，与强门禁单一真相冲突。

## 中高优先级候选项

6. 安装完整性校验无法识别关键补丁未落地的“半迁移”状态。
7. personal profile 的首次入口路由错误地落到 `design`，而不是 `brainstorm`。

## 中优先级候选项

8. spec 层大面积仍是模板占位，影响“specs injected, not remembered”真实性。
9. `trellis-meta` 维护文档仍描述旧三阶段与旧收尾语义，易造成二次漂移。

## 审计原则

- 每条候选项都需要目标项目证据或源层静态证据支撑。
- 若发现同类问题，需一并记录并纳入修复范围。
- 假警报要明确标注，不进行无价值“优化”。

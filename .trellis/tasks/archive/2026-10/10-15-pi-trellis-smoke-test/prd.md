# PRD: Pi 平台 Trellis 全链路冒烟测试

## Background

当前项目（ai-coding-toolkit）已为 Pi 平台部署 Trellis 集成层：`.pi/extensions/trellis/index.ts`（SessionStart 上下文注入 + `trellis_subagent` 工具）、`.pi/prompts/trellis-*.md`、`.pi/agents/trellis-*.md`。需要实际验证这些组件在 Pi 运行时中的可用性，而非仅静态存在。

## Goal

对 Pi 平台的 Trellis 集成做一次端到端冒烟测试，覆盖：

1. **任务生命周期**：`task.py create` → PRD 填写 → `task.py start` → `task.py archive`
2. **上下文注入**：
   - SessionStart 注入 `<session-overview>` / `<trellis-workflow>` / first-reply-notice（本会话已验证）
   - 任务激活后 workflow-state breadcrumb 是否切换为当前任务状态
   - `trellis_subagent` 调度时子代理是否收到任务上下文（prd.md / implement.jsonl 注入）
3. **子代理调度**：通过 `trellis_subagent` 实际调度 `trellis-research` / `trellis-implement` / `trellis-check` 至少各一次（含一次并行模式可选）
4. **finish-work 收尾**：session 记录写入 journal

## Scope

- 测试工作全部在 `.trellis/` 任务目录与子代理返回内容中完成，**不改任何源码或工作流资产**
- 不干扰另一个平台的任务 `10-15-dsh-trellis-smoke-test`
- 测试任务完成后归档

## Acceptance Criteria

- [ ] `task.py create` 成功且会话绑定使用 Pi session key（`pi_*` 前缀）
- [ ] PRD 写入后 `task.py start` 成功，任务状态变为 in_progress，workflow-state 反映该状态
- [ ] `trellis_subagent` 以 `trellis-research` 或 `trellis-implement` 调度成功，子代理能复述任务目录与 PRD 关键内容（证明上下文注入生效）
- [ ] `trellis_subagent` 以 `trellis-check` 调度成功并返回检查结论
- [ ] `task.py archive` 成功，任务移入归档
- [ ] session 记录（journal）追加成功
- [ ] 全程未改动 `docs/`、`trellis-library/`、`.pi/` 等源资产

## Non-Goals

- 不修复测试中发现的问题（发现则如实记录为测试结果）
- 不做多平台对比

## Notes

- 证据来源：实际命令输出与子代理返回文本，逐项记录在最终测试报告中。

# PRD: ZCode 平台 Trellis 全链路冒烟测试

## Background

当前项目（ai-coding-toolkit）已为 ZCode 部署 Trellis 集成层：`.zcode/config.json`（SessionStart session-start.py、UserPromptSubmit inject-workflow-state.py、PreToolUse Agent|Task inject-subagent-context.py、PreToolUse Bash inject-shell-session-context.py 四类钩子）、`.zcode/agents/trellis-*.md`（research/implement/check 原生子代理）、`.zcode/skills/trellis-*`（9 个技能）、`.zcode/commands/trellis/{continue,finish-work}.md`。需要实际验证这些组件在 ZCode 运行时中的可用性，而非仅静态存在。

## Goal

对 ZCode 平台的 Trellis 集成做一次端到端冒烟测试，覆盖：

1. **任务生命周期**：`task.py create` → PRD 填写 → `task.py start` → `task.py archive`
2. **上下文注入**：
   - SessionStart 注入 compact 上下文 + first-reply-notice（本会话已验证）
   - UserPromptSubmit workflow-state breadcrumb 是否随任务状态切换（no_task → planning/in_progress）
   - PreToolUse Bash 钩子是否为 `task.py start/current/finish` 写会话票据（`.trellis/.runtime/shell-tickets/`）
   - Agent 调度时子代理是否收到任务上下文（`<!-- trellis-hook-injected -->` 标记 / prd.md + implement.jsonl 注入）
3. **子代理调度**：通过原生 Agent 工具（`subagent_type=trellis-implement` / `trellis-check`）各实际调度至少一次
4. **finish-work 收尾**：session 记录写入 journal，任务归档

## Scope

- 测试工作全部在 `.trellis/` 任务目录与子代理返回内容中完成，**不改任何源码或工作流资产**
- 唯一交付物为本任务目录内的 `report.md`（冒烟测试证据记录），由 trellis-implement 子代理撰写
- 测试任务完成后归档

## Acceptance Criteria

- [ ] `task.py create` 成功；会话绑定在 `task.py start` 后生效，`task.py current --source` 指向本任务（create 阶段不自动绑定，如实记录该行为）
- [ ] PRD 写入后 `task.py start` 成功，任务状态变为 in_progress，workflow-state 反映该状态
- [ ] Agent 工具以 `trellis-implement` 调度成功，子代理能复述任务目录与 PRD 关键内容，并说明是否收到 `<!-- trellis-hook-injected -->` 标记（证明上下文注入生效）
- [ ] Agent 工具以 `trellis-check` 调度成功并对 `report.md` 返回检查结论
- [ ] `task.py archive` 成功，任务移入归档
- [ ] session 记录（journal）追加成功
- [ ] 全程未改动 `docs/`、`trellis-library/`、`.zcode/`、`.agents/` 等源资产

## Non-Goals

- 不修复测试中发现的问题（发现则如实记录为测试结果）
- 不做多平台对比

## Notes

- 证据来源：实际命令输出与子代理返回文本，逐项记录在 `report.md`。

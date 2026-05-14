# 修复 Trellis 0.5.15 runtime 升级残留与 .new 处理

## Goal

基于当前仓库实际生效的 Trellis runtime，修正 `0.5.14 -> 0.5.15` 升级过程中错误接收、错误回退或遗漏的 carrier/runtime 改动，并按审计结论处理 `.new` 文件，确保当前 repo 的 live Trellis 合同继续成立。

## What I already know

- 当前本机 `trellis --version` 是 `0.5.15`，而 `/tmp/trellis-0.5.14/.trellis/.version` 是 `0.5.14`。
- 当前 repo 的 Trellis 主权威层是 `.trellis/`，平台目录仅是 carrier。
- 当前 repo 的 Codex 默认仍是 inline 模式，不能把 `.codex/agents/*` 当成 inline 主会话的随手逃生口。
- `Phase 2` 当前 live 合同要求 `trellis-implement` / `trellis-check` / `trellis-research` 的 dispatch prompt 第一行必须带 `Active task: <task path>`。
- 当前 diff 中，`trellis-research` 在 Claude/Codex/OpenCode/Qoder 上被错误弱化，删除了 richer search tool routing 和 `Active task` fallback。
- Kiro 当前 `trellis-research` 也仍是弱化版，即使这次没有出现在 diff 中，也与当前项目要求不一致。
- `.codex/config.toml.new`、`.codex/hooks.json.new`、`.trellis/workflow.md.new`、`.trellis/scripts/add_session.py.new`、`.trellis/scripts/common/safe_commit.py.new`、`.trellis/scripts/common/task_store.py.new` 需要逐项按“接受/丢弃/合并”处理。

## Assumptions

- 这次任务只修复当前项目自己的 Trellis runtime 与 carrier，不修改 `docs/workflows/新项目开发工作流/` 产品源层。
- 审计结论已被用户接受，可以直接执行，不需要再做方案确认。
- `.new` 文件代表本轮 `trellis update` 产生的候选，不应默认整体接收。

## Requirements

- 恢复并统一当前项目对 `trellis-research` 的 live 合同。
- `trellis-research` 需要支持 `ace.search_context` 等额外工具，不得退化成只靠基础 grep/web。
- `trellis-research` 必须恢复 `Active task: <task path>` dispatch prompt fallback。
- 处理 `.new` 文件：
- `.codex/config.toml.new` 只吸收有价值的上游说明，保留 repo-local inline 约束。
- `.codex/hooks.json.new` 按审计结论处理。
- `.trellis/workflow.md.new` 不得引入当前 repo 不存在的路径引用。
- `.trellis/scripts/add_session.py.new`、`safe_commit.py.new`、`task_store.py.new` 不得回退当前 repo 已有的 `session_auto_commit` / narrow staging / deletion staging 修复。
- 修复 `.template-hashes.json`，使其反映最终正确的 live 文件内容。
- 修复 `trellis-meta` 的 `change-workflow.md` 中对 `Phase 3.4` 的弱化描述。

## Acceptance Criteria

- [ ] `trellis-research` 在当前项目使用到的 carrier 上重新具备 richer tool routing 和 `Active task` fallback。
- [ ] Kiro carrier 不再与其他平台在 research 合同上明显漂移。
- [ ] `.new` 文件按结论处理，不再留下错误候选。
- [ ] `.template-hashes.json` 与最终保留内容一致。
- [ ] 文档/注释层不再弱化 `Phase 3.4 commit` 的当前 live 合同。
- [ ] 运行相关验证命令，至少覆盖 git diff/status 与相关 Python 单测。

## Out of Scope

- 不修改 `docs/workflows/新项目开发工作流/` 的 product workflow 源资产。
- 不做新的 Trellis 架构设计，只修复本轮升级残留。

## Technical Notes

- 审计依据主要来自 `.trellis/workflow.md`、`.trellis/config.yaml`、`.codex/config.toml`、各平台 `trellis-research` carrier、`.new` 候选与 `/tmp/trellis-0.5.14` 基线样本。
- 这次会话禁止使用 subagents，需保持 Codex inline 执行。

# Trellis 升级工作树差异分类

- Query: 分析当前仓库因 Trellis 升级引起的 `git status` / `git diff` 变化，区分正常升级改动、需回退的编号漂移、以及需要逐个判断的 `.new` 候选文件
- Scope: internal
- Date: 2026-05-06

## Findings

### 1. 可直接保留的正常升级改动

#### 1.1 版本升级

- `.trellis/.version` 从 `0.5.0-rc.3` 升至 `0.5.0-rc.5`
- 该变更本身是标准 Trellis 升级信号

#### 1.2 Hook disable guard

以下文件新增 `TRELLIS_HOOKS=0` / `TRELLIS_DISABLE_HOOKS=1` 的短路逻辑：

- `.claude/hooks/inject-workflow-state.py`
- `.codex/hooks/inject-workflow-state.py`
- `.opencode/plugins/inject-workflow-state.js`
- `.opencode/plugins/session-start.js`
- `.qoder/hooks/session-start.py`
- `.kiro/hooks/inject-subagent-context.py`

判断：

- 这是跨平台一致性的 runtime 兼容增强
- 不引入阶段口径漂移
- 应保留

#### 1.3 Active task fallback

`.trellis/scripts/common/active_task.py` 新增：

- `source_type="session-fallback"` 的 source 文案
- `_resolve_single_session_fallback()`：当无法解析上下文 key 且 runtime 中恰好只有一个 session 文件时，推断当前任务

判断：

- 该逻辑与 class-2 平台子代理无法继承父 session id 的问题直接对应
- 在 `0` 或 `>=2` 个 session 文件时拒绝猜测，边界合理
- 应保留

#### 1.4 子代理取任务路径说明

以下 agent 文件新增“先看 dispatch prompt 第一行的 `Active task:`，再 fallback 到 `task.py current --source`”说明：

- `.codex/agents/trellis-implement.toml`
- `.codex/agents/trellis-check.toml`
- `.qoder/agents/trellis-implement.md`
- `.qoder/agents/trellis-check.md`

判断：

- 与 `active_task.py` 的 fallback 逻辑一致
- 解决 class-2 平台上下文注入不足问题
- 应保留

### 2. 不应直接接受的 live 编号漂移

当前 live 文件中出现的主要新编号：

- `Phase 1.3`：表示“curate jsonl context”
- `Phase 1.4`：表示“run task.py start”
- `Phase 3.4`：表示“code commit”
- `Phase 3.5`：仅在参考文档中出现，表示“finish-work”

受影响 live 文件包括：

- `.agents/skills/trellis-continue/SKILL.md`
- `.claude/commands/trellis/continue.md`
- `.opencode/commands/trellis/continue.md`
- `.kiro/skills/trellis-continue/SKILL.md`
- `.qoder/commands/trellis-continue.md`
- `.qoder/hooks/session-start.py`
- `.opencode/lib/session-utils.js`
- `.kiro/hooks/inject-subagent-context.py`
- `.agents/skills/trellis-finish-work/SKILL.md`
- `.kiro/skills/trellis-finish-work/SKILL.md`
- `.qoder/commands/trellis-finish-work.md`

判断依据：

- 当前 live `.trellis/workflow.md` 仍使用原始阶段口径，Finish 摘要仍是“Commit code, then archive + record session via /finish-work”
- 2026-05-05 仓库审计已明确认定：
  - `.trellis/workflow.md.new` 的 `3.1 -> 3.4` 属于 phase-number drift
  - `.trellis/scripts/task.py.new` 的 `1.2 -> 1.3` 也不应盲合并

处理结论：

- live 文件中的阶段编号要恢复为仓库原口径
- 不接受这批编号迁移为当前 repo 合同

### 3. 格式噪音

发现以下文件存在多余反引号等无语义收益格式变化：

- `.agents/skills/trellis-brainstorm/SKILL.md`
- `.agents/skills/trellis-update-spec/SKILL.md`

判断：

- 不像必要升级内容
- 应回退

### 4. `.new` 文件的性质与处理原则

当前未跟踪 `.new` 文件：

- `AGENTS.md.new`
- `.claude/commands/trellis/finish-work.md.new`
- `.claude/hooks/inject-subagent-context.py.new`
- `.claude/hooks/session-start.py.new`
- `.codex/config.toml.new`
- `.codex/hooks/session-start.py.new`
- `.opencode/commands/trellis/finish-work.md.new`
- `.opencode/lib/trellis-context.js.new`
- `.opencode/package.json.new`

判断依据：

- `.agents/skills/trellis-meta/references/local-architecture/generated-files.md` 规定：当 live 文件已被用户修改时，`trellis update` 生成 `.new` 属于正常保护行为
- 仓库已有升级残留审计规定：`.new` 文件不是“升级成功后的稳定状态”，而是待明确处置的候选补丁

处理原则：

- 不采用统一策略
- 每个 `.new` 文件都要单独判断：
  - 删除
  - 保留待后续
  - 直接择一采用
  - 与 live 文件合并

## Recommended handling

1. 保留正常 runtime / hook / agent context 增强。
2. 回退所有 live 阶段编号漂移，继续使用原编号口径。
3. 回退无意义格式噪音。
4. 逐个评估 `.new` 文件，不把它们直接视为应提交内容。
5. 在最终保留集确定后，再刷新 `.trellis/.template-hashes.json`。

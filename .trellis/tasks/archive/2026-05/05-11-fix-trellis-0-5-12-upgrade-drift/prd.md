# Fix Trellis 0.5.12 Upgrade Drift

## Goal

修复 `trellis update` 自动应用和 `.new` 候选文件中的三类问题：(1) trellis-research agent 工具列表被错误剥离，(2) .new 文件等待处置决策，(3) safe_commit.py .new 存在 archive 路径暂存回归。

## Decision (ADR-lite)

**Context**: trellis update 0.5.12 自动覆盖了 4 个 research agent（因为 template-hash 匹配了上次提交的定制版哈希），同时产生了 20 个 .new 文件等待审查。

**Decisions**:
1. trellis-research 工具恢复 → 恢复到 git 上一提交版本（含完整 MCP 工具 + 6 类型路由表）
2. safe_commit.py / task_store.py / add_session.py .new → 选择性合并（采纳新特性，修复回归）
3. codex .new → 丢弃（保留 inline-mode 安全守卫）
4. brainstorm/continue/finish-work .new → 覆盖（Phase 修正正确）
5. change-workflow.md → 修正描述（3.1 不含 spec update，应为 3.1→3.3→3.4）

**Consequences**: 手动合并 safe_commit.py 可能引入新 bug，需针对性测试。

## Requirements

### R1: 恢复 trellis-research 完整工具列表
- 恢复 `.claude/agents/trellis-research.md` 到 git HEAD 版本
- 恢复 `.opencode/agents/trellis-research.md` 到 git HEAD 版本
- 恢复 `.qoder/agents/trellis-research.md` 到 git HEAD 版本
- `.codex/agents/trellis-research.toml` 也需恢复到 HEAD 版本（含完整工具列表 + inline-mode 守卫）

### R2: 处理 .new 文件 — 覆盖类（14 个）
- `*/trellis-brainstorm/SKILL.md.new` → `mv .new → 原文件`（5 个）
- `*/trellis/continue.md.new` → `mv .new → 原文件`（2 个）
- `*/trellis-continue/SKILL.md.new` → `mv .new → 原文件`（2 个）
- `*/trellis-finish-work/SKILL.md.new` → `mv .new → 原文件`（2 个）
- `.qoder/commands/trellis-finish-work.md.new` → `mv .new → 原文件`（1 个）
- 覆盖后更新 template-hashes.json 中的对应条目

### R3: 处理 .new 文件 — 丢弃类（4 个）
- `.codex/agents/trellis-research.toml.new` → 删除
- `.codex/agents/trellis-implement.toml.new` → 删除
- `.codex/agents/trellis-check.toml.new` → 删除
- `.codex/config.toml.new` → 删除

### R4: 选择性合并 safe_commit.py
- 采纳 .new 中的 `session_auto_commit: false` 支持（函数内检查，早期返回）
- 采纳 .new 中的改进警告消息
- 保留 `include_removals` 参数（用于 archive 场景的 `git add -A`）
- 保留 `_path_is_tracked` 函数
- 修复：archive commit 必须用 `include_removals=True` 才能暂存源目录删除

### R5: 选择性合并 task_store.py
- 采纳 .new 中的 all-active-tasks 遍历路径策略
- 适配 safe_commit.py 的 `include_removals` 保留

### R6: 选择性合并 add_session.py
- 采纳 .new 中的改动（需逐一审查差异）

### R7: 修正已应用的修改
- 4 个 `change-workflow.md`: 修正 "3.1 (verify quality + spec update)" → "Phase 3.1 → 3.3 → 3.4"

### R8: 清理与收尾
- 删除 backup 内嵌套的 .new 文件（2 个）
- 修复 template-hashes.json 末尾换行符
- 更新 template-hashes.json 使其与所有最终文件内容一致

## Acceptance Criteria

- [ ] `git diff HEAD -- .claude/agents/trellis-research.md` 无差异（完全恢复）
- [ ] `git diff HEAD -- .opencode/agents/trellis-research.md` 无差异
- [ ] `git diff HEAD -- .qoder/agents/trellis-research.md` 无差异
- [ ] `.codex/agents/trellis-research.toml` 包含完整工具列表 + inline-mode 守卫
- [ ] 无残留 .new 文件（项目根目录 `.git` 之外不含 .new）
- [ ] safe_commit.py 保留 `include_removals` + `_path_is_tracked` + 新增 `session_auto_commit` 支持
- [ ] change-workflow.md 入口为 "Phase 3.1 → 3.3 → 3.4" 而非合并描述
- [ ] template-hashes.json 哈希与实际文件内容一致 + 末尾有换行

## Definition of Done

- 所有 .new 文件已处置（覆盖/合并/丢弃/删除）
- 所有已修改文件逻辑正确
- template-hashes.json 与实际内容一致
- 工作区仅有预期变更

## Out of Scope (explicit)

- 不修改 workflow.md 本身
- 不修改全局 rules 文件
- 不升级 trellis npm 包版本
- 不做 backup 目录的全面清理（仅删除其中嵌套的 .new）
- 不修复 template-hash 导致"下次 update 又覆盖"的根本机制问题（那是 trellis 上游的设计限制）

## Technical Notes

### trellis-research 恢复细节
4 个文件直接 `git checkout HEAD -- <path>` 即可，因为 HEAD 版本就是定制后的完整版本。
codex 版本还额外需要恢复 inline-mode 安全守卫头。

### safe_commit.py 合并策略
以 HEAD 版本为基础，手动合入 .new 的以下改进：
1. `session_auto_commit` 检查下沉到 `safe_git_add` / `_auto_commit_session` 内部
2. 改进的警告消息（含 config.yaml 提示路径）
3. `safe_git_add` 签名保留 `used_force` 返回值兼容（但始终 False）

不采纳的 .new 变更：
- 移除 `include_removals` 参数
- 移除 `_path_is_tracked` 函数
- `safe_archive_paths_to_add` 简化（丢失 tracked 检测）

### add_session.py 合并
需对比 HEAD 与 .new 差异，待实现时审查。

### template-hashes 更新
覆盖类 .new 文件后，其内容已变更，hash 需要更新为 trellis 0.5.12 模板的预期值（即 .trellis/.template-hashes.json 中已自动更新的值）。对于恢复到 HEAD 的文件（research agents），hash 也需恢复到 HEAD 的值。

### change-workflow.md Phase 描述
workflow.md 实际 Phase 3 结构：
- 3.1 Quality verification
- 3.3 Spec update
- 3.4 Commit changes
正确入口是 3.1，但流程经过 3.3 和 3.4，不应合并描述。

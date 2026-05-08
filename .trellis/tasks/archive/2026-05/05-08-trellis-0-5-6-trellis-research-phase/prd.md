# 修复 Trellis 0.5.6 升级缺陷：回退 trellis-research 工具简化并修正 Phase 编号

## Goal

修复 Trellis 0.5.6 升级过程中的两个关键缺陷：
1. **trellis-research 工具被错误简化**：移除了 ace.search_context、Context7、deepwiki、grok-search 等核心研究工具
2. **Phase 编号不一致**：workflow-state blocks 中的 Phase 引用（1.3, 3.4）与 Phase Index（1.1, 1.2, 1.3）不匹配

确保升级后的 Trellis 保持功能完整性和文档一致性。

## What I already know

### 问题来源
- Trellis 从早期版本升级到 0.5.6，产生了 `.new` 文件
- 用户已对 `.new` 文件进行了分析，识别出两类缺陷

### trellis-research 工具简化问题
**受影响文件**：
- `.claude/agents/trellis-research.md` - 工具列表从 20+ 减少到 7 个
- `.codex/agents/trellis-research.toml` - permission 中移除了多个 MCP 工具
- `.opencode/agents/trellis-research.md` - 同样简化
- `.qoder/agents/trellis-research.md` - 同样简化
- `.kiro/agents/trellis-research.json` - 状态未知（未在 git diff 中）

**被错误移除的工具**：
- `mcp__ace__search_context` - 代码语义搜索（核心工具）
- `mcp__Context7__resolve-library-id` / `mcp__Context7__query-docs` - 第三方库文档查询
- `mcp__deepwiki__read_wiki_structure` / `mcp__deepwiki__read_wiki_contents` / `mcp__deepwiki__ask_question` - GitHub 仓库文档
- `mcp__grok-search__web_search` / `mcp__grok-search__web_fetch` - 实时网络搜索
- `mcp__exa__web_fetch_exa` - 网页抓取
- `mcp__exa__web_search_advanced_exa` - 深度搜索

**影响**：
- 失去代码语义搜索能力
- 无法查询第三方库文档
- 无法理解 GitHub 仓库
- 无法进行实时信息检索

### Phase 编号不一致问题

**workflow.md.new 的 Phase Index**：
```
1.1 Brainstorm / PRD
1.2 Curate JSONL Context
1.3 Enter Execute Phase
2.1 Implement
2.2 Check
2.3 Update Spec
3.1 Commit & Verify
3.2 Close-Out
```

**workflow.md.new 的 workflow-state blocks 引用**：
- Line 515: `Phase 1.3` (planning state)
- Line 521: `Phase 3.4` (in_progress state)
- Line 522: `Phase 3.4` (in_progress state)
- Line 529: `Phase 3.4` (completed state)
- Line 530: `Phase 3.4` (completed state)

**其他文件中的不一致引用**：
- `.claude/commands/trellis/continue.md` - 引用 1.3 和 1.4
- `.trellis/scripts/common/task_context.py.new` - Line 11-14 引用 Phase 1.3
- `.trellis/scripts/common/task_store.py.new` - Line 287 引用 Phase 1.3
- `.claude/commands/trellis/finish-work.md.new` - 引用 Phase 3.4

**根本原因**：升级漂移导致的不一致，试图调整引用但未同步更新 Phase Index

### 其他已确认正确的变更
- ✅ 移除 readonly git failure handling（task.py, add_session.py, task_store.py）
- ✅ 移除 `archive-commit-only` 命令
- ✅ 添加 iFlow 和 Pi Agent 平台支持
- ✅ YAML 解析器内联到 config.py
- ✅ 新增 generated-files.md 文档

## Assumptions (temporary)

1. Phase 编号体系应保持稳定，不引入破坏性变更
2. trellis-research 工具简化是升级过程中的错误，应完全回退
3. 其他平台（codex, opencode, qoder）的 trellis-research 也需要同步回退
4. .kiro/agents/trellis-research.json 可能也需要检查和修复

## Open Questions

暂无阻塞性问题。需求已从分析中明确得出。

## Requirements

### R1: 回退 trellis-research 工具简化

**范围**：所有平台的 trellis-research agent 定义文件

**回退文件清单**：
1. `.claude/agents/trellis-research.md`
2. `.codex/agents/trellis-research.toml`
3. `.opencode/agents/trellis-research.md`
4. `.qoder/agents/trellis-research.md`

**验证**：检查 `.kiro/agents/trellis-research.json` 是否需要同步修复

**操作**：使用 `git checkout -- <file>` 回退到原版

### R2: 修正 Phase 编号引用

**修正策略**：保持 Phase Index 不变，将所有 workflow-state blocks 和文档中的引用调整回原有编号

**修正文件清单**：

1. **workflow.md.new**
   - Line 515: `Phase 1.3` → `Phase 1.2`
   - Line 521: `Phase 3.4` → `Phase 3.1`
   - Line 522: `Phase 3.4` → `Phase 3.1`
   - Line 529: `Phase 3.4` → `Phase 3.1`
   - Line 530: `Phase 3.4` → `Phase 3.1`

2. **.claude/commands/trellis/continue.md**
   - Line 28: `1.3` → `1.2`
   - Line 29: `1.4` → `1.3`
   - Line 38: `1.3` → `1.2`

3. **.trellis/scripts/common/task_context.py.new**
   - Line 11-14: `Phase 1.3` → `Phase 1.2`

4. **.trellis/scripts/common/task_store.py.new**
   - Line 287: `Phase 1.3` → `Phase 1.2`

5. **.claude/commands/trellis/finish-work.md.new**
   - Line 3: `Phase 3.4` → `Phase 3.1`
   - Line 38: `Phase 3.4` → `Phase 3.1`
   - Line 64: `Phase 3.4` → `Phase 3.1`

### R3: 合并正确的 .new 文件

**覆盖文件清单**（Phase 修正后）：
1. `workflow.md.new` → `workflow.md`
2. `task.py.new` → `task.py`
3. `add_session.py.new` → `add_session.py`
4. `task_context.py.new` → `task_context.py`（修正后）
5. `cli_adapter.py.new` → `cli_adapter.py`
6. `task_store.py.new` → `task_store.py`（修正后）
7. `config.py.new` → `config.py`
8. `finish-work.md.new` → `finish-work.md`（修正后）

**保留原版文件**：
1. `config.yaml.new` - 原版注释更详细

**添加新文件**：
1. `generated-files.md.new` - 所有平台（.claude, .kiro, .opencode, .qoder, .agents）

### R4: 验证和清理

1. 验证 `.trellis/.template-hashes.json` 是否需要更新
2. 清理所有 `.new` 文件
3. 验证所有修改的一致性

## Acceptance Criteria

- [ ] 所有 4 个 trellis-research 文件已回退到原版（包含完整工具列表）
- [ ] 所有 Phase 引用已修正为原有编号（1.2, 3.1）
- [ ] 所有正确的 .new 文件已合并
- [ ] `config.yaml` 保留了详细注释版本
- [ ] 所有平台的 `generated-files.md` 已添加
- [ ] `.kiro/agents/trellis-research.json` 已检查和修复（如需要）
- [ ] 所有 `.new` 文件已清理
- [ ] `git status` 显示干净的修改列表（无 .new 文件残留）
- [ ] 通过 grep 搜索验证无遗漏的 Phase 1.3/3.4 引用

## Definition of Done

- [ ] 所有修改已提交，commit message 遵循 `fix(trellis): 回退 trellis-research 工具简化并修正 Phase 编号`
- [ ] 所有文件修改已验证（grep 检查）
- [ ] 无遗留的 `.new` 文件
- [ ] template-hashes.json 已更新（如需要）
- [ ] 无 lint/test 错误
- [ ] 文档更新已检查

## Out of Scope

- 不修改 Phase Index 结构（保持原有编号体系）
- 不引入新的 Phase 编号体系
- 不修改其他 trellis-core 功能
- 不修改任何 spec 文件
- 不创建新的 research 输出文件（此任务不涉及研究）

## Technical Notes

### 关键约束
- Phase 编号体系必须保持稳定，避免破坏性变更
- trellis-research 必须保留完整工具集以支持研究工作流

### 受影响的文件总数
- 回退文件：4 个 trellis-research agent 定义
- Phase 修正文件：5 个文件
- 覆盖文件：8 个 .new 文件
- 新增文件：5 个 generated-files.md（各平台）

### 验证命令
```bash
# 验证无 Phase 1.3 引用（除 Phase Index 中的正确位置）
grep -rn "Phase 1\.3" .trellis/ .claude/ .kiro/ .opencode/ .qoder/ .codex/ --include="*.md" --include="*.py" | grep -v "Phase Index"

# 验证无 Phase 3.4 引用
grep -rn "Phase 3\.4" .trellis/ .claude/ .kiro/ .opencode/ .qoder/ .codex/ --include="*.md" --include="*.py"

# 验证无 .new 文件
find . -name "*.new" -type f
```

### 实现顺序
1. 回退 trellis-research 文件（R1）
2. 修正 Phase 编号（R2）
3. 合并 .new 文件（R3）
4. 验证和清理（R4）

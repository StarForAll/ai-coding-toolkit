# PRD: 处理 Trellis 0.5.17 升级 .new 文件

## 背景

当前项目从 Trellis 0.5.16 升级到 0.5.17，升级脚本在需要替换的文件旁生成了 `.new` 文件（而非直接覆盖），需要人工审查后决定每个 .new 文件的处置方式。

已完成的深度分析确认：
- **所有 .new 文件都与参考项目 `/tmp/trellis-0.5.17/` 中对应文件完全一致**
- 应用 .new = 回退到 baseline 0.5.17，会丢失当前项目所有本地增强
- 当前项目的本地增强分 4 类：degraded 机制（应移除）、MCP 工具增强（应保留）、Codex 安全注释（应保留）、.kiro/ 平台（应保留）

## 0.5.17 升级主题

1. **移除 degraded active-task 回退机制** — "没有 session 身份 = 没有 active-task"
2. **移除 `[workflow-state:stale]` 伪状态及显示逻辑**
3. **简化 auto-commit 流程** — 移除 `include_removals` 参数和 `git rm --cached` 条件守卫
4. **Research Agent 降级** — 参考项目 research agent 只有 exa + Skill，当前项目有 ace/Context7/deepwiki/grok-search/exa 全套
5. **新增 `.current-task` 常量和 gitignore 规则** — 过渡标记
6. **新增 `trellis-spec-bootstarp` skill** — 5 个平台均有（目录名有拼写错误，上游问题）

## 实施方案

### Step 1: OVERWRITE — 用 .new 替换原文件（13 个）

这些文件中的本地增强是已废弃的 degraded 机制，应随上游移除：

```
# Hooks (4) — 移除 stale/degraded display 逻辑
.claude/hooks/inject-workflow-state.py.new → .claude/hooks/inject-workflow-state.py
.codex/hooks/inject-workflow-state.py.new → .codex/hooks/inject-workflow-state.py
.qoder/hooks/inject-workflow-state.py.new → .qoder/hooks/inject-workflow-state.py
.opencode/plugins/inject-workflow-state.js.new → .opencode/plugins/inject-workflow-state.js

# OpenCode 库 (1) — 移除 _resolveDegradedActiveTask()
.opencode/lib/trellis-context.js.new → .opencode/lib/trellis-context.js

# Workflow 文档 (1) — 移除 stale 块、改 degraded fallback 为 fail-with-hint
.trellis/workflow.md.new → .trellis/workflow.md

# 核心脚本 (4) — 移除 degraded fallback、简化 auto-commit
.trellis/scripts/task.py.new → .trellis/scripts/task.py
.trellis/scripts/common/active_task.py.new → .trellis/scripts/common/active_task.py
.trellis/scripts/common/safe_commit.py.new → .trellis/scripts/common/safe_commit.py
.trellis/scripts/common/task_store.py.new → .trellis/scripts/common/task_store.py
.trellis/scripts/add_session.py.new → .trellis/scripts/add_session.py

# 配置 (2) — 添加 .current-task gitignore、FILE_CURRENT_TASK 常量
.trellis/.gitignore.new → .trellis/.gitignore
.trellis/scripts/common/paths.py.new → .trellis/scripts/common/paths.py
```

操作方式：`mv file.new file`（直接覆盖）

### Step 2: DISCARD — 删除 .new，保留当前版本（5 个）

这些文件的本地增强是有价值的，不应回退：

```
# Codex config — 保留 inline-mode 安全注释（防止 inline session 手动 spawn sub-agent）
.codex/config.toml.new → 删除 .new，保留当前版本

# Codex agents — 保留 carrier 注释（4行安全文档）
.codex/agents/trellis-check.toml.new → 删除 .new，保留当前版本
.codex/agents/trellis-implement.toml.new → 删除 .new，保留当前版本

# Codex research — 保留 enriched MCP 工具路由 + carrier 注释
.codex/agents/trellis-research.toml.new → 删除 .new，保留当前版本

# __init__.py — 影响极小，但当前版本更完整
.trellis/scripts/common/__init__.py.new → 删除 .new，保留当前版本
```

### Step 3: RETAIN — 删除 .new，保留当前 enriched 版本（5 个）

当前项目的 research agent 比参考项目多出大量 MCP 工具（ace、Context7、deepwiki、grok-search、exa advanced），回退将严重削弱调研能力：

```
# Claude research — 保留 10 个 MCP 工具 + 搜索路由表 + 3-step 解析
.claude/agents/trellis-research.md.new → 删除 .new，保留当前版本

# OpenCode research — 保留 MCP 工具权限
.opencode/agents/trellis-research.md.new → 删除 .new，保留当前版本

# Qoder research — 保留 MCP 工具路由
.qoder/agents/trellis-research.md.new → 删除 .new，保留当前版本

# Kiro research — 参考项目无 .kiro/ 目录，回退会丢失整个 Kiro 平台支持
.kiro/agents/trellis-research.json.new → 删除 .new，保留当前版本

# __init__.py 已在 Step 2 处理
```

当前 enriched 版本额外工具列表（不应丢失）：
- `mcp__ace__search_context` — 代码语义搜索
- `mcp__exa__web_fetch_exa` — 网页内容抓取
- `mcp__exa__web_search_advanced_exa` — 高级搜索
- `mcp__Context7__resolve-library-id` + `query-docs` — 第三方库文档
- `mcp__deepwiki__read_wiki_structure` + `read_wiki_contents` + `ask_question` — GitHub 仓库文档
- `mcp__grok-search__web_search` + `web_fetch` — 实时信息检索
- 3-step task resolution（dispatch → task.py current → ask user）
- 搜索路由表（internal → ace, library → Context7, repo → deepwiki, realtime → grok-search）

### Step 4: 清理 .new 文件

确保所有 22 个 .new 文件都已处理（mv 或 rm），不留残留。

```bash
find . -name "*.new" -type f | head -30  # 应返回空
```

### Step 5: 处理新增的未跟踪目录

5 个平台的 `trellis-spec-bootstarp/` skill 目录是 0.5.17 新增内容，应保留并纳入版本控制：

```
.agents/skills/trellis-spec-bootstarp/
.claude/skills/trellis-spec-bootstarp/
.kiro/skills/trellis-spec-bootstarp/
.opencode/skills/trellis-spec-bootstarp/
.qoder/skills/trellis-spec-bootstarp/
```

注意：目录名 "bootstarp" 是拼写错误（应为 "bootstrap"），但参考项目中也是同样拼写，属于上游问题，本期不修。

### Step 6: 处理已修改的跟踪文件

这两个文件已在 git diff 中（unstaged），无需额外操作：

- `.trellis/.version` — 0.5.16 → 0.5.17（正确）
- `.trellis/.template-hashes.json` — 新增 25 个 spec-bootstarp skill 哈希（正确）

### Step 7: 验证

```bash
# 1. 确认无残留 .new 文件
find . -name "*.new" -type f

# 2. 验证 task.py 功能正常
python3 ./.trellis/scripts/task.py current --source

# 3. 验证 active_task.py 不再有 degraded 函数
python3 -c "from scripts.common.active_task import get_degraded_active_task" 2>&1 | grep -q "ImportError" && echo "OK: degraded removed" || echo "FAIL: degraded still exists"

# 4. 验证 workflow.md 无 stale 块
grep -c "workflow-state:stale" .trellis/workflow.md  # 应为 0

# 5. 验证 research agent 保留 MCP 工具
grep -c "mcp__ace__" .claude/agents/trellis-research.md  # 应 > 0
grep -c "mcp__Context7__" .claude/agents/trellis-research.md  # 应 > 0

# 6. 验证 Codex config 保留安全注释
grep -c "inline-mode rule" .codex/config.toml  # 应 > 0
```

## 关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| Degraded 机制 | 移除（OVERWRITE） | 上游已废弃，引入跨窗口状态混乱风险 |
| Research Agent MCP 工具 | 保留（DISCARD .new） | 丢失将严重削弱调研能力，参考项目只是基线 |
| Codex inline-mode 注释 | 保留（DISCARD .new） | 防护 inline session 误 spawn sub-agent |
| Codex carrier 注释 | 保留（DISCARD .new） | 有价值的文档 |
| .kiro/ 平台 | 完整保留 | 参考项目无 .kiro/，回退会丢失平台支持 |
| "bootstarp" 拼写 | 暂不修 | 上游问题，等上游修 |

## 风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 移除 degraded 后 shell/manual 流程无 active-task | 中 | `.current-task` gitignore 是防御层；纯 session 流程不受影响 |
| Research Agent 误回退 MCP 工具 | 高 | Step 3 明确保留 enriched 版本 |
| Codex 安全注释误删 | 中 | Step 2 明确 DISCARD config.toml.new |
| `.kiro/` 误回退 | 低 | Step 3 明确保留当前版本 |

## 参考文件

- 参考项目：`/tmp/trellis-0.5.17/`（Trellis 0.5.17 全新初始化项目）
- 研究报告：`.trellis/tasks/_research/git-changes-analysis.md`
- 研究报告：`.trellis/tasks/03-19-implement-agents-source/research/trellis-0.5.17-reference-vs-current.md`
- 研究报告：`.trellis/tasks/research/`（8 份核心机制分析）

# PRD: Enhance trellis-research MCP Tools

## Problem

trellis-research agent 作为专职搜索 agent，当前工具集与项目 MCP 路由矩阵存在显著缺口：
- 内部搜索仅有 Glob/Grep/Read（关键词级），缺少语义检索
- 外部搜索仅有 2 个 exa 基础工具，缺全文读取、库文档、GitHub 仓库研究等关键能力
- spec/index.md 中无工具能力描述，后续维护者无法理解本次增强的范围和意图

## Scope

### 修改文件（6 个）

1. `.claude/agents/trellis-research.md` — frontmatter tools 列表 + body 搜索指引
2. `.qoder/agents/trellis-research.md` — 同 Claude
3. `.opencode/agents/trellis-research.md` — permission block + body 搜索指引
4. `.codex/agents/trellis-research.toml` — 不改（沙箱隐式继承，无 MCP 工具声明能力）
5. `.kiro/agents/trellis-research.json` — 不改（通用工具名，沙箱模型不同）
6. `.trellis/spec/agents/index.md` — 新增 Tool Capability Enhancement 段落

### 不改的文件

- `agents/README.md` — 源资产层未建立，留给 03-19-implement-agents-source 任务
- Codex / Kiro 部署文件 — 平台不支持 MCP 工具声明，保持现状

## Tool Enhancement Plan

### P0（关键缺口）

| Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|------|---------|--------|-------|----------|-------|------|
| `mcp__ace__search_context` | 内部语义检索 | + | + | + | - | - |
| `mcp__exa__web_fetch_exa` | 搜索后全文读取 | + | + | + | - | - |

### P1（显著缺口）

| Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|------|---------|--------|-------|----------|-------|------|
| `mcp__Context7__resolve-library-id` | 库文档查询（resolve） | + | + | + | - | - |
| `mcp__Context7__query-docs` | 库文档查询（query） | + | + | + | - | - |

### P2（补充能力）

| Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|------|---------|--------|-------|----------|-------|------|
| `mcp__deepwiki__read_wiki_structure` | GitHub 仓库文档结构 | + | + | + | - | - |
| `mcp__deepwiki__read_wiki_contents` | GitHub 仓库文档内容 | + | + | + | - | - |
| `mcp__deepwiki__ask_question` | GitHub 仓库问答 | + | + | + | - | - |

### P3（高级扩展）

| Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|------|---------|--------|-------|----------|-------|------|
| `mcp__exa__web_search_advanced_exa` | 高级搜索（日期/领域/深度推理） | + | + | + | - | - |
| `mcp__grok-search__web_search` | 补充搜索源 | + | + | + | - | - |
| `mcp__grok-search__web_fetch` | 补充网页读取 | + | + | + | - | - |

## Body Changes (Shared across Claude/Qoder/OpenCode)

### Core Responsibilities — update line 1

Before:
```
1. **Internal Search** — locate files/components, understand code logic, discover patterns (Glob, Grep, Read)
```

After:
```
1. **Internal Search** — locate files/components, understand code logic, discover patterns (ace.search_context → Glob/Grep/Read)
```

### Core Responsibilities — update line 2

Before:
```
2. **External Search** — library docs, API references, best practices (web search)
```

After:
```
2. **External Search** — library docs (Context7), GitHub repos (deepwiki), web search (exa/grok), full-page reading (web_fetch)
```

### Workflow Step 3 — replace

Before:
```
Run independent searches in parallel (Glob + Grep + web) for efficiency.
```

After:
```
Choose tools by search type:

| Search Type | Primary | Fallback |
|-------------|---------|----------|
| Internal code | ace.search_context | Glob + Grep + Read |
| Library docs | Context7 (resolve → query) | exa.code_context → exa.web_search |
| GitHub repos | deepwiki (structure → contents / ask) | exa.web_search |
| General web | exa.web_search → exa.web_fetch | grok.web_search → grok.web_fetch |
| Advanced web | exa.web_search_advanced | grok.web_search |

Run independent searches in parallel where tools don't share state.
```

### Codex / Kiro — no change

These platforms use sandbox / generic tool models that don't support named MCP tool declarations.
When the main agent dispatches trellis-research on these platforms and needs an MCP-only
search, it should coordinate externally rather than relying on the sub-agent to call those tools.

## Spec Change (.trellis/spec/agents/index.md)

Insert after "### Context-Adapter Audit (2026-05-06)" section, before "### Notes for Source Layer Task":

```markdown
### Tool Capability Enhancement (2026-05-06)

trellis-research originally deployed with basic internal search (Glob/Grep/Read) + 2 exa tools.
Enhanced on 2026-05-06 to cover the project MCP routing matrix's primary search scenarios.

**Enhancement type**: `capability-enhancement` — extends available search channels
without changing the core role, boundaries, or workflow structure.

#### Enhanced Tool Matrix

| Priority | Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|----------|------|---------|--------|-------|----------|-------|------|
| P0 | mcp__ace__search_context | Internal semantic search | ✓ | ✓ | ✓ | ✗ | ✗ |
| P0 | mcp__exa__web_fetch_exa | Full-page read after search | ✓ | ✓ | ✓ | ✗ | ✗¹ |
| P1 | mcp__Context7__resolve-library-id | Library docs (resolve) | ✓ | ✓ | ✓ | ✗ | ✗ |
| P1 | mcp__Context7__query-docs | Library docs (query) | ✓ | ✓ | ✓ | ✗ | ✗ |
| P2 | mcp__deepwiki__* (3 tools) | GitHub repo research | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__exa__web_search_advanced_exa | Advanced search | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__grok-search__web_search | Supplementary search | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__grok-search__web_fetch | Supplementary fetch | ✓ | ✓ | ✓ | ✗ | ✗ |

¹ Kiro uses generic `web_fetch` which is functionally equivalent to `mcp__exa__web_fetch_exa`
but is not an MCP-specific tool declaration.

**Cross-platform notes:**
- Claude / Qoder / OpenCode: full enhancement with all MCP tools
- Codex: sandbox model doesn't support named MCP tool declarations; main agent coordinates external searches
- Kiro: generic tool names (`web_search`/`web_fetch`) cover basic web capability; no MCP-specific tools
```

## Acceptance Criteria

- [ ] Claude/Qoder/OpenCode 三个部署的 frontmatter/tools/permission 包含全部 P0-P3 工具
- [ ] Claude/Qoder/OpenCode body 中 Core Responsibilities 和 Workflow Step 3 按上述方案更新
- [ ] Codex/Kiro 部署文件不做任何修改
- [ ] spec/index.md 新增 Tool Capability Enhancement 段落，漂移分类中新增 `capability-enhancement` 类型
- [ ] 各平台 description 不变（不是本次改动范围）

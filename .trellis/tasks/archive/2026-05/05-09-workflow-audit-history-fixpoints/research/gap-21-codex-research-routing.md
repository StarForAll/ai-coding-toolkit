# Research: Gap #21 Codex 版 trellis-research 缺搜索路由表

- **Query**: .codex/agents/trellis-research.toml 是否包含搜索路由表（ace/Context7/deepwiki/grok/exa 优先级和 fallback 链）
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.codex/agents/trellis-research.toml` | 安装后的 Codex research agent |
| `/ops/projects/personal/ai-coding-toolkit/.codex/agents/trellis-research.toml` | 源码 Codex research agent |
| `/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md` | 安装后的 Claude research agent |
| `/tmp/trellis-0.5.9-2/.opencode/agents/trellis-research.md` | 安装后的 OpenCode research agent |

### 安装后 Codex 版 trellis-research.toml 搜索路由分析

安装后的 `.codex/agents/trellis-research.toml` 的 `developer_instructions` 部分 (line 29-35) 包含：

```
4. Choose tools by search type:
   - Internal code: `ace.search_context` → `Glob/Grep/Read`
   - Library docs: `Context7` → `exa`
   - GitHub repos: `deepwiki` → `exa`
   - Real-time / latest info: `grok-search` → `exa`
   - General web (non-time-sensitive): `exa` → `grok-search`
   - Advanced / deep research: `exa.web_search_advanced` → `grok-search`
```

**这已经是一个搜索路由表**，包含：
- 6 种搜索场景
- 每种场景的 Primary 和 Fallback 工具
- 与 Claude 版的搜索路由表口径一致

### 三版对比

| 维度 | Codex (toml) | Claude (md) | OpenCode (md) |
|---|---|---|---|
| 搜索路由表 | ✅ 有 (6 种场景) | ✅ 有 (6 种场景 + 表格) | ✅ 有 (6 种场景 + 表格) |
| 路由详细程度 | 文本列表（简洁） | Markdown 表格（含 Primary/Fallback 列） | Markdown 表格（含 Primary/Fallback 列） |
| 总体结构 | 一致 | 一致 | 一致 |
| MCP 工具列表 | 不在 toml 中（依赖 Codex sandbox 配置） | frontmatter 中显式列出 | frontmatter 中显式列出 |

### 源码对比

安装后的 Codex toml 与源码 `.codex/agents/trellis-research.toml` **完全一致**。

### Codex 版与 Claude 版路由差异

Claude 版和 OpenCode 版使用 Markdown 表格格式（含 Primary/Fallback 列标题），Codex 版使用缩进文本列表格式。**内容口径完全一致**，只是格式不同（Codex 的 `developer_instructions` 使用纯文本/Markdown 嵌入，格式选择合理）。

## 判定: ✅ 已修复

### 修复证据

1. Codex 版 trellis-research.toml 的 developer_instructions 中已包含 6 种搜索场景的路由指引
2. 路由表覆盖了 ace / Context7 / deepwiki / grok-search / exa，包含优先级和 fallback 链
3. 三版（Codex / Claude / OpenCode）的搜索路由口径一致

### 残留缺口

- Codex 版使用文本列表格式而非表格格式，信息密度略低，但功能等效
- Codex 版没有 Claude 版中 "Run independent searches in parallel where tools don't share state" 的显式并行提示，不过这是 Codex 执行模型的约束，不影响路由完整性

## Caveats / Not Found

- 无新增发现

# Research: trellis-0-5-12-upgrade-residue

- **Query**: 当前仓库 Trellis 0.5.12 升级残留中，哪些 live 改动应保留，哪些 `.new` 应拒收，哪些行为升级未真正接线
- **Scope**: internal
- **Date**: 2026-05-10

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/workflow.md` | 当前项目真实生效的 Phase Index 与 workflow-state 合同 |
| `.claude/agents/trellis-research.md` | Claude live research agent，当前被错误简化 |
| `.opencode/agents/trellis-research.md` | OpenCode live research agent，当前被错误简化 |
| `.qoder/agents/trellis-research.md` | Qoder live research agent，当前被错误简化 |
| `.codex/agents/trellis-research.toml` | Codex live research agent，保留了增强路由和 dispatch prompt fallback |
| `.trellis/scripts/common/config.py` | `session_auto_commit` 解析函数已新增 |
| `.trellis/scripts/add_session.py` | 仍仅使用 `--no-commit`，未读取 `session_auto_commit` |
| `.trellis/scripts/common/task_store.py` | archive auto-commit 仍仅使用 `--no-commit`，未读取 `session_auto_commit` |
| `.agents/skills/trellis-meta/references/customize-local/change-workflow.md` | 当前 live 出现错误的 `Phase 3.1` 漂移 |
| `.agents/skills/trellis-meta/references/customize-local/change-spec-structure.md` | 当前 live 出现错误的 `Phase 3.3` 漂移 |
| `.agents/skills/trellis-meta/references/local-architecture/spec-system.md` | 当前 live 出现错误的 `Phase 3.3` 漂移 |
| `.trellis/.template-hashes.json` | 已提前记录未最终裁决的 live 文件哈希 |

### Code Patterns

- 当前项目实际 Phase 编号以 `.trellis/workflow.md` 为准，关键编号为 `1.1 / 1.3 / 1.4 / 2.1 / 2.2 / 2.3 / 3.4 / 3.5`。
- `trellis-research` 的增强版合同要求：
  - internal code 优先 `ace.search_context`
  - library docs 优先 `Context7`
  - GitHub repo 优先 `deepwiki`
  - latest/realtime 优先 `grok-search`
  - 通用 web 优先 `exa`
- Codex 当前 live 合同还额外要求：`Active task: <path>` dispatch prompt fallback + inline/non-inline carrier 注释。
- `session_auto_commit` 当前只在 `common/config.py` 中可读，但实际调用链没有接入，属于半升级。
- `.new` 文件在本仓库应视为候选模板差异，而不是自动采纳的真相源。

### Related Specs

- `.trellis/spec/scripts/python-conventions.md` — Python 运行脚本改动约束
- `.trellis/spec/docs/index.md` — 文档/运行面传播边界
- `.trellis/spec/guides/cross-layer-thinking-guide.md` — 多层联动改动需同步验证

## Caveats / Not Found

- 未发现任何本轮 `.new` 候选值得直接整体采用。
- `.template-hashes.json` 应在最终 live 内容稳定后再刷新，不能提前作为正确性依据。

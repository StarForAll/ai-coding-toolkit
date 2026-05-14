# Research: runtime upgrade decision

- Query: 将当前仓库实际生效的 Trellis runtime 与 `/tmp/trellis-0.5.14` 基线样本对比，判断 `0.5.15` 升级残留和 `.new` 文件的正确处理方案。
- Scope: mixed
- Date: 2026-05-14

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/workflow.md` | 当前 repo 的 live Phase / dispatch 合同 |
| `.trellis/config.yaml` | Codex inline 默认约束 |
| `.codex/config.toml` | repo-local Codex inline 规则和 hook 说明 |
| `.codex/hooks.json.new` | 仅将 hook 命令改为 `python3 -X utf8` |
| `.trellis/workflow.md.new` | 引用了当前 repo 与 baseline 都不存在的路径 |
| `.claude/.codex/.opencode/.qoder/.kiro trellis-research` | 当前 research carrier 合同 |

### Code Patterns

- 当前 live workflow 要求所有 Trellis sub-agent dispatch prompt 第一行使用 `Active task: <task path>`，见 `.trellis/workflow.md:197-203`。
- 当前 repo 的 Codex inline 规则要求 main session 不手动使用 subagent，见 `.trellis/config.yaml:82-90` 与 `.codex/config.toml:15-34`。
- 当前 `trellis-research` carrier 被弱化后，丢失 richer MCP routing 和 `Active task` fallback；这与当前 repo live 合同不一致。
- `.trellis/scripts/common/safe_commit.py` 当前版本保留了 narrow staging、tracked-path 判断、`include_removals=True`；`.new` 会把这些回退。

### External References

- `/tmp/trellis-0.5.14/.codex/config.toml` — fresh-ish `0.5.14` baseline sample
- `/tmp/trellis-0.5.14/.trellis/workflow.md` — baseline workflow sample

### Related Specs

- `.trellis/spec/platforms/codex-workflow-behavior.md` — Codex inline contract
- `.trellis/spec/scripts/index.md` — runtime script editing conventions
- `.trellis/spec/docs/index.md` — repo-local docs boundary

## Caveats / Not Found

- `/tmp/trellis-0.5.14` 不是当前 CLI 版本 fresh init，只能作为 `0.5.14` 对照样本。
- `.trellis/workflow.md.new` 引用的 `.trellis/spec/cli/backend/workflow-state-contract.md` 与 `.trellis/scripts/inject-workflow-state.py` 在当前 repo 和样本里都不存在。

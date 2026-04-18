# Reviewer Commands Round 3

## Task Summary

Current task continues the workflow compatibility upgrade for `docs/workflows/新项目开发工作流`.

Round 1 and Round 2 have already:

- aligned managed-agent wording and boundaries
- aligned `research -> implement -> check-agent` as the implementation internal chain
- aligned Codex `check.toml` to workspace-write self-fix semantics
- added upgrade-analysis / upgrade-compat / uninstall / sandbox-boundary regression coverage
- fixed uninstall symmetry for newly created managed agents

Round 3 should only look for still-uncovered, high-value issues after those fixes.

## Review Focus

- final post-fix implementation-chain boundary consistency
- final post-fix managed-agent parity across Claude / OpenCode / Codex
- final install / analyze-upgrade / upgrade-compat / uninstall / test symmetry
- final documentation propagation completeness

## Target Path

- `docs/workflows/新项目开发工作流`

## Review Round

- `round`: `3`
- `task-dir`: `tmp/multi-cli-review/04-18-trellis-native-workflow-compat`

## Reviewer Commands

### Claude

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改，在 round-1 与 round-2 修复后是否仍存在未覆盖的高价值问题。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中完全一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成真正对称闭环，尤其是新建无备份 agent 的 uninstall 行为；3) research 的 `exa + Context7` 硬规则、Codex `check.toml` 的 workspace-write 自修复语义，是否仍与 README、边界矩阵、测试断言完全一致；4) 只报告当前仍成立的新问题，不重复 round-1 与 round-2 已关闭项。读取 `summary-round-1.md`、`summary-round-2.md`、`action.md` 作为上下文。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id claude --round 3 --review-focus "final post-fix implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

### OpenCode

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改，在 round-1 与 round-2 修复后是否仍存在未覆盖的高价值问题。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中完全一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成真正对称闭环，尤其是新建无备份 agent 的 uninstall 行为；3) research 的 `exa + Context7` 硬规则、Codex `check.toml` 的 workspace-write 自修复语义，是否仍与 README、边界矩阵、测试断言完全一致；4) 只报告当前仍成立的新问题，不重复 round-1 与 round-2 已关闭项。读取 `summary-round-1.md`、`summary-round-2.md`、`action.md` 作为上下文。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id opencode --round 3 --review-focus "final post-fix implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-3/claude.md`
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-3/opencode.md`

## Aggregator Command

Current CLI after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --round 3
```

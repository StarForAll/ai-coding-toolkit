# Reviewer Commands Round 2

## Task Summary

Current task continues the workflow compatibility upgrade for `docs/workflows/新项目开发工作流`.

Round 1 has already:

- aligned Codex managed-agent wording to "partial installer management"
- added Claude / OpenCode managed-agent upgrade-analysis tests
- added Codex managed-agent uninstall recovery coverage
- added Codex research / implement sandbox-boundary assertions

Round 2 should only look for issues that still remain after those fixes.

## Review Focus

- post-fix implementation-stage internal-chain boundary
- post-fix managed-agent parity across Claude / OpenCode / Codex
- post-fix install / analyze-upgrade / upgrade-compat / uninstall / test symmetry
- propagation completeness across workflow docs

## Target Path

- `docs/workflows/新项目开发工作流`

## Review Round

- `round`: `2`
- `task-dir`: `tmp/multi-cli-review/04-18-trellis-native-workflow-compat`

## Reviewer Commands

### Claude

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中保持一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成完整闭环，且不会把 hooks/config 的 verify-only 边界误写成托管资产；3) Codex `check.toml` 的 workspace-write 自修复语义，以及 research 的 `exa + Context7` 硬规则，是否仍与当前 CLI 适配文档、官方边界口径、测试断言一致；4) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。读取 `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/summary-round-1.md` 与 `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/action.md` 作为 round-1 决策上下文。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id claude --round 2 --review-focus "post-fix implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

### OpenCode

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改，在 round-1 修复后是否仍存在未覆盖的高价值问题。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中保持一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成完整闭环，且不会把 hooks/config 的 verify-only 边界误写成托管资产；3) Codex `check.toml` 的 workspace-write 自修复语义，以及 research 的 `exa + Context7` 硬规则，是否仍与当前 CLI 适配文档、官方边界口径、测试断言一致；4) 只报告当前仍成立的新问题，不重复 round-1 已关闭项。读取 `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/summary-round-1.md` 与 `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/action.md` 作为 round-1 决策上下文。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id opencode --round 2 --review-focus "post-fix implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-2/claude.md`
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-2/opencode.md`

## Aggregator Command

Current CLI after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --round 2
```

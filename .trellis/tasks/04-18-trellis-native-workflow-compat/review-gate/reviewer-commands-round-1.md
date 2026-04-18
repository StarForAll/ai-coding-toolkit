# Reviewer Commands Round 1

## Task Summary

Current task updates `docs/workflows/新项目开发工作流` to:

- treat `plan / dispatch agent` as not adopted by the workflow
- define `research -> implement -> check-agent` as the implementation-stage internal chain
- distinguish internal `check-agent` from formal `/trellis:check`
- bring `.codex/agents/{research,implement,check}.toml` into workflow compatibility governance
- align Codex `check.toml` to a workspace-write self-fixing check-agent
- require research-agent external search to prefer `exa`, and require `Context7` first for library/framework/SDK docs

## Review Focus

- implementation-stage internal chain boundary
- managed agents parity across Claude / OpenCode / Codex
- install / analyze-upgrade / upgrade-compat / uninstall symmetry
- documentation and test propagation completeness

## Target Path

- `docs/workflows/新项目开发工作流`

## Review Round

- `round`: `1`
- `task-dir`: `tmp/multi-cli-review/04-18-trellis-native-workflow-compat`

## Reviewer Commands

### Claude

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中保持一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成完整闭环，且不会把 hooks/config 的 verify-only 边界误写成托管资产；3) Codex `check.toml` 改为 workspace-write、自修复 check-agent，以及 research 的 `exa + Context7` 硬规则，是否仍与当前 CLI 适配文档、官方边界口径、测试断言一致；4) 只报告当前仍成立的高价值问题，不做代码修改。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id claude --round 1 --review-focus "implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

### OpenCode

```text
/multi-cli-review "复核当前针对“新项目开发工作流 Trellis 原生能力兼容升级”的修改。重点检查：1) implementation 内部链 `research -> implement -> check-agent` 与正式 `/trellis:check` 的阶段边界，是否在 start/check/命令映射/总纲/walkthrough 中保持一致；2) `.codex/agents/*.toml` 纳管后，install/uninstall/analyze-upgrade/upgrade-compat/test fixtures 是否形成完整闭环，且不会把 hooks/config 的 verify-only 边界误写成托管资产；3) Codex `check.toml` 改为 workspace-write、自修复 check-agent，以及 research 的 `exa + Context7` 硬规则，是否仍与当前 CLI 适配文档、官方边界口径、测试断言一致；4) 只报告当前仍成立的高价值问题，不做代码修改。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --reviewer-id opencode --round 1 --review-focus "implementation 内部链边界、三端 managed agents 对齐、安装/升级/卸载/测试闭环、文档传播一致性"
```

## Output Contract

- reviewer output path:
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-1/claude.md`
  - `tmp/multi-cli-review/04-18-trellis-native-workflow-compat/review-round-1/opencode.md`

## Aggregator Command

Current CLI after both reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-18-trellis-native-workflow-compat --round 1
```

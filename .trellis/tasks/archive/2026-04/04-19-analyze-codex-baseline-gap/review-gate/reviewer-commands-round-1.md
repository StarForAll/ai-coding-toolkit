# Reviewer Commands Round 1

## Task Summary

Current task: `04-19-analyze-codex-baseline-gap`

This round reviews the Codex baseline-skill boundary fix inside `docs/workflows/新项目开发工作流/`.

Expected behavior after the fix:

- Distributed workflow skills still sync to both `.agents/skills/` and `.codex/skills/`
- Codex baseline patches for `start` and `finish-work` only apply to the active skills directory
- `parallel` remains a Codex-local skill handled in `.codex/skills/`
- install / upgrade / uninstall / tests / docs stay aligned

## Review Focus

`Codex 活动 skills 目录判定、baseline patch 仅作用于 .agents/skills 的正确性，以及 install/upgrade/uninstall/test/doc 五层同步`

## Target Paths

- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`

## Review Directory

- `task-dir`: `tmp/multi-cli-review/04-19-analyze-codex-baseline-gap`
- `round`: `1`
- reviewer reports must be written into:
  - `tmp/multi-cli-review/04-19-analyze-codex-baseline-gap/review-round-1/<reviewer-id>.md`

## Reviewer Commands

### Reviewer 1

```text
/multi-cli-review "审查 docs/workflows/新项目开发工作流 中本轮 Codex skills 目录边界修复：确认分发型 workflow skills 仍同步到 .agents/skills 与 .codex/skills，而 start/finish-work baseline patch 只作用于活动 skills 目录；同时检查 install/upgrade/uninstall/test/doc 是否一致，是否存在遗漏恢复路径、错误回滚、目录漂移或文档-实现不一致。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-19-analyze-codex-baseline-gap --reviewer-id claude-code --round 1 --review-focus "Codex 活动 skills 目录判定、baseline patch 仅作用于 .agents/skills 的正确性，以及 install/upgrade/uninstall/test/doc 五层同步"
```

### Reviewer 2

```text
/multi-cli-review "审查 docs/workflows/新项目开发工作流 中本轮 Codex skills 目录边界修复：确认分发型 workflow skills 仍同步到 .agents/skills 与 .codex/skills，而 start/finish-work baseline patch 只作用于活动 skills 目录；同时检查 install/upgrade/uninstall/test/doc 是否一致，是否存在遗漏恢复路径、错误回滚、目录漂移或文档-实现不一致。" docs/workflows/新项目开发工作流 --task-dir tmp/multi-cli-review/04-19-analyze-codex-baseline-gap --reviewer-id opencode --round 1 --review-focus "Codex 活动 skills 目录判定、baseline patch 仅作用于 .agents/skills 的正确性，以及 install/upgrade/uninstall/test/doc 五层同步"
```

## Current CLI Aggregation Command

Run this in the current CLI after both reviewer reports are ready:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-19-analyze-codex-baseline-gap --round 1
```

## Notes

- The two reviewer commands intentionally keep the same review description and the same `--review-focus`; only `--reviewer-id` differs.
- Reviewer CLIs must not create the review directory; it has already been prepared by the coordinator.
- Reviewer CLIs must only run `multi-cli-review` and must not modify code directly.

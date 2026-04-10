# Round 2 Reviewer Commands

## Task Summary

- Task: `04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver`
- Round: `2`
- Goal: 在第 1 轮补强后，复核当前迁移蓝图是否仍有遗漏的高价值可执行缺口，特别是验证第 1 轮“已覆盖/已忽略”的判断是否稳固
- Primary target:
  - `.trellis/tasks/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/migration-blueprint.md`
- Required context:
  - `tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/summary-round-1.md`
  - `tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/action.md`
  - `docs/workflows/新项目开发工作流/commands/check.md`
  - `docs/workflows/新项目开发工作流/commands/review-gate.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`

## Review Focus

- 第 1 轮新增的“旧规则去重”步骤是否足以关闭该类风险
- 第 1 轮被标记为“已覆盖/可忽略”的问题，当前蓝图是否真的已明确到可执行程度
- 是否仍存在会影响后续实施的高价值遗漏项
- 不重新报告第 1 轮已被证伪的事实性误报，除非能给出新的证据链

## Reviewer Assignment

| Reviewer | Focus |
|----------|-------|
| `claude` | 语义迁移边界、source-of-truth 边界、安装记录与验证/回滚契约 |
| `opencode` | 路由迁移完整性、阶段链一致性、脚本路径适配与执行顺序 |

## Standard Commands

### Claude

```text
/multi-cli-review "复核 migration-blueprint.md 在 round-1 修订后是否仍存在未覆盖的高价值可执行缺口。重点检查：1) 第1轮新增的旧 self-review / 旧 check 去重步骤是否足以关闭重复迁移风险；2) 第1轮被标记为已覆盖的 source-of-truth、workflow-installed.json、review-gate 来源、验证/回滚契约是否真的已经明确到可实施；3) 只报告仍然成立的新问题，不重复已证伪误报。" .trellis/tasks/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/migration-blueprint.md --task-dir tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver --reviewer-id claude --round 2 --review-focus "语义迁移边界、source-of-truth 边界、安装记录与验证/回滚契约；同时读取 summary-round-1.md 与 action.md 作为第1轮决策上下文"
```

### OpenCode

```text
/multi-cli-review "复核 migration-blueprint.md 在 round-1 修订后是否仍存在未覆盖的高价值可执行缺口。重点检查：1) AGENTS/start.md 路由迁移与阶段链是否已经被蓝图完整覆盖；2) check-quality.py 路径模式适配、review-gate 新增、实施顺序是否仍有遗漏；3) 只报告当前仍成立的问题，不重复第1轮已关闭项。" .trellis/tasks/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/migration-blueprint.md --task-dir tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver --reviewer-id opencode --round 2 --review-focus "路由迁移完整性、阶段链一致性、脚本路径适配与实施顺序；同时读取 summary-round-1.md 与 action.md 作为第1轮决策上下文"
```

## Output Contract

- Reports must be written to:
  - `tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/review-round-2/claude.md`
  - `tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver/review-round-2/opencode.md`
- Reviewer only writes reports
- Reviewer must not modify files
- Reviewer must not create directories

## Aggregation Command

After both reports are ready, run:

```text
/multi-cli-review-action --task-dir tmp/multi-cli-review/04-09-workflow-compat-plan-browser-bookmark-cleaner-rchiver --round 2
```

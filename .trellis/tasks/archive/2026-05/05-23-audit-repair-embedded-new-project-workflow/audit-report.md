# Audit Report

## Audit Boundary

- Workflow Root: `docs/workflows/新项目开发工作流/`
- Target Project Sample: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Current Mode: `task-based static (analysis only before user approval)`

## Collected Evidence

- `source repo`: `commands/workflow_assets.py` declares `COMPATIBLE_TRELLIS_VERSION = "0.5.17"` and installs only `EXECUTION_CARDS = ["需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"]`.
- `runtime command output`: `trellis -v` returned `0.5.17`.
- `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` records only the two execution cards above; `/tmp/trellis-0.5.17-2/.trellis/workflow-docs/` contains exactly those two files.
- `generated target project`: `/tmp/trellis-0.5.17-2/.trellis/workflow.md` stage transition quick reference omits `project-audit -> delivery`, while installed `workflow-state.py` allows that canonical transition.
- `source repo`: `commands/shell/workflow-state.py` still contains `EXIT_READY_STATUSES = {"awaiting_user_confirmation", "completed"}` and an error string referencing `implementation / test-first`.
- `source repo`: `阶段状态机与强门禁协议.md` still documents `status` as including `completed`.
- `source repo`: `工作流全局流转说明（通俗版）.md` still contains legacy `start` and `test-first` wording inconsistent with the strong-gate source of truth.

## Preliminary Classification

### Confirmed Issues

- Pending detailed write-up after final line-level verification.

### False Alarms / Non-Defects

- `workflow-docs` only deploying two execution cards is the current install contract, not a missing-doc defect.

### Evidence Gaps

- Need final line-level sweep to determine whether `completed` is merely dead terminology or whether any target-project-visible behavior still depends on it.

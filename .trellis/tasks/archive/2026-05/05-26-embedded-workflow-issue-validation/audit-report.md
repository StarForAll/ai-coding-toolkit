# Audit Report

## Audit Boundary

- Workflow Root: `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Runtime Target Project: `/tmp/trellis-0.5.17-2`
- Current Mode: `task-based static+runtime evidence collection`

## Confirmed Issues

### 1. Leaf / task-owner init guidance can produce a dead-on-arrival transition

- Status: `confirmed`
- Source repo:
- `commands/workflow-patch-projectization.md` documents:
  - `plan -> implementation`: init leaf with `--stage plan`, then direct `set --stage implementation`
  - `project-audit -> check`: after switching back from formal `PROJECT-AUDIT` carrier to the task-level owner, it still tells the operator to init that owner with `--stage project-audit`, then direct `set --stage check`
- `commands/shell/workflow-state.py` rejects stage switch when current `status != awaiting_user_confirmation`
- `commands/project-audit.md` and `阶段状态机与强门禁协议.md` explicitly define:
  - `check` is task-level
  - `project-audit` is project-level
  - leaving formal `PROJECT-AUDIT` for `check` / `review-gate` must switch back to `task_level_check_task`
- Generated target project:
- `/tmp/trellis-0.5.17-2/.trellis/workflow.md` contains the same transition guidance
- Runtime command output:
  - `workflow-state.py init <leaf> --stage plan` then direct `set --stage implementation ... --transition-from plan` fails with:
    - `进入 'implementation' 前 status 必须为 awaiting_user_confirmation`
  - `workflow-state.py init <task-owner> --stage project-audit` then direct `set --stage check ... --transition-from project-audit` fails with the same gate
- Refined interpretation:
  - the defect is **not** that project-level `project-audit` and task-level `check` are separated
  - that separation is correct and already enforced by current validators/tests
  - the real defect is that the documented manual handoff sequence for the task-level owner is illegal under the current state machine, and it also pollutes the task-level owner with a project-level stage label

### 2. Codex start quick reference still routes unclear work to legacy `trellis-brainstorm`

- Status: `confirmed`
- Source repo:
  - installed patch source currently leaves `trellis-start` quick reference stale
- Generated target project:
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md`
    - `| New feature / unclear requirements | trellis-brainstorm |`
  - installed workflow also ships `.agents/skills/brainstorm/SKILL.md` as the formal stage entry
  - installed `trellis-brainstorm` is the legacy generic brainstorm skill that still creates task first and uses legacy sub-agent rules

### 3. `plan-validate.py` misses the “declared PROJECT-AUDIT but no structured task row” case

- Status: `confirmed`
- Source repo:
  - `commands/shell/plan-validate.py` only enforces `project_audit_count <= 1`
  - dependency / graph checks still read textual `PROJECT-AUDIT` references even when the task table row is absent
- Runtime command output:
  - a synthetic `task_plan.md` with `PROJECT-AUDIT` still present in checklist / dependency / graph sections, but removed from `Trellis Task 清单`, returns `0`
  - script prints `project-audit 任务数量合法（0 或 1）` and passes all checks

### 4. Codex main-session-only policy is not structurally hard-disabled

- Status: `confirmed`
- Generated target project:
  - `/tmp/trellis-0.5.17-2/.codex/config.toml` keeps `[features.multi_agent_v2].enabled = true`
  - `/tmp/trellis-0.5.17-2/.codex/hooks.json` only wires `UserPromptSubmit -> inject-workflow-state.py`
  - no spawn / tool-level hard block is installed
  - `AGENTS.md` states agent/subagent path is explicitly forbidden, but that is prompt-layer guidance rather than carrier-level disablement

### 5. `delivery` next-step finish-work entry naming is inconsistent with the installed command surface

- Status: `confirmed`
- Source repo / generated target project:
  - `delivery` docs say the next entry is `/finish-work`
  - installed Claude command carrier is `.claude/commands/trellis/finish-work.md`, whose public entry surface is `/trellis:finish-work`
  - installed AGENTS routing table also advertises `/trellis:finish-work`

### 6. Upgrade / embed integrity checks miss multiple real semantic defects

- Status: `confirmed`
- Runtime command output:
  - `upgrade-compat.py --check --project-root /tmp/trellis-0.5.17-2 --cli claude,opencode,codex` returns full green
  - yet issues 1 / 2 / 3 / 5 above are simultaneously present in the same installed target project
- Interpretation:
  - current integrity layer verifies important patch markers and some semantic fragments
  - but it does not currently enforce these workflow-contract invariants

## False Alarms / Reframed Items

### 7. “缺少状态机与门禁脚本自动化回归测试” is false as written

- Status: `false alarm (reframe needed)`
- Source repo evidence:
  - `commands/shell/test_workflow_state.py`
  - `commands/shell/test_plan_validate.py`
  - `commands/test_workflow_installers.py`
  - other validator test files under `commands/shell/test_*.py`
- Reframed gap:
  - there is substantial automated coverage
  - but the specific regressions above are not fully covered by targeted tests / invariants yet

## Pending Fix Directions

1. Rewrite invalid init-transition guidance into legal two-step re-entry or repair flows.
2. Patch installed `trellis-start` Phase Router quick reference to point Codex at `brainstorm`, not `trellis-brainstorm`.
3. Add `PROJECT-AUDIT` declaration-vs-row consistency checks to `plan-validate.py` plus regression tests.
4. Decide whether Codex hard-disable should be implemented by project config, additional hook gating, or both; verify solution stays within current workflow carrier contract.
5. Normalize `delivery` next-step entry naming to `/trellis:finish-work` on Claude/OpenCode and `trellis-finish-work` on Codex.
6. Extend upgrade / integrity checks and regression tests so the above defects are detectable pre-release.

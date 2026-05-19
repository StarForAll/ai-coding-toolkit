# Workflow State Gates Audit

## Audit Boundary

- Source workflow root: `docs/workflows/新项目开发工作流/`
- Runtime evidence target: `/tmp/trellis-0.5.17-2`
- Fix scope: source workflow assets only

## Version Gate

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`
- Local `trellis -v`
  - `0.5.17`
- Result
  - exact match, version gate passed

## Confirmed Evidence So Far

### 1. `awaiting_user_confirmation` exit-gate coverage is incomplete

- `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
  - `collect_exit_gate_blockers()` only checks `brainstorm/design/plan/check/finish-work/delivery`
- `/tmp/trellis-0.5.17-2/.agents/skills/project-audit/SKILL.md`
  - requires `project-audit.md`, verification matrix, findings, fix plan, results, risks
- `/tmp/trellis-0.5.17-2/.agents/skills/review-gate/SKILL.md`
  - requires `review-gate/review-gate-round-<N>.md`, reviewer command pack, optional `summary-round-<N>.md` and `action.md`
- `/tmp/trellis-0.5.17-2/.agents/skills/record-session/SKILL.md`
  - defines archive + `add_session.py` + metadata cleanup closure

Conclusion:
- current route layer can report `awaiting_confirmation` without proving project-audit / review-gate / record-session evidence exists

### 2. Canonical transition graph is not enforced strongly enough

- `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
  - `validate_state_shape()` only checks whether `allowed_next_stages` contains valid stage names
  - `cmd_set()` only checks whether target is inside current state's `allowed_next_stages`
- `阶段状态机与强门禁协议.md`
  - `allowed_next_stages` is only candidate metadata, not authorization

Conclusion:
- if `allowed_next_stages` drifts, current set logic can still allow non-canonical stage hops

### 3. `check-quality.py` is fail-open when no commands are provided

- `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/check-quality.py`
  - missing command -> `None`
  - main returns non-zero only when any result is `False`

Conclusion:
- no validation commands can still exit 0, contradicting evidence-first gate intent

### 4. `check` and `finish-work` gates are still structure-heavy and content-light

- `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
  - `validate_check_gate()` currently only checks `Changed Scope/变更范围` and `Verification Results/验证结果`
  - `validate_finish_work_gate()` currently checks headers/table presence but not true result semantics
- `/tmp/trellis-0.5.17-2/.agents/skills/check/SKILL.md`
  - minimum content includes applied specs, deviations, uncovered risks, suggested next step, pass/fail/not run evidence

Conclusion:
- `check` gate is definitely weaker than the command/skill contract
- `finish-work` likely also needs stronger semantic checks, but current exact minimal contract still needs refinement

### 5. `repair` preserves semantic fields too trustingly

- `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
  - `cmd_repair()` reuses existing `allowed_next_stages`, `awaiting_user_confirmation`, `last_confirmed_transition`, notes, checkpoints
  - result is only shape-validated, not rebuilt against canonical stage rules

Conclusion:
- dirty state can be repackaged as `repair_ready`

## Candidate Same-Class Issues To Verify

- `workflow-state.py validate` may not enforce downstream stage artifacts consistently with `route`
- `record-session` may need an explicit stage evidence contract if source docs require more than delivery completion
- command docs may still describe stronger guarantees than scripts enforce

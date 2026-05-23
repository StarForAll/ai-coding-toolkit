# Research: 9-Stage State Machine Analysis — Native vs Embedded Trellis

- **Query**: Analyze the "新项目开发工作流" 9-stage state machine design, judging whether it causes unnecessary complexity or damage to the native trellis framework
- **Scope**: Mixed (internal code comparison + external design docs)
- **Date**: 2026-05-23

## Findings

### 1. Native Trellis Stages and Transition Rules

| Aspect | Detail |
|---|---|
| Phase model | 3-phase: Plan (1.0-1.5) → Execute (2.1-2.3) → Finish (3.1-3.5) |
| State field | `task.json.status`: `planning` / `in_progress` / `completed` |
| Status flip | `task.py start` sets `task.json.status = "in_progress"` |
| Breadcrumb blocks | 4 blocks: `[workflow-state:no_task]`, `[workflow-state:planning]`, `[workflow-state:in_progress]`, `[workflow-state:completed]` |
| Routing | `get_context.py --mode phase --step X.Y` returns step guidance |
| Session resume | `session-start.py` 4 cases: no-task → brainstorm, has-task → inject, completed → finish-work, no-PRD → create |
| Pending filter | `task_queue.list_pending_tasks()` filters by `status == "planning"` |

### 2. Embedded 9-Stage Definitions and Transition Rules

| Aspect | Detail |
|---|---|
| Stage chain | `feasibility → brainstorm → design → plan → implementation → project-audit → check → review-gate → delivery` |
| State field | `workflow-state.json.stage` + `workflow-state.json.status` (dual-field) |
| STAGES set | `{feasibility, brainstorm, design, plan, implementation, check, review-gate, project-audit, delivery}` |
| STAGE_STATUSES | `in_progress`, `blocked`, `awaiting_user_confirmation`, `completed` |
| Breadcrumb blocks | 16 blocks: 9 stage blocks + 7 route-action pseudo-state blocks |

**STAGE_TRANSITIONS (15 entries):**

```python
{
    "feasibility": ["brainstorm"],
    "brainstorm": ["design", "plan", "implementation"],         # shortcut paths
    "design": ["plan"],
    "plan": ["implementation"],
    "implementation": ["check", "project-audit"],
    "check": ["implementation", "review-gate", "project-audit", "delivery"],  # 4 targets
    "review-gate": ["implementation", "project-audit", "delivery"],
    "project-audit": ["check", "review-gate", "delivery"],
    "delivery": [],                                              # terminal
}
```

**Route action pseudo-states** (computed, not stored):
- `awaiting_confirmation`, `awaiting_confirmation_with_blockers`, `blocked`
- `context_needed`, `recovery_needed`, `repair_needed`, `embed_invalid`
- `workflow-state.route_failed`

**Gate validators (7):**
- `validate_plan_gate`, `validate_design_exit_gate`, `validate_check_gate`
- `validate_finish_work_gate`, `validate_project_audit_gate`
- `validate_review_gate_gate`, `validate_delivery_gate`

### 3. Stage-by-Stage Comparison

| Native Phase/Step | Embedded Stage | Relationship |
|---|---|---|
| — | feasibility | **NEW** — no native equivalent |
| Plan 1.1 (brainstorm) | brainstorm | **REPLACES** native brainstorm skill invocation; now a formal stage |
| Plan 1.2 (PRD) | design | **NEW** — native has no design stage; PRD creation is an implicit part of Plan |
| Plan 1.3-1.5 (plan steps) | plan | **REPLACES** native Plan sub-steps; collapsed into single stage |
| Execute 2.1-2.3 | implementation | **REPLACES** native Execute phase; single stage |
| — | project-audit | **NEW** — no native equivalent; full-project quality review |
| — | check | **NEW** — no native equivalent; quality check against spec |
| — | review-gate | **NEW** — no native equivalent; multi-CLI supplementary review |
| Finish 3.1-3.5 | delivery | **REPLACES** native Finish phase; narrowed to delivery acceptance |

**Summary**: Of 9 embedded stages, 4 replace/modifiy native phases (brainstorm, plan, implementation, delivery), 4 are entirely new (feasibility, design, project-audit, check, review-gate). Wait — that's 5 new. Actually: feasibility, design, project-audit, check, review-gate = 5 new stages. 4 replace native phases. 0 are purely additive without touching native semantics.

### 4. Core State Machine Logic Modifications (Not Just Additions)

These are **modifications to existing native logic**, not pure additions. Each is a point where the embedded workflow overrides, disables, or replaces a native trellis invariant.

| # | Native Behavior | Embedded Override | File Changed | Severity |
|---|---|---|---|---|
| 1 | `task.py start` flips `task.json.status` from `planning` to `in_progress` | **DISABLED**: prints "Strong-gate mode: skipping legacy task.json status flip" | `scripts/task.py` | **HIGH** — breaks the native invariant that task.py start advances status |
| 2 | `workflow_phase.py` returns step guidance via `get_context.py --mode phase` | **DISABLED** when workflow-state.json exists: prints warning to use `workflow-state.py route` | `scripts/workflow/workflow_phase.py` | **HIGH** — native step guidance mechanism disabled entirely |
| 3 | `task list` displays `task.json.status` (planning/in_progress/completed) | **OVERRIDDEN**: displays `workflow-state.json.stage` instead | `scripts/common/tasks.py` | **MEDIUM** — native status semantics replaced in UI |
| 4 | `inject-workflow-state.py` reads `task.json.status` for breadcrumb | **OVERRIDDEN**: reads `workflow-state.json` stage, prefers it over task.json.status | `.claude/hooks/inject-workflow-state.py` | **HIGH** — native breadcrumb logic replaced at injection point |
| 5 | `session-start.py` has 4 routing cases including completed-task resume | **PARTIAL REPLACEMENT**: Cases 3 (completed) and 4 (no-PRD) REMOVED; replaced with route-first approach via `workflow-state.py route` subprocess | `.claude/hooks/session-start.py` | **HIGH** — native session resumption logic deleted |
| 6 | `task_queue.list_pending_tasks()` filters by `status == "planning"` | **CHANGED** to `list_tasks_by_status(None)`: returns all non-archived tasks | `scripts/common/task_queue.py` | **MEDIUM** — native filtering semantics changed; pending list now includes in-progress tasks |
| 7 | `brainstorm SKILL.md` contains native trellis brainstorm instructions | **PATCHED** with workflow-specific content about strong-gate brainstorm stage | skills overlay | **LOW-MEDIUM** — native skill content modified |

**Verdict**: 4 HIGH-severity modifications disable or replace core native invariants (task.py start status flip, workflow_phase step guidance, breadcrumb injection logic, session resumption logic). These are not additive — they break the native trellis contract at its root mechanisms.

### 5. Over-Complex Transitions

#### 5a. Multi-target branches

| Stage | # Targets | Targets |
|---|---|---|
| check | 4 | implementation, review-gate, project-audit, delivery |
| brainstorm | 3 | design, plan, implementation |
| project-audit | 3 | check, review-gate, delivery |
| review-gate | 3 | implementation, project-audit, delivery |
| implementation | 2 | check, project-audit |

Three stages (check, project-audit, review-gate) share overlapping target sets, creating an ambiguous routing surface where the same destination can be reached via multiple paths with unclear differentiation.

#### 5b. Bidirectional cycles

| Cycle | Path | Implication |
|---|---|---|
| implementation ↔ check | implementation → check → implementation | Bug-fix loop, potentially infinite without external break |
| check ↔ project-audit | check → project-audit → check | Quality review loop, no clear convergence |
| project-audit ↔ review-gate | project-audit → review-gate → project-audit | Audit-gate loop |
| Extended cycle | review-gate → implementation → check → review-gate | 3-stage cycle |

The implementation ↔ check cycle is by design (bug-fix loop), but the check ↔ project-audit and project-audit ↔ review-gate cycles lack a clear convergence mechanism. In native trellis, there are no bidirectional transitions — the model is strictly linear (Plan → Execute → Finish).

#### 5c. Gate validation depth

`validate_stage_transition_gates()` calls up to 5 gate validators in sequence depending on the stage combination. The validation tree:

```
if new_stage == "implementation": validate_plan_gate()
elif current_stage in ("check","review-gate","project-audit") and new_stage == "implementation": (already covered by plan gate for first entry; for re-entry, no separate gate)
elif current_stage == "implementation" and new_stage in ("check","project-audit"): (no explicit exit gate from implementation)
elif new_stage == "review-gate": validate_check_gate()
elif new_stage == "delivery": validate_delivery_gate() or validate_review_gate_gate() or validate_finish_work_gate()
elif current_stage == "design": validate_design_exit_gate()
elif new_stage == "project-audit": validate_project_audit_gate()
```

The branching logic is complex and the relationship between `current_stage + new_stage` pairs and which validator fires is not always obvious — for example, entering delivery from check, review-gate, or project-audit each fires a different validator.

#### 5d. Transition command surface

The Stage Transition Quick Reference has 20 rows, each with Step A (signal readiness) and Step B (after user confirms). That's 40 discrete transition commands for complete coverage. In native trellis, the transition surface is: `task.py start` (planning→in_progress) + `finish-work` (in_progress→completed) = 2 commands.

### 6. Overlapping Responsibilities Between Stages

| Overlap Pair | Reason |
|---|---|
| check vs project-audit | Both perform quality review. project-audit is "full-project quality review" vs check's "quality check against spec". The distinction is scope, not kind. project-audit can go to check AND check can go to project-audit, implying the boundary is unclear. |
| check vs review-gate | review-gate is described as "multi-CLI supplementary review" — appears to be a subset of check's quality assurance role. Both can advance to delivery. |
| project-audit vs review-gate | Both can advance to delivery directly. Both can loop back to implementation. The difference between "audit" and "review-gate" is semantically thin. |
| brainstorm shortcut vs design+plan | brainstorm → implementation shortcut bypasses design and plan entirely, but checkpoints like `architecture_confirmed` and `context7_review_completed` default to false on this path — these fields become dead weight. |

The triple overlap of check / project-audit / review-gate is the most significant concern. These three stages all perform variants of "quality review before delivery" and their routing targets overlap heavily. In practice, the distinction between "check quality against spec", "full-project audit", and "review gate" may be too granular for the workflow to enforce meaningfully.

### 7. Dead Paths and Unreachable States

| Item | Detail |
|---|---|
| `checkpoints.context7_review_completed` | Defined in `build_default_state()`, validated in gate checks, but only meaningful in design stage. When brainstorm → implementation shortcut is taken, this checkpoint is never set and never meaningful, yet it exists in state as dead weight. |
| `current_block` / `completed_blocks` | Validated in all stages, but only design stage actually uses `current_block` for its "Design Stage Special Doc Boundary" protocol. All other stages set `current_block = None`. |
| `STAGE_STATUS = "completed"` | Defined but never assigned in any transition. delivery has empty transition list (`[]`), meaning there is no stage-level transition to a "completed" state — completion is handled by native finish-work outside the state machine. The `completed` status is defined but effectively unreachable within the 9-stage model itself. |
| `brainstorm → implementation` path | Checkpoints default to false, no gate validator enforces them on this path. The shortcut path carries vestigial checkpoint state that is never validated. |
| `recovery_needed` route action | Defined as a route result but never generated by any `workflow-state.py route` branch in the current code. Only `repair_needed` and `awaiting_confirmation` are actually produced. |

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.17-1/.trellis/workflow.md` | Native trellis workflow definition (690 lines) |
| `/tmp/trellis-0.5.17-2/.trellis/workflow.md` | Embedded/patched workflow (532 lines) |
| `/tmp/trellis-0.5.17-2/.trellis/.backup-original/workflow.md` | Backup of original (identical to native) |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` | Core new routing script (~700+ lines) |
| `/tmp/trellis-0.5.17-1/.trellis/scripts/task.py` | Native task.py |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` | Patched task.py (status flip disabled) |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/common/tasks.py` | Patched tasks.py (display override) |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/common/task_queue.py` | Patched task_queue.py (pending filter changed) |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow_phase.py` | Patched workflow_phase.py (step guidance disabled) |
| `/tmp/trellis-0.5.17-1/.claude/hooks/inject-workflow-state.py` | Native injection hook |
| `/tmp/trellis-0.5.17-2/.claude/hooks/inject-workflow-state.py` | Patched injection hook (route data) |
| `/tmp/trellis-0.5.17-1/.claude/hooks/session-start.py` | Native session start |
| `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py` | Patched session start (cases 3/4 removed) |
| `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` | Installation metadata |
| `/ops/.../阶段状态机与强门禁协议.md` | Source design doc for strong-gate |
| `/ops/.../local-architecture/workflow.md` | Source local architecture doc |

### External References

- [阶段状态机与强门禁协议.md](file:///ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md) — Source design doc defining strong-gate principles and transition protocol
- [local-architecture/workflow.md](file:///ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/local-architecture/workflow.md) — Source local architecture doc declaring native routing as non-authoritative

### Related Specs

- `.trellis/spec/scripts/workflow/workflow-state.md` — Spec for the workflow-state.py script
- `.trellis/spec/commands/trellis/check.md` — Spec for the check command
- `.trellis/spec/commands/trellis/review-gate.md` — Spec for the review-gate command

## Caveats / Not Found

- **workflow-state.json runtime examples not available**: No active tasks existed in either temp project, so no actual workflow-state.json files were present. Analysis is based on `build_default_state()` and transition logic, not on runtime state instances.
- **Gate validator implementations partially read**: workflow-state.py exceeded the single-read token limit. Gate validators were read in chunks; some internal details of validation logic may be missing.
- **No runtime testing performed**: The analysis is static (code reading + diff comparison). No attempt was made to run the state machine through actual transitions.
- **brainstorm SKILL.md overlay only partially examined**: The patched skill content was noted as modified but not fully compared line-by-line against the native version.
- **Excluded per instructions**: feasibility stage existence, 9-stage structure existence, status field mapping issues, learning cost criticism — these are not raised as problems even where they might be arguable.

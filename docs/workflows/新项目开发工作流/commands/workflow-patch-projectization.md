## Development Process

<!-- workflow-projectization-patch -->

### Task Development Flow

```text
1. First entry / route current task
   --> python3 ./.trellis/scripts/workflow/workflow-state.py route --project-root <project-root>
   --> For new outsourcing projects: route to feasibility first
   --> For resumable tasks: re-enter the currently confirmed stage only

2. Create or reuse the task directory for the current stage
   --> feasibility / brainstorm may create the task
   --> workflow-state.json is the single source of truth for stage routing

3. Confirm stage gates before leaving the current stage
   --> Signal readiness with stage_status=awaiting_user_confirmation
   --> After explicit user confirmation, switch stage via workflow-state.py set

4. Implement only after execution authorization
   --> plan -> implementation / test-first requires checkpoints.execution_authorized=true
   --> If task.py start runs without session identity, it must also write .trellis/.runtime/degraded-active-task.json for later recovery

5. Verify and commit
   --> Run the project's frozen verification commands when scaffold exists (see spec docs)
   --> Manual feature testing
   --> git add <files>
   --> git commit -m "type(scope): description"

6. Final close-out
   --> finish-work -> delivery -> record-session
   --> archive and add_session happen only at record-session
```

`python3 ./.trellis/scripts/task.py finish` remains available when you intentionally need to clear the current session's active task without archiving a completed task. Do not use it as a substitute for final close-out. In degraded mode, `task.py start` must leave a recoverable fallback file under `.trellis/.runtime/degraded-active-task.json`.

For workflows that split work into a parent coordination task plus child execution tasks:

- freeze the project test-first baseline once in design/spec docs
- select one concrete child task before entering test-first or implementation
- completing the current child task does not automatically authorize the next child task
- after a child task is completed or archived, update the parent coordinator records in the same round so the latest completed frontier, pending frontier, and next selectable child task stay synchronized
- the next child task may start only after the human explicitly names or approves that task in the current round
- create and verify the test gate for that child task only
- complete that child task's test gate before entering its concrete implementation work
- do not pre-write one-shot tests for the entire plan from the parent coordination task
- do not run sibling child tasks in parallel; finish the current child task before switching to the next one

### Code Quality Checklist

**Must pass before commit**:

- [OK] Lint checks pass (project-specific command)
- [OK] Type checks pass (if applicable)
- [OK] Manual feature testing passes

**Project-specific checks**:

- Run the project's frozen verification matrix when the scaffold exists (see `.trellis/spec/` quality guidelines)
- If a change is Trellis-related, sync all linked current-entry hidden directories instead of updating `.trellis/` alone:
  - `.trellis/`
  - `.claude/`
  - `.opencode/`
  - `.agents/skills/`
  - `.codex/`
- Keep each directory in its own format and command style.

---

## Session End

### One-Click Session Recording

The strong-gate workflow no longer archives at `finish-work`. Session recording belongs to the terminal `record-session` stage only:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>

python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

git status --short .trellis/workspace .trellis/tasks
```

Expected metadata status output: empty. This command pair is a `record-session` stage action, not a generic finish-work shortcut.

Notes:

- Close-out follows this order: **finish-work → delivery → record-session**. `archive` and `add_session` are performed at the `record-session` stage, not at `finish-work`.
- `finish-work` only handles commit checklist and close-out evidence; it does NOT archive the task.
- `delivery` handles acceptance, deliverables, and ownership proof.
- `record-session` performs the final `task.py archive` + `add_session.py` to complete the workflow cycle.
- Detailed close-out gates still belong to the installed `/trellis:finish-work` / `trellis-finish-work` and `/trellis:delivery` entries. Directly invoking `/trellis:record-session` remains an old-target compatibility entry; in the strong-gate flow the `record-session` stage is reached only after `delivery`.

### Pre-end Checklist

Close-out runs in three phases:

**Phase A — pre-commit (`/trellis:finish-work`)**

1. Frozen verification matrix executed or truthfully marked `deferred` / `not run`
2. Manual browser / app verification completed where required
3. `finish-work-checklist.md` records the current close-out evidence
4. Spec docs updated if needed

**Phase B — delivery (`/trellis:delivery`)**

1. Deliverables assembled and verified
2. Acceptance confirmed
3. Ownership proof validated (outsourcing profile)

**Phase C — post-delivery (`/trellis:record-session`)**

1. Current completed task archived; if it is a child task, the parent coordinator records are also synchronized to the new completed frontier
2. `add_session.py` completed successfully for the current session record
3. `.trellis/workspace` and `.trellis/tasks` metadata clean

---

## Phase Index

<!-- workflow-projectization-phase-index-patch -->

```
feasibility → brainstorm → design → plan → implementation → test-first → project-audit → check → review-gate → finish-work → delivery → record-session
```

Stage transition gates are enforced by `workflow-state.py set --stage <next>`; use `--force` to bypass for repair scenarios. `finish-work` may only transition to `delivery` — the shortcut `finish-work → record-session` is not allowed, as it would bypass the delivery gate.

### Stage Transition Quick Reference

All transitions follow a two-step protocol: **(A)** signal readiness by setting `stage_status=awaiting_user_confirmation`, then **(B)** after user confirms, switch to the next stage. `workflow-state.py set` must evaluate the fully merged target state in one call, including any checkpoint flags passed on the same command.

| From → To | Step A: Signal readiness | Step B: After user confirms |
|---|---|---|
| no_task → feasibility | N/A (outsourcing first entry) | `workflow-state.py route` → load `/trellis:feasibility` (skill auto-creates task + init feasibility state) |
| feasibility → brainstorm | assessment.md approved | `workflow-state.py set <dir> --stage brainstorm --stage-status in_progress --awaiting-user-confirmation false --allowed-next design,plan,implementation,test-first` |
| brainstorm → design | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage design --stage-status in_progress --awaiting-user-confirmation false --allowed-next plan --transition-from brainstorm` |
| brainstorm → plan | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage plan --stage-status in_progress --awaiting-user-confirmation false --allowed-next implementation,test-first --transition-from brainstorm` |
| brainstorm → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from brainstorm` |
| brainstorm → test-first | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage test-first --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next implementation,check,project-audit --transition-from brainstorm` |
| design → plan | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage plan --stage-status in_progress --awaiting-user-confirmation false --allowed-next implementation,test-first --transition-from design` |
| plan → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from plan` |
| plan → test-first | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage test-first --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next implementation,check,project-audit --transition-from plan` |
| implementation → check | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage check --stage-status in_progress --awaiting-user-confirmation false --allowed-next review-gate,implementation,finish-work` |
| implementation → test-first | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage test-first --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next implementation,check,project-audit --transition-from implementation` |
| implementation → project-audit | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage project-audit --stage-status in_progress --awaiting-user-confirmation false --allowed-next check,review-gate --transition-from implementation` |
| test-first → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from test-first` |
| test-first → check | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage check --stage-status in_progress --awaiting-user-confirmation false --allowed-next review-gate,implementation,finish-work --transition-from test-first` |
| test-first → project-audit | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage project-audit --stage-status in_progress --awaiting-user-confirmation false --allowed-next check,review-gate --transition-from test-first` |
| project-audit → check | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage check --stage-status in_progress --awaiting-user-confirmation false --allowed-next review-gate,implementation,finish-work --transition-from project-audit` |
| project-audit → review-gate | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage review-gate --stage-status in_progress --awaiting-user-confirmation false --allowed-next finish-work,implementation --transition-from project-audit` |
| check → review-gate | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage review-gate --stage-status in_progress --awaiting-user-confirmation false --allowed-next finish-work,implementation` |
| check → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from check` |
| check → finish-work | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage finish-work --stage-status in_progress --awaiting-user-confirmation false --allowed-next delivery` |
| review-gate → finish-work | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage finish-work --stage-status in_progress --awaiting-user-confirmation false --allowed-next delivery` |
| review-gate → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from review-gate` |
| finish-work → delivery | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage delivery --stage-status in_progress --awaiting-user-confirmation false --allowed-next record-session` |
| delivery → record-session | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage record-session --stage-status in_progress --awaiting-user-confirmation false --allowed-next` |

For repair scenarios, append `--force` to bypass validation gates.

---

## Customizing Trellis (for forks)

This section is for developers who want to modify the Trellis workflow itself. All customization is done by editing this file; the scripts are parsers only.

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase sections above. **Critical constraint**: if you change a step's `[required · once]` marker or add a new `[required · once]` step, you MUST also add a matching enforcement line to that phase's `[workflow-state:STATUS]` tag block — otherwise the per-turn breadcrumb omits the reinforcement, and the AI silently skips the step.

Under the strong-gate model, each stage has its own `[workflow-state:STATUS]` tag block. The full list of tag blocks lives in the `## Strong-Gate Breadcrumb Blocks` section below.

### Changing the per-turn prompt text

Directly edit the body of the corresponding `[workflow-state:STATUS]` block. After editing, restart your AI session — no script changes required.

### Adding a custom status

Add a new block:

```
[workflow-state:my-status]
your per-turn prompt text
[/workflow-state:my-status]
```

Constraints:
- STATUS charset: `[A-Za-z0-9_-]+` (underscores and hyphens allowed, e.g. `in-review`, `blocked-by-team`)
- Under the strong-gate model, do **not** treat `task.json.status` as the stage-routing source of truth. Custom breadcrumb tags must be backed by the actual routing layer that emits them (normally `workflow-state.py route` and the hook's breadcrumb-key mapping), otherwise the block is unreachable.
- Lifecycle hooks live in `task.json.hooks.after_*` and bind to one of `after_create / after_start / after_finish / after_archive`

### Adding a lifecycle hook

Add a `hooks` field to your `task.json`:

```json
{
  "hooks": {
    "after_finish": [
      "your-script-or-command-here"
    ]
  }
}
```

Supported events: `after_create / after_start / after_finish / after_archive`. Note that `after_finish` ≠ a status change (it only clears the active-task pointer); use `after_archive` for "task is done" notifications.

### Full contract

For the workflow state machine's runtime contract, the locations of all status writers, pseudo-statuses (`no_task` / `stale_<source_type>`), the hook reachability matrix, and other deep details, see:

- `workflow-state.py --help` — runtime contract + writer table + test invariants

---

## Strong-Gate Breadcrumb Blocks

<!-- workflow-projectization-breadcrumb-patch -->

[workflow-state:feasibility]
Current stage: **feasibility** — first project assessment gate.
Load `/trellis:feasibility` to evaluate project viability, risk, and engagement type.
All new projects must pass feasibility before entering brainstorm.
Run `python3 ./.trellis/scripts/workflow/workflow-state.py route` to check routing.
[/workflow-state:feasibility]

[workflow-state:brainstorm]
Current stage: **brainstorm** — requirement discovery and PRD iteration.
Load `/trellis:brainstorm` skill to iterate on prd.md with the user.
Prerequisite: valid assessment.md from feasibility.
After prd.md and jsonl are curated, set `stage_status = awaiting_user_confirmation` for design/plan transition.
[/workflow-state:brainstorm]

[workflow-state:design]
Current stage: **design** — architecture and design document creation.
Load `/trellis:design` to produce developer-facing PRD (block A), design docs (block B), project docs (block C), and engineering alignment (block D).
Blocks A and B require user confirmation before proceeding.
Run `python3 ./.trellis/scripts/workflow/workflow-state.py validate <task-dir> --project-root <root>` to check exit readiness.
[/workflow-state:design]

[workflow-state:plan]
Current stage: **plan** — task decomposition and scheduling.
Load `/trellis:plan` to decompose work into child tasks with prd.md.
**Hard prohibition**: no implementation code, no scaffolding, no migration scripts.
Set `stage_status = awaiting_user_confirmation` when plan is ready for user approval.
[/workflow-state:plan]

[workflow-state:implementation]
Current stage: **implementation** — code writing phase.
`checkpoints.execution_authorized` must be `true` before entering.
For sub-agent dispatch mode: dispatch `trellis-implement` sub-agent. For inline dispatch mode (`codex.dispatch_mode=inline`): implement directly (load `trellis-before-dev` first).
After implementation, proceed to `check` or `test-first`.
[/workflow-state:implementation]

[workflow-state:test-first]
Current stage: **test-first** — write tests before implementation code.
Load `/trellis:test-first` skill for TDD-driven verification.
`checkpoints.execution_authorized` must be `true`.
[/workflow-state:test-first]

[workflow-state:project-audit]
Current stage: **project-audit** — full-project quality review.
Load `/trellis:project-audit` for cross-cutting quality assessment.
[/workflow-state:project-audit]

[workflow-state:check]
Current stage: **check** — quality check against spec and conventions.
Load `/trellis:check` to validate implementation against specifications.
After passing, proceed to `review-gate`, back to `implementation`, or directly to `finish-work` (when no review-gate is needed).
[/workflow-state:check]

[workflow-state:review-gate]
Current stage: **review-gate** — multi-CLI supplementary review.
Load `/trellis:review-gate` for additional cross-platform quality assurance.
After passing, proceed to `finish-work`.
[/workflow-state:review-gate]

[workflow-state:finish-work]
Current stage: **finish-work** — commit preparation and close-out evidence.
Load `/trellis:finish-work` for commit checklist and close-out evidence collection.
After this stage, proceed to `delivery`. Archive and add_session are performed at the `record-session` stage, NOT here.
[/workflow-state:finish-work]

[workflow-state:delivery]
Current stage: **delivery** — project handover and deployment.
Load `/trellis:delivery` for acceptance, deliverables, and ownership proof.
[/workflow-state:delivery]

[workflow-state:record-session]
Current stage: **record-session** — workflow cycle complete.
This is the strong-gate terminal stage. Run `task.py archive <task-name>` then `add_session.py` to finalize close-out. The workflow cycle is now complete.
The legacy `/trellis:record-session` command remains available as a backwards-compatible entry point for older projects that use the baseline three-phase model; in the strong-gate flow this stage is reached automatically after `delivery`.
[/workflow-state:record-session]

---

## No-Task Entry Point (Strong-Gate)

<!-- workflow-projectization-no-task-patch -->

[workflow-state:no_task]
No active task. **A Direct answer** — pure Q&A / explanation / lookup / chat; no file writes + one-line answer + repo reads ≤ 2 files → AI judges, no override needed.
**A+ Deep analysis** — multi-file read-only audit / architecture review / diagnostic report; file writes limited to analysis docs (research/, temp files); no source code / config / project file modification allowed. Creates a task only if the user explicitly asks to act on findings.
**B Create a task** — any implementation / code change / build / refactor work. For outsourcing profile: entry sequence starts with feasibility gate — (1) `python3 ./.trellis/scripts/workflow/workflow-state.py route` to detect first-entry → (2) if `action=first_entry`, load `/trellis:feasibility` (the feasibility skill will automatically create the task directory and initialize workflow-state.json) → (3) after feasibility passes, `trellis-brainstorm` for prd iteration → (4) `task.py start <task-dir>`. For personal profile: (1) `task.py create "<title>"` → (2) `trellis-brainstorm` — personal profile can skip feasibility but **must** supplement core fields of `assessment.md` during brainstorm (`project_engagement_type=non_outsourcing` + `source_watermark_*` + `ownership_proof_required`), otherwise subsequent stage gate validation will block → (3) `task.py start <task-dir>`. **"It looks small" is NOT grounds for downgrading B to A+ or C**.
`task.py start` in this branch only persists or repairs the active-task pointer for the current session. It does **not** advance `workflow-state.json.stage`; stage changes must still be performed via `workflow-state.py set` after the current stage reaches `awaiting_user_confirmation`.
**C Inline change** (per-turn only, escape hatch for B) — the user's CURRENT message MUST contain one of: "skip trellis" / "no task" / "just do it" / "don't create a task" / "跳过 trellis" / "别走流程" / "小修一下" / "直接改" / "先别建任务" → briefly acknowledge ("ok, skipping trellis flow this turn"), then inline. **Without seeing one of these phrases you must NOT inline on your own**; do not invent an override the user never said.
[/workflow-state:no_task]

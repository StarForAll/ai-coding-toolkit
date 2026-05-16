## Development Process

<!-- workflow-projectization-patch -->

### Task Development Flow

```text
1. Create or select task
   --> python3 ./.trellis/scripts/task.py create "<title>" --slug <name> or list

2. Start task (mark as current)
   --> python3 ./.trellis/scripts/task.py start <name>
   --> Writes session-scoped active task runtime state; future sessions and hooks can re-enter the current task

3. Write code according to guidelines
   --> Read .trellis/spec/ docs relevant to your task
   --> For cross-layer: read .trellis/spec/guides/

4. Self-test
   --> Run the project's frozen verification commands when scaffold exists (see spec docs)
   --> Manual feature testing

5. Commit code
   --> git add <files>
   --> git commit -m "type(scope): description"
       Format: feat/fix/docs/refactor/test/chore

6. Final close-out
   --> python3 ./.trellis/scripts/task.py archive <task-name>
   --> python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
   --> archive runs first, then add_session
```

`python3 ./.trellis/scripts/task.py finish` remains available when you intentionally need to clear the current session's active task without archiving a completed task. Do not use it as a substitute for final close-out.

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

After the human has tested and committed the code, archive the current task first and record the session second:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>

python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

git status --short .trellis/workspace .trellis/tasks
```

Expected metadata status output: empty.

Notes:

- Close-out follows Trellis native `finish-work` behavior: archive first, then `add_session.py`.
- `archive` 预期会清除当前 session 的 active-task runtime；真正需要关注的阻塞条件是 `.trellis/workspace` / `.trellis/tasks` 元数据仍然 dirty。
- Detailed close-out gates still belong to the installed `/trellis:finish-work` / `trellis-finish-work` and `/trellis:delivery` entries; legacy `/trellis:record-session` is old-target compatibility only. This workflow guide only summarizes the default path.

### Pre-end Checklist

Close-out runs in two phases:

**Phase A — pre-commit (`/trellis:finish-work`)**

1. Frozen verification matrix executed or truthfully marked `deferred` / `not run`
2. Manual browser / app verification completed where required
3. `finish-work-checklist.md` records the current close-out evidence
4. Spec docs updated if needed

**Phase B — post-commit**

1. Human commit already exists
2. Current completed task archived; if it is a child task, the parent coordinator records are also synchronized to the new completed frontier
3. `add_session.py` completed successfully for the current session record
4. `.trellis/workspace` and `.trellis/tasks` metadata clean

---

## Phase Index

<!-- workflow-projectization-phase-index-patch -->

```
feasibility → brainstorm → design → plan → implementation → test-first → project-audit → check → review-gate → finish-work → delivery → record-session
```

Stage transition gates are enforced by `workflow-state.py set --stage <next>`; use `--force` to bypass for repair scenarios.

### Stage Transition Quick Reference

All transitions follow a two-step protocol: **(A)** signal readiness by setting `stage_status=awaiting_user_confirmation`, then **(B)** after user confirms, switch to the next stage. `workflow-state.py set` applies all flags in one call and validates the final state.

| From → To | Step A: Signal readiness | Step B: After user confirms |
|---|---|---|
| no_task → feasibility | N/A (outsourcing first entry) | `workflow-state.py route` → load `/trellis:feasibility` (skill auto-creates task + init) |
| feasibility → brainstorm | assessment.md approved | `workflow-state.py set <dir> --stage brainstorm --stage-status in_progress --allowed-next design,plan` |
| brainstorm → design | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage design --stage-status in_progress --awaiting-user-confirmation false --allowed-next plan --transition-from brainstorm` |
| design → plan | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage plan --stage-status in_progress --awaiting-user-confirmation false --allowed-next implementation,test-first --transition-from design` |
| plan → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next test-first,check,project-audit --transition-from plan` |
| plan → test-first | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage test-first --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next implementation,check,project-audit --transition-from plan` |
| implementation → check | code complete | `workflow-state.py set <dir> --stage check --stage-status in_progress --allowed-next review-gate,implementation` |
| implementation → test-first | code complete | `workflow-state.py set <dir> --stage test-first --stage-status in_progress --allowed-next implementation,check,project-audit` |
| check → review-gate | check passes | `workflow-state.py set <dir> --stage review-gate --stage-status in_progress --allowed-next finish-work,implementation` |
| review-gate → finish-work | review passes | `workflow-state.py set <dir> --stage finish-work --stage-status in_progress --allowed-next delivery,record-session` |
| finish-work → delivery | archive + add_session done | `workflow-state.py set <dir> --stage delivery --stage-status in_progress --allowed-next record-session` |
| delivery → record-session | delivery accepted | `workflow-state.py set <dir> --stage record-session --stage-status in_progress --allowed-next` |

For repair scenarios, append `--force` to bypass validation gates.

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
After passing, proceed to `review-gate` or back to `implementation`.
[/workflow-state:check]

[workflow-state:review-gate]
Current stage: **review-gate** — multi-CLI supplementary review.
Load `/trellis:review-gate` for additional cross-platform quality assurance.
After passing, proceed to `finish-work`.
[/workflow-state:review-gate]

[workflow-state:finish-work]
Current stage: **finish-work** — commit preparation and session wrap-up.
Load `/trellis:finish-work` for commit checklist and close-out.
After this stage, run `task.py archive <task-name>` then `add_session.py` to complete close-out before proceeding to `delivery`.
[/workflow-state:finish-work]

[workflow-state:delivery]
Current stage: **delivery** — project handover and deployment.
Load `/trellis:delivery` for acceptance, deliverables, and ownership proof.
[/workflow-state:delivery]

[workflow-state:record-session]
Current stage: **record-session** — workflow cycle complete.
This is the strong-gate terminal stage confirming that all close-out steps (archive + add_session) have been recorded. The workflow cycle is now complete.
The legacy `/trellis:record-session` command remains available as a backwards-compatible entry point for older projects that use the baseline three-phase model; in the strong-gate flow this stage is reached automatically after `delivery`.
[/workflow-state:record-session]

---

## No-Task Entry Point (Strong-Gate)

<!-- workflow-projectization-no-task-patch -->

[workflow-state:no_task]
No active task. **A Direct answer** — pure Q&A / explanation / lookup / chat; no file writes + one-line answer + repo reads ≤ 2 files → AI judges, no override needed.
**A+ Deep analysis** — multi-file read-only audit / architecture review / diagnostic report; file writes limited to analysis docs (research/, temp files); no source code / config / project file modification allowed. Creates a task only if the user explicitly asks to act on findings.
**B Create a task** — any implementation / code change / build / refactor work. For outsourcing profile: entry sequence starts with feasibility gate — (1) `python3 ./.trellis/scripts/workflow/workflow-state.py route` to detect first-entry → (2) if `action=first_entry`, load `/trellis:feasibility` (the feasibility skill will automatically create the task directory and initialize workflow-state.json) → (3) after feasibility passes, `trellis-brainstorm` for prd iteration → (4) `task.py start <task-dir>`. For personal profile: (1) `task.py create "<title>"` → (2) `trellis-brainstorm` → (3) `task.py start <task-dir>`. **"It looks small" is NOT grounds for downgrading B to A+ or C**.
**C Inline change** (per-turn only, escape hatch for B) — the user's CURRENT message MUST contain one of: "skip trellis" / "no task" / "just do it" / "don't create a task" / "跳过 trellis" / "别走流程" / "小修一下" / "直接改" / "先别建任务" → briefly acknowledge ("ok, skipping trellis flow this turn"), then inline. **Without seeing one of these phrases you must NOT inline on your own**; do not invent an override the user never said.
[/workflow-state:no_task]

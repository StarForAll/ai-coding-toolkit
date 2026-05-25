## Development Process

<!-- workflow-projectization-patch -->

### Command Architecture

This installed workflow combines Trellis baseline entrypoints with workflow-defined stage entrypoints.

| Category | What it means in installed target projects |
|---|---|
| Baseline commands | Trellis already ships the baseline entrypoints such as `continue` and native `finish-work`; this workflow patches them instead of redefining Trellis itself |
| Added workflow commands | This workflow adds project-stage entrypoints such as `feasibility`, `design`, `plan`, `project-audit`, `review-gate`, and `delivery` |
| Overlay commands | `brainstorm` and `check` keep the same public entry name as the baseline, but the installed target-project copy is the workflow-enhanced version |
| Disabled commands | `parallel` is intentionally removed from the active command surface because strong-gate requires a single active task, explicit stage confirmation, and a non-forked mainline |

### Script Organization

Installed target projects keep Trellis baseline runtime helpers under `.trellis/scripts/` and workflow-owned strong-gate helpers under `.trellis/scripts/workflow/`.

| Path family | Ownership boundary |
|---|---|
| `.trellis/scripts/*.py`, `.trellis/scripts/common/*.py` | Trellis baseline runtime and shared task/session helpers |
| `.trellis/scripts/workflow/*.py` | Workflow-installed strong-gate helpers, validators, and patch-repair support owned by this workflow |

When debugging or customizing an installed target project, treat `.trellis/scripts/workflow/` as workflow-managed and Trellis baseline scripts as upstream baseline unless a workflow patch explicitly says otherwise.

### Spec Management

This workflow does not replace the target project's entire `.trellis/spec/` tree. Instead it layers on top of a baseline pack import plus project-local extension.

| Layer | Role |
|---|---|
| `initial_pack` / `initial_pack_assets` | Installer imports `pack.requirements-discovery-foundation` as the workflow's baseline requirements/spec foundation |
| `initial_pack_cleanup_policy = retain-imported-assets` | Imported foundation assets remain in the target project after install; uninstall does not delete them by default |
| project `.trellis/spec/` updates during design | The workflow then expects the project to extend/refine those imported specs according to the confirmed architecture |

So the merge strategy is: import baseline pack → retain imported assets → project/workflow refine the relevant specs in-place.

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
   --> plan -> implementation requires checkpoints.execution_authorized=true
   --> If task.py start runs without session identity, it follows the Trellis baseline degraded behavior for that shell and does not persist a separate degraded active-task fallback contract; users should re-run it inside a session-aware AI environment when task binding is required

5. Verify and commit
   --> Run the project's frozen verification commands when scaffold exists (see spec docs)
   --> Manual feature testing
   --> git add <files>
   --> git commit -m "type(scope): description"

6. Final close-out
   --> delivery handles project-level / handoff-level acceptance and deliverables
   --> native finish-work handles current active task archive + add_session
```

`python3 ./.trellis/scripts/task.py finish` remains available when you intentionally need to clear the current session's active task without archiving a completed task. Do not use it as a substitute for final close-out. When session identity is unavailable, `task.py start` follows the Trellis baseline degraded behavior and the router should rely on the normal Trellis session runtime only.

For workflows that split work into a parent coordination task plus child execution tasks:

- freeze the project test-first baseline once in design/spec docs
- select one concrete child task before entering implementation
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

### Native Finish-Work Close-Out

The strong-gate workflow reuses native Trellis `finish-work` for terminal close-out after `delivery`:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>

python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

git status --short .trellis/workspace .trellis/tasks
```

Expected metadata status output: empty. This remains the native `finish-work` close-out action.

Notes:

- `delivery` handles project-level acceptance, deliverables, and ownership proof.
- Native `finish-work` handles the current active task's final `task.py archive` + `add_session.py`.
- If a workflow instance needs both in the same round, treat them as different layers: project-level `delivery` plus task-level native `finish-work`.
- `record-session` remains only as a legacy compatibility entry for older target projects; it is not part of the fresh-baseline strong-gate stage chain.

### Pre-end Checklist

Close-out runs in two phases:

**Phase A — delivery (`/trellis:delivery`)**

1. Frozen verification matrix executed or truthfully marked `deferred` / `not run`
2. Manual browser / app verification completed where required
3. `finish-work-checklist.md` records the current close-out evidence
4. Spec docs updated if needed
5. Deliverables assembled and verified
6. Acceptance confirmed
7. Ownership proof validated (outsourcing profile)

**Phase B — native close-out (`/trellis:finish-work`)**

1. Current completed task archived; if it is a child task, the parent coordinator records are also synchronized to the new completed frontier
2. `add_session.py` completed successfully for the current session record
3. `.trellis/workspace` and `.trellis/tasks` metadata clean

---

## Phase Index

<!-- workflow-projectization-phase-index-patch -->

```
feasibility → brainstorm → design → plan → implementation → project-audit → check → review-gate → delivery
```

Stage transition gates are enforced by `workflow-state.py set --stage <next>`; use `--force` to bypass for repair scenarios. Native `finish-work` runs after `delivery` and is not modeled as a `workflow-state` stage.

### Stage Transition Quick Reference

All transitions follow a two-step protocol: **(A)** signal readiness by setting `stage_status=awaiting_user_confirmation`, then **(B)** after user confirms, switch to the next stage. `workflow-state.py set` must evaluate the fully merged target state in one call, including any checkpoint flags passed on the same command.

| From → To | Step A: Signal readiness | Step B: After user confirms |
|---|---|---|
| no_task → feasibility | N/A (outsourcing first entry) | `workflow-state.py route` → if `action=entry_choice_required` and当前意图是开始新任务，再进入 `/trellis:feasibility`；若只是只读分析 / 元审计，则保持 `no_task` 直接分析 |
| no_task → brainstorm | N/A (personal first entry) | `workflow-state.py route` → if `action=entry_choice_required` and `target=brainstorm`，先创建 task，并立即 `workflow-state.py init "$TASK_DIR" --stage brainstorm` 初始化阶段状态，再进入 `/trellis:brainstorm`；离开本阶段前必须在当前 task 内补齐 assessment 最低基线 |
| feasibility → brainstorm | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage brainstorm --stage-status in_progress --awaiting-user-confirmation false --allowed-next design,plan,implementation --transition-from feasibility` |
| brainstorm → design | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage design --stage-status in_progress --awaiting-user-confirmation false --allowed-next plan --transition-from brainstorm` |
| brainstorm → plan | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage plan --stage-status in_progress --awaiting-user-confirmation false --allowed-next implementation --transition-from brainstorm` |
| brainstorm → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next check,project-audit --transition-from brainstorm`（仅当 `prd.md` 的 `complexity_decision = L0` 时允许） |
| design → plan | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage plan --stage-status in_progress --awaiting-user-confirmation false --allowed-next implementation --transition-from design` |
| plan → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next check,project-audit --transition-from plan` |
| implementation → check | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage check --stage-status in_progress --awaiting-user-confirmation false --allowed-next project-audit,review-gate,implementation,delivery` |
| implementation → project-audit | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage project-audit --stage-status in_progress --awaiting-user-confirmation false --allowed-next check,review-gate --transition-from implementation` |
| project-audit → check | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage check --stage-status in_progress --awaiting-user-confirmation false --allowed-next project-audit,review-gate,implementation,delivery --transition-from project-audit` |
| project-audit → review-gate | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage review-gate --stage-status in_progress --awaiting-user-confirmation false --allowed-next project-audit,delivery,implementation --transition-from project-audit` |
| project-audit → delivery | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage delivery --stage-status in_progress --awaiting-user-confirmation false --transition-from project-audit` |
| check → project-audit | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage project-audit --stage-status in_progress --awaiting-user-confirmation false --allowed-next check,review-gate --transition-from check` |
| check → review-gate | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage review-gate --stage-status in_progress --awaiting-user-confirmation false --allowed-next delivery,implementation` |
| check → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next check,project-audit --transition-from check` |
| check → delivery | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage delivery --stage-status in_progress --awaiting-user-confirmation false --transition-from check` |
| review-gate → project-audit | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage project-audit --stage-status in_progress --awaiting-user-confirmation false --allowed-next check,review-gate --transition-from review-gate` |
| review-gate → delivery | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage delivery --stage-status in_progress --awaiting-user-confirmation false --transition-from review-gate` |
| review-gate → implementation | `workflow-state.py set <dir> --stage-status awaiting_user_confirmation --awaiting-user-confirmation true` | `workflow-state.py set <dir> --stage implementation --stage-status in_progress --awaiting-user-confirmation false --execution-authorized true --allowed-next check,project-audit --transition-from review-gate` |

For repair scenarios, append `--force` to bypass validation gates.

### Baseline Step Compatibility

The strong-gate workflow keeps stage routing in `workflow-state.py`, but some
baseline Trellis utilities still read `workflow.md` via
`get_context.py --mode phase --step <X.Y>`. The numbered headings below are a
compatibility layer for those readers. They do **not** replace the strong-gate
stage machine above, and they are **not** the preferred entry model for new
strong-gate target projects. New projects should follow `workflow-state.py route`
plus the stage machine; the numbered step blocks remain only to preserve
baseline step lookups such as `get_context.py --mode phase --step <X.Y>`.

#### 1.0 Create task

Use `workflow-state.py route --project-root <project-root>` to decide the first
allowed entry. For new outsourcing work, start at `feasibility`; for pure
read-only / maintainer analysis, remain at `no_task`.

#### 1.1 Requirement exploration

Requirement discovery lives in the `brainstorm` stage. Enter it only after the
current route or prior stage allows `brainstorm`, and keep all requirement
artifacts in the active task directory instead of relying on chat memory.

#### 1.2 Research

Research may happen inside `feasibility`, `brainstorm`, `design`, or later
execution stages, but findings should still be persisted to task files before
they are treated as stage-complete evidence.

#### 1.3 Configure context

The current routing source of truth is `workflow-state.json.stage`. Any
task-local context, execution cards, design artifacts, or delivery proofs must
be aligned with the currently confirmed stage before advancing.

#### 1.4 Activate task

`task.py start <task-dir>` still marks the task as the active task for the
current session, but under strong-gate it does **not** advance
`workflow-state.json.stage`; stage changes happen only through
`workflow-state.py set`.

#### 1.5 Completion criteria

Phase-1-style planning is complete only when the current stage artifacts are
written, route / validation says the next stage is allowed, and the human has
confirmed any required transition gate.

#### 2.1 Implement

Implementation happens only after `plan -> implementation` transition approval, with
`checkpoints.execution_authorized=true` present on the transition that opens
execution. If the team chooses a test-first style, that still runs inside
implementation rather than via a separate workflow-state stage.

#### 2.2 Quality check

Quality review belongs to `check` and, when required, `review-gate`. Use the
project's frozen verification matrix plus any stage-specific artifacts that the
current workflow requires.

#### 2.3 Rollback

If execution reveals a stage defect, move back to the correct prior stage
through the strong-gate transition rules instead of silently treating the task
as still "in progress".

#### 3.1 Quality verification

Final workflow-stage verification happens before and inside `delivery`, after
`check` / `review-gate` leave the task ready for close-out.

#### 3.2 Debug retrospective

When the same issue repeats, capture the root cause before close-out so the
next route does not restart from the same broken assumption.

#### 3.3 Spec update

Stage-complete knowledge must be written back to the relevant spec or workflow
artifact before the task moves into final close-out.

#### 3.4 Commit changes

Commit only the current task's verified work before entering `delivery`.
Native Trellis `finish-work` runs later as terminal close-out, not as a
workflow-state stage shortcut from implementation.

#### 3.5 Wrap-up reminder

The strong-gate close-out order is `delivery -> native finish-work`.
`archive` and `add_session.py` run in native Trellis `finish-work`.

---

## Customizing Trellis (for forks)

This section is for developers who want to modify the installed Trellis workflow itself. Prompt copy lives in this file, but the runtime contract also lives in `workflow-state.py`, installer patchers, and carrier patches. If you change stage semantics, routing, degraded recovery, or gate behavior, update the corresponding runtime scripts and patch templates in the same change instead of treating them as parser-only helpers.

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase sections above. **Critical constraint**: if you change a step's `[required · once]` marker or add a new `[required · once]` step, you MUST also add a matching enforcement line to that phase's `[workflow-state:STATUS]` tag block — otherwise the per-turn breadcrumb omits the reinforcement, and the AI silently skips the step.

Under the strong-gate model, each stage has its own `[workflow-state:STATUS]` tag block, and route-only action states such as `blocked` / `repair_needed` / `awaiting_confirmation_with_blockers` may also own dedicated blocks. The full list of tag blocks lives in the `## Strong-Gate Breadcrumb Blocks` section below.

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

## Skill Routing

When a user request matches one of these intents, route to the corresponding stage entry first. Under the strong-gate model this routing table remains a required quick-reference layer even though the detailed per-turn enforcement now lives in the stage breadcrumb blocks below.

| User intent | Stage / route | Primary execution surface |
|---|---|---|
| New project assessment, can we take it, quote/risk/feasibility | `feasibility` | Claude/OpenCode: `/trellis:feasibility`; Codex: natural language or `feasibility` skill |
| Requirement discovery, PRD clarification, decide whether to split tasks | `brainstorm` | Claude/OpenCode: `/trellis:brainstorm`; Codex: natural language or `brainstorm` skill |
| Architecture/design/spec alignment | `design` | Claude/OpenCode: `/trellis:design`; Codex: natural language or `design` skill |
| Task decomposition / scheduling / readiness gate | `plan` | Claude/OpenCode: `/trellis:plan`; Codex: natural language or `plan` skill |
| Resume implementation on the current approved leaf task | `continue` → `implementation` | Claude/OpenCode: `/trellis:continue`; Codex: natural language or `trellis-continue` skill |
| Project-wide audit / cross-task quality sweep | `project-audit` | Claude/OpenCode: `/trellis:project-audit`; Codex: natural language or `project-audit` skill |
| Task-level formal quality check | `check` | Claude/OpenCode: `/trellis:check`; Codex: natural language or `check` skill |
| Multi-CLI supplementary review gate | `review-gate` | Claude/OpenCode: `/trellis:review-gate`; Codex: natural language or `review-gate` skill |
| Delivery / acceptance / handoff artifacts | `delivery` | Claude/OpenCode: `/trellis:delivery`; Codex: natural language or `delivery` skill |
| Single-task terminal close-out after delivery | native `finish-work` | Claude/OpenCode: `/trellis:finish-work`; Codex: natural language or `trellis-finish-work` skill |

For implementation internals, keep this distinction explicit:

- `trellis-research` / `trellis-implement` / `trellis-check` are Trellis-native implementation-chain roles used inside the implementation stage
- they are not public top-level workflow stages
- Codex inline mode still performs the equivalent work in the main session instead of manually dispatching that chain

### DO NOT skip skills / route guards

| What you're thinking | Why it's wrong under strong-gate |
|---|---|
| "This looks simple, I can skip feasibility/brainstorm and just start coding" | First-entry routing is stage-gated. If the current route says feasibility or brainstorm, skipping it breaks the state machine and later validation. |
| "I already know what stage we're in from the files on disk" | Stage is determined by `active task -> workflow-state.json`, not by guessing from `design/`, `check.md`, or other artifacts. |
| "The next stage is obvious, I'll auto-advance after this reply" | Only the user can confirm stage transitions. AI can recommend, not advance implicitly. |
| "Implementation self-check is enough; formal check/review-gate can be skipped" | The implementation chain and formal `check` / `review-gate` are different layers. Skipping the formal layer hides stage-exit defects. |
| "Delivery already happened, so finish-work is implied" | `delivery` and native `finish-work` are different layers; finish-work remains the single-task close-out entry after delivery, not an automatic side effect. |

---

## Strong-Gate Breadcrumb Blocks

<!-- workflow-projectization-breadcrumb-patch -->

[workflow-state:feasibility]
Current stage: **feasibility** — first project assessment gate.
Load `/trellis:feasibility` to evaluate project viability, risk, and engagement type.
Outsourcing / external-delivery first-entry work must pass feasibility before entering brainstorm. Personal-profile first entry may route directly to brainstorm, but must complete the minimum assessment baseline before leaving that stage.
When both repo-root `assessment.md` and `.trellis/workflow-installed.json` profile hints exist, route trusts `assessment.md` / `project_engagement_type` first. The install-record profile is only a fallback when no reusable assessment exists yet.
If the project may require ownership proof, freeze `source_watermark_*` and `ownership_proof_required` in line with `源码水印与归属证据链执行卡` before stage exit.
Run `python3 ./.trellis/scripts/workflow/workflow-state.py route` to check routing.
[/workflow-state:feasibility]

[workflow-state:brainstorm]
Current stage: **brainstorm** — requirement discovery and PRD iteration.
Load `/trellis:brainstorm` skill to iterate on prd.md with the user.
Prerequisite:

- outsourcing / external-delivery projects: valid `assessment.md` from feasibility
- personal profile first-entry: `brainstorm` may bootstrap the minimum `assessment.md` baseline in-place, but it must be complete before leaving `brainstorm`
- minimum bootstrap fields: `project_engagement_type`, `法律/合规风险结论`, `source_watermark_level`, `source_watermark_channels`, `zero_width_watermark_enabled`, `subtle_code_marker_enabled`, `ownership_proof_required`, `是否允许进入 brainstorm`
- minimum baseline vs full feasibility assessment: the personal bootstrap branch only satisfies the minimum gate needed to stay in `brainstorm` and leave it safely; it does **not** replace the fuller risk-analysis, pricing, negotiation, and external-delivery assessment fields that `/trellis:feasibility` may record
- whether personal projects must later return to `feasibility`: not by default. If the project remains an internal/non-outsourcing effort and no later decision needs the full feasibility artifact set, it may continue from `brainstorm` into later stages. If the project later introduces outsourcing-style delivery control, pricing/negotiation commitments, or other assumptions that the minimum baseline does not cover, return to `/trellis:feasibility` and complete the fuller assessment there before proceeding
- if a personal-profile task wants to enrich the assessment beyond the minimum baseline while still inside `brainstorm`, it may keep writing the same `assessment.md` in-place. Return to `/trellis:feasibility` only when the project needs the full feasibility decision path, not merely because more detail was added
- if the project does not explicitly set `ownership_proof_required = no`, personal-profile bootstrap must also freeze `source_watermark_level`, `source_watermark_channels`, and `ownership_proof_required` before stage exit
During requirement iteration, keep the execution-card obligations visible: requirement-scope changes must follow `需求变更管理执行卡`, and ownership / watermark-sensitive projects must preserve the upstream constraints later enforced by `源码水印与归属证据链执行卡`.
After prd.md and jsonl are curated, set `stage_status = awaiting_user_confirmation` for design/plan transition.
[/workflow-state:brainstorm]

[workflow-state:design]
Current stage: **design** — architecture and design document creation.
Load `/trellis:design` to produce developer-facing PRD (block A), design docs (block B), project docs (block C), and engineering alignment (block D).
Block/file mapping summary:

- block A → `docs/requirements/developer-facing-prd.md`
- block B → design authority docs such as `design/TAD.md`, `design/ODD-dev.md`, `design/ODD-user.md`, plus conditional design artifacts like `design/DDD.md`, `design/IDD.md`, `design/AID.md`, `design/STITCH-PROMPT.md`, `design/specs/<module>.md`, `design/pages/<page>.md`, and `design/source-watermark-plan.md` when applicable
- block C → project-facing docs such as project-root `README.md`, `README.en.md`, and target-project `docs/` updates aligned to the confirmed architecture
- block D → engineering alignment work: projectized `.trellis/spec/` refinement, `Context7` review via `design/context7-review.md`, the automation/quality verification matrix, and the `/trellis:finish-work` / close-out adaptation baseline
`engineering alignment (block D)` is the stage area where the project-level automation check matrix is finalized; installed `quality-guidelines.md` files may still contain a workflow-aware placeholder, but the real verification matrix must be frozen by this block
Each design block requires a stop-and-confirm boundary before proceeding to the next block; do not treat A/B as the only confirmation points.
Run `python3 ./.trellis/scripts/workflow/workflow-state.py validate <task-dir> --project-root <root>` to check exit readiness.
[/workflow-state:design]

[workflow-state:plan]
Current stage: **plan** — task decomposition and scheduling.
Load `/trellis:plan` to decompose work into child tasks with prd.md.
**Hard prohibition**: no implementation code, no scaffolding, no migration scripts.
If ownership proof is enabled, decompose the watermark / ownership tasks required by `源码水印与归属证据链执行卡` instead of leaving them implicit.
Set `stage_status = awaiting_user_confirmation` when plan is ready for user approval.
[/workflow-state:plan]

**Global execution rule**: this embedded workflow is main-session-only in every stage. Do not dispatch `trellis-research`, `trellis-implement`, `trellis-check`, or other platform agents/sub-agents; keep all execution in the current main session.

[workflow-state:implementation]
Current stage: **implementation** — code writing phase.
`checkpoints.execution_authorized` must be `true` before entering.
Re-enter this stage through `/trellis:continue`; do **not** expect a public `/trellis:implementation` command or same-named shared skill.
This embedded workflow is main-session-only: do the implementation work directly in the current session (load `trellis-before-dev` first) and do not dispatch `trellis-implement` or other sub-agents.
If `ownership_proof_required = yes` and design has declared `Protected Watermark Snippets`, run `source-watermark-guard.py --task-dir <task-dir> --mode check` before touching protected files; only explicitly declared low-risk snippets may use `--mode repair`, and you must rerun `--mode check` afterwards.
If you need TDD-style verification, do it inside implementation rather than switching to a separate `test-first` stage.
After implementation, proceed to `check`.
[/workflow-state:implementation]

[workflow-state:project-audit]
Current stage: **project-audit** — full-project quality review.
Formal mode typically re-enters here from `check` / `review-gate`; pre-audit may enter early from `implementation`.
Load `/trellis:project-audit` for cross-cutting quality assessment.
[/workflow-state:project-audit]

[workflow-state:check]
Current stage: **check** — quality check against spec and conventions.
Load `/trellis:check` to validate implementation against specifications.
After passing, proceed to `project-audit`, `review-gate`, back to `implementation`, or directly to `delivery` (when no project-audit / review-gate is needed).
[/workflow-state:check]

[workflow-state:review-gate]
Current stage: **review-gate** — multi-CLI supplementary review.
Load `/trellis:review-gate` for additional cross-platform quality assurance.
If the task still needs a formal project-level sweep, it may re-enter `project-audit` from here before `delivery`.
After passing, proceed to `delivery`.
[/workflow-state:review-gate]

[workflow-state:delivery]
Current stage: **delivery** — project handover and deployment.
Load `/trellis:delivery` for acceptance, deliverables, and ownership proof.
If ownership proof is enabled, verify the final evidence chain against `源码水印与归属证据链执行卡` before leaving delivery.
After delivery completes, enter native Trellis `/trellis:finish-work` for the final archive + session-record close-out.
[/workflow-state:delivery]

[workflow-state:awaiting_confirmation]
Route action: **awaiting_confirmation** — stop at the confirmation boundary.
Do not continue executing the current stage body until the user explicitly confirms the transition.
If the header contains `Stage: ...`, treat it as context only; the required action now is to summarize readiness and wait.
[/workflow-state:awaiting_confirmation]

[workflow-state:awaiting_confirmation_with_blockers]
Route action: **awaiting_confirmation_with_blockers** — the stage reached its confirmation point, but exit blockers still exist.
Fix every header `Blockers:` item first. Do **not** ask for stage transition confirmation until the blockers are cleared and `workflow-state.py route` no longer returns this action.
[/workflow-state:awaiting_confirmation_with_blockers]

[workflow-state:blocked]
Route action: **blocked** — do not keep executing the current stage as if it were normal re-entry.
Read the header `Reason:` / `Blockers:` lines, repair those conditions, then rerun `workflow-state.py route`.
If the header contains `Stage: ...`, that stage name is diagnostic context, not permission to proceed.
[/workflow-state:blocked]

[workflow-state:context_needed]
Route action: **context_needed** — the current task cannot continue directly.
Most commonly this means the current stage requires a leaf task but the active task still has `children`.
Switch to the correct child task with `task.py start <child-task-dir>` before continuing.
[/workflow-state:context_needed]

[workflow-state:recovery_needed]
Route action: **recovery_needed** — the workflow cannot determine the active task safely.
Do not guess from filenames or chat history. Ask the user to clarify the current task, or explicitly reselect it with `task.py start <task-dir>`.
[/workflow-state:recovery_needed]

[workflow-state:repair_needed]
Route action: **repair_needed** — workflow state is missing, uninitialized, stale, or structurally invalid.
Run `workflow-state.py repair <task-dir>` first.
Basic usage:

- inspect only: `python3 ./.trellis/scripts/workflow/workflow-state.py repair <task-dir>`
- rebuild after confirmation: `python3 ./.trellis/scripts/workflow/workflow-state.py repair <task-dir> --stage <stage> --apply`
- execution-stage rebuild: `python3 ./.trellis/scripts/workflow/workflow-state.py repair <task-dir> --stage implementation --execution-authorized true --transition-from <previous-stage> --apply`

Status meanings:

- `repair_ready`: the helper has enough evidence and explicit inputs to rebuild a valid `workflow-state.json`; confirm with the user, then rerun with `--apply`
- `manual_confirmation_required`: the helper refuses to guess a required stage or execution authorization detail; ask the user to confirm the currently approved stage and any required execution boundary flags, then rerun with those explicit arguments
- `repair_blocked`: the remaining state is still structurally inconsistent even after normalization; fix the listed blockers first

Recovery path:

1. run `repair` without `--apply` to inspect status/evidence/blockers
2. if status is `repair_ready`, confirm with the user and rerun with `--apply`
3. if status is `manual_confirmation_required`, gather the missing stage / execution-boundary confirmation from the user, then rerun with the required flags
4. after apply succeeds, rerun `workflow-state.py route` or `workflow-state.py validate <task-dir>` before resuming the stage body

Execution re-entry such as `implementation` requires explicit `--execution-authorized true` and `--transition-from <previous-stage>`.
[/workflow-state:repair_needed]

[workflow-state:embed_invalid]
Route action: **embed_invalid** — the installed workflow surface is incomplete or drifted.
Stop normal task execution and repair the workflow installation first. Check `.trellis/workflow-installed.json`, `.trellis/library-lock.yaml`, helper scripts, and critical runtime patches before continuing.
[/workflow-state:embed_invalid]

[workflow-state:workflow-state.route_failed]
Route action: **workflow-state.route_failed** — the route helper itself failed.
Do not treat the current stage as trustworthy. Inspect the header `Reason:` line, fix the route helper or its runtime dependency, then retry.
[/workflow-state:workflow-state.route_failed]

[workflow-state:stale]
Active task pointer is stale: the session still points at a task directory that no longer exists.
Before continuing stage work, inspect the stale pointer with `python3 ./.trellis/scripts/task.py current --source`, then either run `task.py finish` to clear it or `task.py start <task-dir>` to repoint the session at the correct live task.
Do **not** treat this as `no_task`, and do not silently continue implementation / check / delivery work against missing task context.
[/workflow-state:stale]

---

## No-Task Entry Point (Strong-Gate)

<!-- workflow-projectization-no-task-patch -->

[workflow-state:no_task]
No active task. **A Direct answer** — pure Q&A / explanation / lookup / chat; no file writes + one-line answer + repo reads ≤ 2 files → AI judges, no override needed.
**A+ Deep analysis** — multi-file read-only audit / architecture review / diagnostic report; file writes limited to disposable `tmp/` artifacts or other explicitly analysis-only scratch paths used only to support the current read-only analysis; no source code / config / project file modification allowed. Do **not** treat ordinary project-root docs, specs, workflow assets, or user-facing product files as “temp files”. Creates a task only if the user explicitly asks to act on findings, or if the next step clearly changes from read-only analysis into implementation / source editing / durable workflow asset updates.
**B Create a task** — any implementation / code change / build / refactor work. For outsourcing profile: entry sequence starts with route intent choice — (1) `python3 ./.trellis/scripts/workflow/workflow-state.py route` → (2) if `action=entry_choice_required` and当前意图是开始新任务，load `/trellis:feasibility` (the feasibility skill will automatically create the task directory and initialize `workflow-state.json`)；若当前只是 workflow / 项目只读分析、元审计或 A/A+ 纯分析，则停留在 `no_task` 直接分析，不创建任务 → (3) after feasibility passes, load `/trellis:brainstorm` for prd iteration → (4) `task.py start <task-dir>`. For personal profile: (1) `task.py create "<title>"` → (2) load `/trellis:brainstorm` — personal profile can skip feasibility but **must** supplement the minimum `assessment.md` baseline during brainstorm (`project_engagement_type=non_outsourcing`, `法律/合规风险结论`, `source_watermark_level`, `source_watermark_channels`, `zero_width_watermark_enabled`, `subtle_code_marker_enabled`, `ownership_proof_required`, `是否允许进入 brainstorm=是`), otherwise subsequent stage gate validation will block → (3) `task.py start <task-dir>`. **"It looks small" is NOT grounds for downgrading B to A+ or C**.
`task.py start` in this branch only persists or repairs the active-task pointer for the current session. It does **not** advance `workflow-state.json.stage`, and in strong-gate installs it also does **not** keep producing the legacy `planning → in_progress` status flip; stage changes must still be performed via `workflow-state.py set` after the current stage reaches `awaiting_user_confirmation`.
**C Inline change** (per-turn only, escape hatch for B) — the user's CURRENT message MUST contain one of: "skip trellis" / "no task" / "just do it" / "don't create a task" / "跳过 trellis" / "别走流程" / "小修一下" / "直接改" / "先别建任务" → briefly acknowledge ("ok, skipping trellis flow this turn"), then inline. **Without seeing one of these phrases you must NOT inline on your own**; do not invent an override the user never said.
[/workflow-state:no_task]

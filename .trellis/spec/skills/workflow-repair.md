# workflow-repair Skill Specification

> Behavioral contract for the installable skill `skills/workflow-repair/`.

---

## Purpose

`workflow-repair` is the repair-side half of the installable
`workflow-scan` / `workflow-repair` pair.

It consumes `WORKFLOW_QUESTIONS.md`, re-checks each reported issue against the
temp project and inferred source workflow repair surfaces, then repairs only the
workflow product source under `docs/workflows/新项目开发工作流/`.

---

## Scope Boundary

`workflow-repair` must preserve all of the following:

1. File modification scope is locked to `docs/workflows/新项目开发工作流/`,
   the dedicated current repair task directory, and `tmp/workflow-issues/`.
2. The skill must always create/switch to a dedicated repair task before it
   writes task-local artifacts; it must not reuse a pre-existing active task.
3. Task-local repair artifacts and issue-history documents may be written, but
   they are never deleted as part of the run.
4. The temp project remains the primary truth source for whether a reported
   issue exists.
5. The skill runs inline in the current CLI session. Do not route through
   agents or sub-agents.
6. Trellis-native defects must be patched from within the workflow directory so
   the installer can repair future target projects.
7. The skill does not require a same-run re-embed; instead it must complete a
   strict source-side review before it claims success.
8. Repair-side intake is execution-mode agnostic: a scan produced inline or via
   explicit `--agent` assistance is equally acceptable if the final
   `WORKFLOW_QUESTIONS.md` passes the shared contract validation.
9. Scan-side `--agent` support does not imply repair-side agent support; repair
   remains a main-session-only skill unless its own scope boundary changes.
10. `--auto` is an explicit repair-side continuation mode only. It may continue
    into current-task close-out after a successful repair run, but it must not
    bypass plan presentation, authorization, verification, commit readiness, or
    finish-work safety gates.
11. `--auto` depends on the current Trellis platform's close-out interaction
    flow. If that platform flow changes, the repair-side auto-follow-through
    behavior must be re-verified before being trusted.

---

## Required Behaviors

### 1. Report, Task, and Temp Project Resolution

The skill must:

- resolve `WORKFLOW_QUESTIONS.md` from `/tmp/trellis-{VERSION}-2/` when the
  user did not supply a path
- derive a repair-task short topic from the report or fall back to a stable
  default
- create a dedicated repair task if none exists
- create a new dedicated repair task and switch to it when another task is
  already active
- validate the shared `workflow-scan-repair-v2` protocol
- resolve the temp project from the report before judging findings
- stop instead of guessing when report/temp context does not line up

### 2. Verification Discipline

The skill must treat every scan finding as a hypothesis.

Before adoption, it must:

- inspect the referenced temp-project artifact when available
- infer and inspect the relevant source-side repair surface
- cross-check relevant declarations such as `workflow_assets.py`
- identify a concrete root-cause class instead of stopping at the visible symptom
- prefer `ignored`, `blocked`, or `manual-decision` over unsafe auto-adoption
- complete strict source-side review rather than requiring a same-run re-embed

If a finding appears to be a repeat of an earlier repair attempt, the skill must
escalate rather than reapply the same narrow patch blindly.

### 3. Issue-History Discipline

The skill must:

- read all numeric Markdown documents under `tmp/workflow-issues/` before
  deciding whether a finding is new or repeated
- compare repeatedness using problem title/ID, root cause, repaired files,
  variant sweep scope, and key marker/path evidence
- write exactly one new numeric Markdown document to `tmp/workflow-issues/`
  for each repair execution
- keep numbering monotonic within that directory

### 4. Authorization Discipline

The skill must distinguish:

- explicit repair requests, which count as standing authorization after the
  correction plan is echoed
- analysis-only requests, which must stop after the correction plan until the
  user confirms execution
- explicit `--auto` requests, which may continue into current-task close-out
  only after the normal repair flow has already succeeded
- `post-plan-confirmation`, which is the execution-time authorization state
  after an analysis-only run receives explicit Step 8 confirmation to proceed

### 4A. Auto Follow-Through Discipline

When `--auto` is requested, the skill must:

- keep `--auto` opt-in and literal rather than inferring it from vague
  "continue" language
- treat `--auto` as a post-repair continuation mode, not as expanded repair
  authority
- continue only within the current repair task's normal close-out flow
- reply `ok` only when the current task's own one-shot commit confirmation
  prompt appears
- require commit-confirmation detection to be explicit to the current repair
  task and to clearly ask for a yes/confirm style response before replying `ok`
- stop when the close-out flow changes in a way that makes single-shot commit
  confirmation unreliable, rather than risking over-confirmation
- stop when any other interactive prompt appears; do not guess a reply
- invoke the available Trellis finish-work command surface only after the task
  is actually ready for wrap-up
- stop when no finish-work command surface exists in the current
  platform/session; do not invent a substitute close-out path
- keep repair-side agent behavior unchanged even if the request also mentions
  `--agent`; `--auto` must not be treated as agent-mode expansion
- treat findings outside an explicit `target_focus` as outside the close-out
  safety decision for `--auto`
- if out-of-focus findings carry higher severity, require the correction plan
  to surface that fact so auto close-out is visibly understood as narrowed
  scope rather than as a fully clean report
- treat `--auto` as having no effect when authorization remains
  `analysis-only` and repair execution never actually runs
- allow `--auto` to continue after partial acceptance only when unresolved
  `blocked` / `manual-decision` items are recorded clearly enough that the
  resulting commit will not misrepresent the repair as fully complete
- stop when `total-succeeded = 0` and `total-attempted > 0` rather than
  continuing to commit/finish-work as if a successful repair occurred
- write continuation outcome into the repair log in two phases:
  `pending` before Step 12 completes, then the final outcome after Step 12
- define `total-attempted` as every repair item that actually entered
  execution, regardless of whether the final status became succeeded, failed,
  or reverted
- treat Step 12 blockers as stopping the close-out flow only; the log update
  and final outcome report must still run afterward
- on a later resumed run, convert stale `pending` continuation state to
  `interrupted: session-did-not-complete` before recording a newer final
  outcome
- treat the latest repair log under the current repair task as the source for
  detecting whether a resumed run is recovering stale `pending` state, using
  the highest `repair-timestamp` value rather than filename ordering alone
- stop and report a blocker instead of forcing commit confirmation or
  finish-work when readiness is unclear or unsafe

### 5. Variant Discipline

For every confirmed safe issue, the skill must search only within
`docs/workflows/新项目开发工作流/` for same-pattern or same-root-cause siblings.

It may repair those siblings in the same run only when:

- the root cause is materially the same
- the repair remains low-risk
- the scope stays inside the workflow directory

The sweep result must be recorded in both the correction plan and the repair
log, even when no sibling fix was needed.

### 6. Contract-Surface Discipline

For each adopted or trellis-native fix, the skill must map the workflow-local
surfaces that should stay aligned if the fix is correct.

Typical surfaces include:

- source scripts
- docs or command markdown
- `workflow_assets.py` declarations
- in-tree tests under the workflow directory
- workflow-local metadata or generated-source companions

If a finding is caused by partial cross-file drift, the skill must not treat a
single-file patch as sufficient unless it explicitly proves the other surfaces
do not need updates.

### 7. Coupled Artifact Discipline

The skill must keep all repair-side protocol surfaces aligned:

- `skills/workflow-repair/SKILL.md`
- `skills/workflow-repair/references/correction-plan-template.md`
- `skills/workflow-repair/references/repair-log-template.md`
- `skills/workflow-repair/references/issue-history-template.md`
- the shared scan report template used by `workflow-scan`

This coupling is **bidirectional and mandatory**:

- whenever `skills/workflow-repair/SKILL.md` changes any shared protocol,
  intake assumption, role boundary, or repair-side decision contract, the
  paired `skills/workflow-scan/SKILL.md` surface must be updated in the same
  change
- whenever `workflow-scan` changes the emitted report contract, this repair
  skill must be adapted in the same change; do not leave repair-side intake on
  the previous contract
- when `workflow-scan` changes execution-mode rules without changing the report
  schema, this repair spec must still state that intake remains based on the
  validated report contract rather than on scan execution topology
- the pair must stay aligned on the scan-side read-back validation rule so
  repair-side intake assumptions match what a successful scan is allowed to emit
- intake must reject reports whose declared total/severity counts do not match
  the actual finding blocks in the report body

---

## Review Checklist

When editing `skills/workflow-repair/`, confirm all of the following:

- modification scope is still locked to `docs/workflows/新项目开发工作流/`
- a dedicated repair task is still mandatory and project-root artifact fallbacks
  are not reintroduced
- the skill still forbids agent/sub-agent execution
- the skill still verifies against the temp project, not only source files
- repair-side intake remains agnostic to whether scan ran inline or with
  explicit `--agent`
- the skill still reads all `tmp/workflow-issues/` history docs and writes one
  new issue-history file per run
- issue-history docs now record continuation mode when `--auto` is part of the
  execution context
- explicit repair authorization and analysis-only behavior remain distinct
- `--auto` remains explicit, post-repair only, and current-task scoped
- `--auto` now explicitly no-ops when repair execution never runs under
  `analysis-only`
- that no-op rule now explicitly applies only when authorization never advanced
  beyond `analysis-only`
- `post-plan-confirmation` is now explicitly defined and remains distinct from
  both `analysis-only` and `authorized-to-repair`
- `--auto` still does not create any repair-side `--agent` interaction
- `--auto` now explicitly stops on non-commit interactive prompts instead of
  guessing a reply
- `--auto` now explicitly stops when one-shot commit confirmation cannot be
  identified reliably
- `--auto` now explicitly stops when no finish-work command surface is
  available
- repeated findings now force broader closure or escalation
- same-pattern sweep behavior is still documented and logged
- contract-surface coverage and repeat-trigger checks are still documented in the plan/log artifacts
- repair-log timing now records continuation outcome without contradicting Step
  11 / Step 12 ordering
- `--auto` still stops instead of forcing finish-work when commit readiness or
  close-out safety is not satisfied
- any protocol, field, role-boundary, example, or behavior change is mirrored
  by a matching `workflow-scan` adaptation and shared-template update in the
  same change

---

## Validation Notes

Minimum expected validation:

- `./scripts/validate-skills.sh`
- paired diff review across:
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `skills/workflow-repair/references/correction-plan-template.md`
  - `skills/workflow-repair/references/repair-log-template.md`
  - `skills/workflow-repair/references/issue-history-template.md`
- verify the scan-side contract now includes an explicit read-back validation
  gate and that repair-side intake assumptions still match that stronger output
  guarantee
- verify repair-side wording does not make inline-only assumptions about how
  scan evidence was gathered before the final report was written
- verify repair-side examples include at least one report intake path for a
  validated `workflow-scan --agent` output
- verify `--auto` is documented as explicit, post-repair only, and blocked when
  the current task is not ready for commit/finish-work
- verify the paired `workflow-scan` diff is an actual compatibility adaptation
  when the repair-side contract changed, not just an unchanged carryover

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
   the dedicated current repair task directory, and optional audit-shadow
   outputs under `tmp/workflow-issues/`.
2. The skill must always create/switch to a dedicated repair task before it
   writes task-local artifacts; it must not reuse a pre-existing active task.
3. Task-local repair artifacts such as repair logs and closure-round artifacts
   may be written, and they are never deleted as part of the run.
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
12. `--auto` close-out must re-enter the current repair task through the
    normal Trellis `continue` surface before `finish-work`; it is not a direct
    jump from repair summary to finish-work.
13. When a Trellis close-out surface is needed, availability must be checked
    in this order: callable platform command surface first, then same-session
    skill surface in the current project/runtime. Only when both are absent may
    the skill treat that surface as missing.
14. `--auto` must stop its `continue` loop when the current repair task is
    clearly closed/completed by `continue`, and must also stop when it cannot
    prove whether another `continue` would be safe.
15. Actionable defect judgment for this skill version is limited to the current
    workflow's Claude Code / OpenCode / Codex managed surfaces. Findings that
    depend only on other CLI usage remain out of scope unless the
    workflow-managed surface is explicitly expanded.
16. `.backup-original/` trees under managed command/skill carriers must not be
    treated as workflow defects by default when temp-project evidence shows
    they are intentional restore surfaces paired with active patched/overlay
    assets in `.trellis/workflow-installed.json`.
17. Cross-task convergence must not be treated as a fresh start just because a
    new dedicated repair task was created. If the same temp-project/report
    lineage already produced two earlier ordinary repair tasks, the next
    attempt must escalate to audit / break-loop instead of continuing another
    routine repair batch.

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
- validate the shared `workflow-scan-repair-v4` protocol
- resolve the temp project from the report before judging findings
- derive a repair-lineage identity from `source-report`, `temp-project-root`,
  and `trellis-version`, using `scan-timestamp` / `repair-lineage-key` as
  stronger evidence when those fields are available
- normalize `repair-lineage-key` as
  `normalize(source-report) + "|" + normalize(temp-project-root) + "|" + trellis-version`,
  where `normalize(path)` resolves absolute paths when possible, converts
  separators to `/`, collapses redundant separators, and strips trailing `/`
  except for filesystem root
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
- classify the item as `ignored` rather than `manual-decision` when the temp-
  project symptom is real but sits outside the current workflow product-source
  ownership boundary under `docs/workflows/新项目开发工作流/`
- classify the item as `ignored` rather than `manual-decision` when the temp-
  project symptom only reflects a Trellis-native hook/runtime convention that
  the current workflow embed preserved unchanged
- classify the item as `ignored` rather than `manual-decision` when the temp-
  project symptom depends only on a CLI outside the current supported
  three-platform surface (Claude Code / OpenCode / Codex)
- classify the item as `ignored` rather than `manual-decision` when the temp-
  project symptom only reports `.backup-original/` carrier copies whose names
  pair cleanly with active patched/overlay assets in
  `.trellis/workflow-installed.json`
- honor the report-side repair classification as a default safety gate:
  `confirmed-defect` may enter normal repair verification, `design-debt`
  defaults to non-adopted handling unless the user explicitly broadens scope,
  and `evidence-gap` must stop for more proof before any source edit is
  allowed

If a finding appears to be a repeat of an earlier repair attempt, the skill must
escalate rather than reapply the same narrow patch blindly.

Before choosing between another ordinary repair batch and a broader audit path
for a repeated temp-project issue, consult the repo-level
`guides/workflow-repeat-issue-triage.md` so the run distinguishes same-family
recurrence from a truly new family or a version-drift case.

When a repair changes runtime-carrier stop / deny / route semantics, closure
must include at least one behavior-level assertion against the installed
carrier path; marker/text presence alone is insufficient for convergence on
that repair family.

### 3. Issue-History Discipline

The skill must:

- require report workflow version, temp-project install-record workflow
  version, and current source `WORKFLOW_VERSION` to match before repair may
  proceed
- treat matching workflow version with mismatched schema version as
  `Blocked / Invalid Embedded State`
- use same-version task-local closure artifacts as the convergence memory
  surface for the current repair task
- inspect earlier repair-task logs across `.trellis/tasks/` and archive for the
  same repair lineage before assuming the current task is a fresh ordinary run
- fall back to legacy matching on `source-report` + `temp-project-root` +
  `trellis-version` when older logs predate explicit lineage fields
- treat workflow version bumps as insufficient to reset the same repair lineage
  on their own
- stop ordinary repair execution and escalate to audit / break-loop if two
  earlier repair tasks already match the same lineage
- optional `tmp/workflow-issues/` outputs are audit shadows only, not the
  primary v4 repair-decision memory
- when the optional shadow is omitted, the repair log should record
  `issue-history-file: none`

### 3A. Version Bump Discipline

When a repair run actually succeeds, the skill must:

- bump `docs/workflows/新项目开发工作流/commands/workflow_assets.py::WORKFLOW_VERSION`
  by incrementing only the final numeric segment
- perform that bump only after closure has converged cleanly and one or more
  repair items remain `verified`
- synchronize the active current-version references in the same change,
  including the workflow overview, command mapping, embed spec, current
  mindmap label/title, and installer assertions that are defined as current-
  version references by the repo contract
- use the workflow-local version-bump helper when available instead of relying
  on memory for the target file list
- skip the version bump entirely when the run is no-op, reverted, failed,
  blocked from convergence, or still has unresolved in-scope closure findings

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
- reply `ok` only when the current task's own eligible commit confirmation
  prompt appears; that eligible confirmation may be either the one-shot commit
  confirmation itself or an explicit current-task commit-plan / commit-scope
  confirmation that still asks for `ok`/yes-style approval
- define `unrecognized working-tree files` as working-tree paths surfaced by
  the close-out flow outside the proposed commit batches and requiring explicit
  include/exclude judgment; they may be modified or untracked
- define `current repair-task artifacts` as files that live inside the current
  repair task directory and are being enumerated by the close-out flow as part
  of that task's commit scope
- treat current repair-task artifacts as independently acceptable by task-
  directory membership plus explicit current-task prompt scoping; they do not
  need separate current-run output proof
- define the current repair run's independently provable output set as
  out-of-directory files inside the skill's other allowed write-scope
  locations when the current run can tie them to its own recorded outputs:
  - workflow source files changed by confirmed repair work under
    `docs/workflows/新项目开发工作流/`
  - the current run's own optional `tmp/workflow-issues/NNNN.md` audit shadow
- a file counts as tied to this run's recorded outputs only when the current
  run's repair log records it as a changed, written, or output file for this
  run
- exclude reverted files from that independently provable output set; a file
  changed and later reverted during post-repair verification is not a remaining
  current-run output for close-out
- reverted files inside the current repair task directory are likewise not
  remaining current-run outputs for close-out, even though the files still live
  in the task directory
- allow unrecognized working-tree files only when the prompt frames them as
  part of the current repair task's commit scope and the skill can still prove
  they belong inside that scope independently
- treat that independent proof as path-plus-run-membership proof rather than as
  task-directory membership alone for out-of-directory files
- require commit-confirmation detection to be explicit to the current repair
  task and to clearly ask for a yes/confirm style response before replying `ok`
- treat phrasing such as `commit the current repair task changes`,
  `commit the current repair task artifacts`, or `commit the focused repairs`
  as minimum-acceptable examples of explicit current-task scope when the rest
  of the prompt stays consistent with that scope
- treat those examples as illustrative rather than exhaustive; semantically
  equivalent phrasing may also qualify when it meets the same explicit
  current-task scope bar
- treat phrasing such as `commit these changes` or `commit working tree
  changes` as insufficient by itself because it does not explicitly frame the
  scope as the current repair task
- stop when the prompt includes working-tree files outside the current repair task's
  commit scope or otherwise mixes task scope with non-task scope
- stop when the prompt's commit-scope or repair-result wording would
  materially overstate the actual repair outcome, including reverted, failed,
  unresolved, or out-of-focus work
- treat wording such as `all fixes verified` or `commit these verified fixes`
  as materially overstating the outcome whenever any attempted fix was
  reverted, failed, unresolved, or left outside `target_focus`
- treat wording such as `commit the successful repairs` or `commit the current
  repair task changes` as potentially honest when it does not imply every
  attempted or every reported fix was verified and when the file list remains
  consistent with that narrower claim
- stop when the prompt does not make either the current-task commit scope or
  the one-shot approval request explicit enough to trust
- stop when the close-out flow changes in a way that makes single-shot commit
  confirmation unreliable, rather than risking over-confirmation
- if multiple blocker causes trigger at once, report all triggered causes in
  the blocker reason rather than collapsing them to a single label
- stop when any other interactive prompt appears; do not guess a reply
- re-enter close-out through the current task's `continue` surface before
  attempting `finish-work`
- define one close-out run as the full post-repair continuation sequence
  beginning with the first `continue` re-entry for this repair task and ending
  only when the task reaches `finish-work`, `reached-task-close`, or stops with
  a blocker
- if a blocker ends that sequence and the task is later resumed, treat the
  resumed continuation as a new close-out run rather than as a continuation of
  the previous one
- keep using `continue` after commit until it either recommends `finish-work`
  or clearly indicates that the current repair task has already closed
- keep the `reply ok exactly once` action centralized in the commit-
  confirmation step rather than duplicating it in the generic `continue`
  inspection step
- record normal task closure reached via `continue` distinctly from
  `reached-finish-work`, rather than pretending finish-work ran when it did not
- bound the `continue` loop with a fixed per-run ceiling so the skill does not
  re-enter forever when safe advancement cannot be proved
- stop rather than looping blindly when `continue` cannot prove whether the
  task advanced, changed stage, or closed
- invoke the available Trellis finish-work surface only after the task
  is actually ready for wrap-up
- stop when no `continue` surface exists in the current platform/session; do
  not invent a substitute re-entry path
- stop when no finish-work surface exists in the current
  platform/session; do not invent a substitute close-out path
- support asymmetric command/skill surface availability as long as each needed
  close-out action can still resolve to either a callable command surface or a
  same-session skill surface at the moment it is needed
- treat both directions of that asymmetric availability as valid:
  command→skill and skill→command
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
- `skills/workflow-repair/references/closure-round-template.md`
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
- same-version task-local closure artifacts are now the repair memory surface
- optional issue-history shadow output must not be treated as the primary v4
  decision path
- when no shadow file is written, the repair log should say `none` explicitly
  rather than leaving the field ambiguous
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
- `--auto` now explicitly allows current-task commit-scope confirmations that
  enumerate proposed commits or task artifacts when they still ask for
  `ok`/yes-style approval
- `--auto` now explicitly restricts unrecognized working-tree files to those that the
  prompt frames as part of the current repair task's commit scope
- `unrecognized working-tree files` are now explicitly defined instead of being
  inferred from git-specific shorthand
- `current repair-task artifacts` are now explicitly defined instead of being
  implied only by examples
- task-directory artifacts now qualify by directory membership plus explicit
  current-task scoping, while only out-of-directory files need current-run
  recorded-output proof
- independent scope proof now explicitly extends across all three allowed
  write-scope locations for the current repair run, not just the task
  directory
- `tie to this run's recorded outputs` is now explicitly defined in terms of
  repair-log evidence for changed, written, or output files
- repeated auto-close-out term definitions are now intentionally centralized in
  the main follow-through rules with shorter references elsewhere
- `--auto` now explicitly stops on mixed-scope commit prompts that include
  non-task working-tree files
- `--auto` now explicitly stops when commit-scope or repair-result wording
  would overstate the actual repair outcome
- `--auto` now explicitly stops when one-shot commit confirmation cannot be
  identified reliably
- `--auto` now explicitly uses `continue` to drive post-repair close-out
- `--auto` now explicitly falls back from command surface to same-session
  skill surface for both `continue` and `finish-work`
- `--auto` now explicitly stops when no finish-work surface is
  available
- `--auto` now explicitly stops when no continue surface is available
- `--auto` now explicitly stops when `continue` cannot prove whether the task
  advanced or closed safely
- `--auto` now explicitly caps same-task `continue` re-entry loops
- `--auto` now explicitly recognizes the case where `continue` itself closes
  the current repair task
- repeated findings now force broader closure or escalation
- same-pattern sweep behavior is still documented and logged
- contract-surface coverage and repeat-trigger checks are still documented in the plan/log artifacts
- repair-log timing now records continuation outcome without contradicting Step
  11 / Step 12 ordering
- `--auto` still stops instead of forcing finish-work when commit readiness or
  close-out safety is not satisfied
- persisted tests now include mixed-scope and misleading-result blocker
  scenarios for commit-scope confirmations
- persisted tests now include the case where prompt framing claims one outside-
  task working-tree path belongs to the current task scope but independent
  proof fails
- persisted tests now include the positive case where a workflow source file or
  current-run optional issue-history shadow file is outside the task directory but still
  independently provable as part of the current repair run
- persisted tests now include the positive case where task-directory files from
  an older run remain acceptable when the prompt still scopes them to the
  current task
- persisted tests now include the blocker case where a previous run's
  out-of-directory workflow file is listed again without current-run proof
- persisted tests now include `target_focus` plus misleading all-success
  close-out wording
- persisted tests now include the positive case where partial success/revert
  results may still continue when close-out wording stays honest
- persisted tests now include the blocker case where the same close-out run
  surfaces a second qualifying commit confirmation
- persisted tests now include the blocker case where task-directory files are
  listed without explicit current-task scoping
- persisted tests now include the positive `target_focus` case where the prompt
  honestly says `the focused repairs`
- persisted tests now split pure working-tree-file prompts into explicit
  continue-vs-stop cases
- persisted tests now include `target_focus` plus failed scope proof
- persisted tests now include an additional multi-cause blocker combination
  beyond mixed-scope plus misleading-result
- persisted tests now include the case where honest wording still fails because
  explicit current-task scoping is missing
- persisted tests now include report-side `design-debt` and `evidence-gap`
  findings that must not auto-enter adopted repair execution
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
- verify repair-side intake now treats report-side repair classification as the
  default anti-overrepair gate instead of assuming every finding is equally
  repair-ready
- verify repair-side examples include at least one report intake path for a
  validated `workflow-scan --agent` output
- verify `--auto` is documented as explicit, post-repair only, and blocked when
  the current task is not ready for commit/finish-work
- verify the paired `workflow-scan` diff is an actual compatibility adaptation
  when the repair-side contract changed, not just an unchanged carryover

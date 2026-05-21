# Improve workflow-repair auto close-out ok follow-through

## Goal

Strengthen `skills/workflow-repair` so `workflow-repair --auto` can continue
through the current repair task's normal close-out flow when Trellis asks for
task-scoped commit confirmation in the broader "confirm include/exclude + reply
ok" wording now used by this repository, instead of stopping as if the prompt
were too ambiguous.

## What I already know

- The current `workflow-repair` skill only allows auto-replying `ok` when it
  can identify a one-shot commit confirmation for the current repair task.
- A real repository close-out prompt now lists proposed commits, names
  unrecognized dirty files, states that the current repair task directory is in
  scope, and explicitly asks the user to reply `ok`.
- `skills/workflow-repair/tests/30-auto-stops-on-unreliable-commit-confirmation.md`
  currently encodes a conservative blocker for prompts that "look somewhat like
  commit confirmation".
- The requested change is repair-side close-out behavior only; it does not
  change the shared `workflow-scan-repair-v2` report schema.

## Assumptions

- The auto-confirmation expansion should stay limited to prompts that are still
  clearly about the current repair task's commit scope and that explicitly ask
  for a yes/confirm style reply.
- Unexpected prompts such as hook failures or unrelated confirmations must
  remain blockers.

## Requirements

- Update `workflow-repair` so `--auto` treats current-task commit-scope
  confirmation prompts that explicitly ask for `ok`/yes-style approval as
  eligible for the one-shot auto reply.
- Keep the auto-confirmation scope limited to the current repair task; do not
  allow broader or unrelated prompts to be auto-answered.
- Treat unrecognized dirty files as eligible only when the prompt explicitly
  frames them as part of the current repair task's commit scope; mixed-scope
  prompts that include non-task files must remain blockers.
- Define `unrecognized working-tree files` precisely enough that modified vs
  untracked paths are both covered without relying on git-specific shorthand.
- Expand independent scope proof beyond the task directory so the auto
  close-out path can recognize files from any of the three allowed write-scope
  locations when those files are provably produced by the current repair run.
- Treat commit-scope prompts whose wording would materially overstate the
  actual repair result as unreliable blockers rather than auto-confirming them.
- Formally define `current repair-task artifacts` so task-scoped artifact
  prompts are recognized consistently.
- Preserve blocker behavior for genuinely ambiguous prompts and non-commit
  interactive prompts.
- Reflect the behavior in skill tests, auxiliary templates, and repair-side
  spec wording.

## Acceptance Criteria

- [ ] Skill docs state that current-task commit-scope confirmation prompts may
      be auto-confirmed when they explicitly ask for `ok`/yes-style approval.
- [ ] Skill docs explicitly reject mixed-scope prompts that include non-task
      dirty files or otherwise cannot prove current-task-only scope.
- [ ] Skill docs explicitly reject commit-scope prompts whose wording would
      materially misstate the actual repair outcome.
- [ ] Skill docs define `unrecognized working-tree files` and remove ambiguity
      between prompt framing and independent scope proof.
- [ ] Skill docs define which write-scope locations may count as independently
      provable current-run outputs during auto close-out.
- [ ] Duplicate auto-close-out term definitions are reduced to a single
      canonical definition area plus stable references elsewhere.
- [ ] A persisted test scenario covers the real close-out prompt shape as a
      success case instead of a blocker.
- [ ] A persisted test scenario still covers truly unreliable commit
      identification as a blocker.
- [ ] Persisted negative scenarios cover mixed-scope prompts and misleading
      repair-result wording.
- [ ] Persisted negative scenarios cover a prompt that frames one outside-task
      path as in-scope even though the path cannot be independently proved.
- [ ] Persisted scenarios cover a positive case where an in-scope workflow file
      or current-run issue-history file is outside the task directory but still
      independently provable.
- [ ] Persisted scenarios cover `target_focus` plus misleading all-success
      close-out wording.
- [ ] Persisted scenarios cover partial success/revert outcomes with honest
      close-out wording that should still allow auto follow-through.
- [ ] Persisted scenarios cover a previous run's out-of-directory workflow file
      being listed again without current-run proof and correctly blocking.
- [ ] Rules explicitly stop if the same close-out run surfaces a second
      qualifying commit confirmation after one auto reply.
- [ ] Error Handling wording matches Step 12.8 blocker categories, including
      repeated confirmation inside the same close-out run.
- [ ] Persisted scenarios cover a close-out prompt that enumerates only
      unrecognized working-tree files with no task artifacts or proposed commit
      batches.
- [ ] Skill docs define `same close-out run` precisely enough to distinguish
      same-run confirmation repeats from later resumed runs.
- [ ] Reverted files are excluded from the independently provable output set.
- [ ] Skill docs provide minimum-acceptable and insufficient current-task
      scoping wording examples.
- [ ] Persisted scenarios cover task-directory files with insufficient task
      scoping, honest `the focused repairs` wording under `target_focus`, and
      split pure working-tree-file continue-vs-stop cases.
- [ ] Skill docs explain that multi-cause blockers should report all triggered
      causes in the blocker reason.
- [ ] Persisted scenarios cover a multi-cause blocker prompt and verify that
      all triggered causes are reported.
- [ ] Persisted scenarios cover `target_focus` plus scope-proof failure and
      honest wording that still blocks because explicit current-task scoping is
      missing.
- [ ] Skill docs clarify that accepted scoping examples are illustrative, not
      exhaustive, and that honest partial-result wording can still fail if
      explicit current-task scoping is missing.
- [ ] Repair-side spec and reference wording match the new safe detection
      boundary.

## Definition of Done

- Relevant skill docs and spec docs updated
- `./scripts/validate-skills.sh` passes
- Diff reviewed for accidental scan/repair shared-contract drift

## Out of Scope

- Changing `workflow-scan` report schema
- Expanding `workflow-repair` to answer prompts unrelated to current-task
  commit confirmation
- Changing Trellis core close-out commands or task scripts

## Technical Notes

- Primary files likely involved:
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-repair/references/correction-plan-template.md`
  - `skills/workflow-repair/references/repair-log-template.md`
  - `skills/workflow-repair/tests/30-auto-stops-on-unreliable-commit-confirmation.md`
  - `skills/workflow-repair/tests/35-auto-stops-when-commit-scope-includes-non-task-files.md`
  - `skills/workflow-repair/tests/36-auto-stops-on-misleading-commit-scope-result-claim.md`
  - `skills/workflow-repair/tests/08-auto-follow-through-success.md`
  - `.trellis/spec/skills/workflow-repair.md`

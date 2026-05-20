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
- the skill still reads all `tmp/workflow-issues/` history docs and writes one
  new issue-history file per run
- explicit repair authorization and analysis-only behavior remain distinct
- repeated findings now force broader closure or escalation
- same-pattern sweep behavior is still documented and logged
- contract-surface coverage and repeat-trigger checks are still documented in the plan/log artifacts
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
- verify the paired `workflow-scan` diff is an actual compatibility adaptation
  when the repair-side contract changed, not just an unchanged carryover

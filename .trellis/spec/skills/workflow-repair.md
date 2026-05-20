# workflow-repair Skill Specification

> Behavioral contract for the installable skill `skills/workflow-repair/`.

---

## Purpose

`workflow-repair` is the repair-side half of the installable
`workflow-scan` / `workflow-repair` pair.

It consumes `WORKFLOW_QUESTIONS.md`, re-checks each reported issue against the
temp project and source workflow, then repairs only the workflow product source
under `docs/workflows/新项目开发工作流/`.

---

## Scope Boundary

`workflow-repair` must preserve all of the following:

1. File modification scope is locked to `docs/workflows/新项目开发工作流/`.
2. Task-local repair artifacts may be written, but they are never deleted as
   part of the run.
3. The temp project remains the primary truth source for whether a reported
   issue exists.
4. The skill runs inline in the current CLI session. Do not route through
   agents or sub-agents.
5. Trellis-native defects must be patched from within the workflow directory so
   the installer can repair future target projects.

---

## Required Behaviors

### 1. Report and Temp Project Resolution

The skill must:

- resolve `WORKFLOW_QUESTIONS.md` from `/tmp/trellis-{VERSION}-2/` when the
  user did not supply a path
- validate the shared `workflow-scan-repair-v1` protocol
- resolve the temp project from the report before judging findings
- stop instead of guessing when report/source/temp context does not line up

### 2. Verification Discipline

The skill must treat every scan finding as a hypothesis.

Before adoption, it must:

- inspect the referenced temp-project artifact when available
- inspect the suspected source location
- cross-check relevant declarations such as `workflow_assets.py`
- identify a concrete root-cause class instead of stopping at the visible symptom
- prefer `ignored`, `blocked`, or `manual-decision` over unsafe auto-adoption

If a finding appears to be a repeat of an earlier repair attempt, the skill must
escalate rather than reapply the same narrow patch blindly.

### 3. Authorization Discipline

The skill must distinguish:

- explicit repair requests, which count as standing authorization after the
  correction plan is echoed
- analysis-only requests, which must stop after the correction plan until the
  user confirms execution

### 4. Variant Discipline

For every confirmed safe issue, the skill must search only within
`docs/workflows/新项目开发工作流/` for same-pattern or same-root-cause siblings.

It may repair those siblings in the same run only when:

- the root cause is materially the same
- the repair remains low-risk
- the scope stays inside the workflow directory

The sweep result must be recorded in both the correction plan and the repair
log, even when no sibling fix was needed.

### 5. Contract-Surface Discipline

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

### 6. Coupled Artifact Discipline

The skill must keep all repair-side protocol surfaces aligned:

- `skills/workflow-repair/SKILL.md`
- `skills/workflow-repair/references/correction-plan-template.md`
- `skills/workflow-repair/references/repair-log-template.md`
- the shared scan report template used by `workflow-scan`

---

## Review Checklist

When editing `skills/workflow-repair/`, confirm all of the following:

- modification scope is still locked to `docs/workflows/新项目开发工作流/`
- the skill still forbids agent/sub-agent execution
- the skill still verifies against the temp project, not only source files
- explicit repair authorization and analysis-only behavior remain distinct
- repeated findings now force broader closure or escalation
- same-pattern sweep behavior is still documented and logged
- contract-surface coverage and repeat-trigger checks are still documented in the plan/log artifacts
- any protocol change is mirrored in `workflow-scan` and the shared template in
  the same change

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

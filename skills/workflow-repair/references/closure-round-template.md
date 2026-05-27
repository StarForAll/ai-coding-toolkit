# Closure Round Template

This document defines the per-round closure artifact that `workflow-repair`
writes inside the current repair task when `v4` bounded closure verification is
executed.

---

## Document Purpose

The closure-round artifact captures fresh-fixture verification truth after
source-side repair changes. It is the same-version convergence memory surface
for the current repair task.

Unlike the high-level repair log:

- it records round/scenario/family-level detail
- it is task-local only
- it must not be reused as a later cross-version repair-memory source

---

## Document Location

Write one file per closure round to the dedicated current repair task
directory:

`closure-round-<N>.md`

Rules:

- `<N>` is a positive integer starting from `1`
- one file per round, not per scenario
- when a round is re-run after rollback, write a new round file rather than
  mutating an older round into a different outcome

---

## Document Structure

### Header

```markdown
---
closure-round-version: 1
protocol: workflow-scan-repair-v4
repair-task: {absolute or repo-relative path to the dedicated repair task directory}
source-report: {absolute path to WORKFLOW_QUESTIONS.md}
base-workflow-version: {workflow version at the start of this repair run}
round: {N}
created-at: {ISO 8601}
total-scenarios: {N}
total-findings: {N}
in-scope-findings: {N}
new-family-findings: {N}
round-outcome: clean | absorbed | blocked | needs-audit | reverted
---

# Workflow Repair Closure Round {N}

## Round Summary

- Repair Task: {repair-task}
- Source Report: {source-report}
- Base Workflow Version: {base-workflow-version}
- Round: {N}
- Scenario Count: {total-scenarios}
- Total Findings: {total-findings}
- In-Scope Findings: {in-scope-findings}
- New-Family Findings: {new-family-findings}
- Round Outcome: {round-outcome}
```

### Scenario Section

```markdown
## Scenarios

### {scenario-id}

- Fixture Root: {absolute temp fixture path}
- Profile: {outsourcing | personal}
- CLI Types: {claude,opencode,codex}
- Status: passed | failed | blocked
- Commands Run:
  - {command 1}
  - {command 2}
- Notes: {brief explanation or `none`}
```

### Closure Finding Entry

```markdown
---

### CR{round}-F{nn}: {title}

- **Issue Family ID**: {stable family identifier}
- **Parent Scan Finding**: {WS-NNN | none}
- **Scenario ID**: {scenario-id}
- **In Scope**: yes | no
- **Disposition**: absorbed | deferred | blocked
- **Origin**: trellis-native | workflow-source
- **Evidence Layer**: generated-target-baseline | generated-target-installed | generated-target-runtime
- **Description**: {what was observed in closure}
- **Evidence**:
  - {observation 1}
  - {observation 2}
- **Why In Scope**: {reason or `not-applicable`}
- **Why Not Auto-Absorbed**: {reason or `not-applicable`}
```

### Round Follow-Up

```markdown
## Follow-Up

- Round Action: absorb-next | stop-for-new-family | stop-for-non-convergence | stop-for-invalid-state | clean
- Rollback Performed: yes | no
- Rollback Scope: current-round-only | none
- Next Step: {brief instruction}
```

---

## Rules

1. Every closure round must write one artifact, even when no new findings are
   discovered.
2. `base-workflow-version` must match the report version and the current source
   workflow version for the duration of the run.
3. Every closure finding must record whether it is in scope for automatic
   absorption.
4. If any new in-scope finding remains unresolved, the overall repair run must
   not close out or bump the workflow version.
5. Findings from a new family must stop automatic progression of the current
   repair batch.
6. Use `round-outcome: blocked` when fixture creation, command execution,
   invalid embedded state, or another execution blocker prevents a reliable
   closure judgment for the round.
7. Use `round-outcome: needs-audit` when:
   - closure discovers a new family and the current batch must stop for a
     broader decision, or
   - same-family non-convergence exceeds the bounded absorb rounds, or
   - broader contract-surface ambiguity requires audit rather than another
     routine absorb round.
8. Use `round-outcome: reverted` when closure-added repairs for this round were
   attempted and then rolled back.
9. These files are task-local same-version execution artifacts, not reusable
   cross-version repair memory.

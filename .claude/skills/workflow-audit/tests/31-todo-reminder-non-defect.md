# 31 Todo Reminder Non-defect

## Purpose

Verify that `workflow-audit` does not misclassify the workflow-created root
`todo.txt` reminder artifact as a managed-surface defect by default when the
artifact is documented as non-gating and low-stakes.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/` and tell me whether the workflow-created
> root `todo.txt` means the install flow is over-managing the target project.

## Expected Mode

Lightweight static mode unless Step 2 findings prove runtime validation is
required for a specific contradictory claim.

## Expected Key Behaviors

- treat `todo.txt` as a hypothesis, not a defect
- check whether the artifact is documented as a low-stakes non-gating reminder
- if no stronger contradictory evidence exists, classify it as contextual output
  or false alarm rather than a confirmed issue
- do not let the artifact's presence alone override stronger carrier-boundary
  evidence

## Must Not

- must not classify `todo.txt` as a confirmed issue solely because it exists
- must not treat `todo.txt` as equivalent to hidden-directory carriers, command
  copies, or routing blocks
- must not generate a cleanup recommendation for `todo.txt` without stronger
  contradictory evidence

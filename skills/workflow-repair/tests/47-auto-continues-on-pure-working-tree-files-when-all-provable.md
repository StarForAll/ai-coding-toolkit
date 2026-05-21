# 47 Auto Continues On Pure Working-Tree Files When All Provable

## Purpose

Verify that `workflow-repair --auto` may continue when a close-out
confirmation enumerates only unrecognized working-tree files and every one of
them is otherwise eligible under the normal proof rules.

## Input

User input:

> Run `/workflow-repair --auto`. Repairs succeed. A later close-out confirmation enumerates only unrecognized working-tree files, without listing task artifacts or proposed commit batches. Every listed file is either a properly scoped task-directory artifact or an out-of-directory file that the current run can independently prove from its remaining write-scope outputs.

## Expected Mode

Auto follow-through allowed because every listed working-tree file is eligible.

## Expected Key Behaviors

- evaluate the pure working-tree-file prompt with the same scope and proof rules
  used elsewhere
- continue even though no task artifacts or proposed commit batches are present
- require every listed file to pass the normal eligibility checks before
  replying `ok`

## Must Not

- must not require task artifacts or proposed commit batches as a prerequisite
  for eligibility
- must not invent extra scope requirements for pure working-tree-file prompts
- must not bypass the normal proof gates for any listed file

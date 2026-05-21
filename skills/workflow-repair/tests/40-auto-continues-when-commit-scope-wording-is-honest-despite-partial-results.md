# 40 Auto Continues When Commit-Scope Wording Is Honest Despite Partial Results

## Purpose

Verify that `workflow-repair --auto` may continue when some attempted fixes
were reverted or otherwise did not succeed, as long as the later close-out
confirmation describes the commit scope honestly and does not imply all
attempted fixes were verified.

## Input

User input:

> Run `/workflow-repair --auto`. Multiple fixes enter execution. At least one fix succeeds, and at least one other attempted fix is reverted. A later close-out confirmation asks for `ok` while truthfully describing the commit scope as the current repair changes or remaining verified repair outputs, without claiming that all attempted fixes were verified.

## Expected Mode

Auto follow-through allowed after partial results because the commit-scope
wording stays honest.

## Expected Key Behaviors

- allow auto follow-through to continue when `total-succeeded > 0` and the
  prompt does not materially overstate the repair result
- distinguish honest scope wording from misleading all-success wording
- keep reverted or otherwise unsuccessful work visible enough that the close-out
  record remains truthful

## Must Not

- must not stop solely because some attempted fixes were reverted when the
  close-out wording remains honest
- must not reinterpret honest partial-result wording as a misleading-result
  blocker
- must not let the prompt imply every attempted fix was verified

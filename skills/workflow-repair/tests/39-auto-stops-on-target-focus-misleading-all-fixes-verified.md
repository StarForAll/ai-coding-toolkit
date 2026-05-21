# 39 Auto Stops On Target-Focus Misleading All-Fixes-Verified Claim

## Purpose

Verify that `workflow-repair --auto` stops when `target_focus` narrows the
executed repair scope but a later close-out confirmation falsely implies that
all fixes were verified.

## Input

User input:

> Run `/workflow-repair --auto --target_focus WS-002`. WS-002 is the only in-scope repair and it succeeds, while at least one out-of-focus finding remains unresolved. A later close-out confirmation asks for `ok` while describing the result as if all fixes were verified.

## Expected Mode

Auto follow-through blocked on misleading all-success wording under narrowed
`target_focus`.

## Expected Key Behaviors

- compare the narrowed execution scope against the prompt's broader success
  claim
- treat wording such as `all fixes verified` as materially misleading when
  out-of-focus findings remain unresolved
- stop and report the blocker instead of auto-confirming the misleading close-out

## Must Not

- must not reply `ok` to wording that collapses out-of-focus unresolved work
  into implicit success
- must not treat successful focused-scope repair as permission to overstate the
  full report status
- must not continue to finish-work after this misleading-result blocker

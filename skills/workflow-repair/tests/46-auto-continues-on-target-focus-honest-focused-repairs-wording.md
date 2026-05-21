# 46 Auto Continues On Target-Focus Honest Focused-Repairs Wording

## Purpose

Verify that `workflow-repair --auto` may continue under `target_focus` when the
close-out confirmation truthfully scopes the result to the focused repairs.

## Input

User input:

> Run `/workflow-repair --auto --target_focus WS-002`. WS-002 is the only in-scope repair and it succeeds, while at least one out-of-focus finding remains unresolved. A later close-out confirmation asks for `ok` while describing the commit scope as `the focused repairs`, without implying that out-of-focus findings were also fixed.

## Expected Mode

Auto follow-through allowed because the narrowed-scope wording stays honest.

## Expected Key Behaviors

- treat `the focused repairs` as an acceptable explicit current-task scope
  description in a `target_focus` run
- distinguish honest narrowed-scope wording from misleading all-success wording
- continue as long as the listed files also satisfy the normal path and proof
  rules

## Must Not

- must not reinterpret honest focused-scope wording as a misleading-result
  blocker
- must not require the prompt to claim that all report findings were fixed
- must not overstate out-of-focus findings as resolved

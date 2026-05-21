# 23 Target Focus With Out-Of-Focus High Severity

## Purpose

Verify that `workflow-repair --auto` may honor an explicit `target_focus`
narrowing while still surfacing any higher-severity out-of-focus findings in
the correction plan.

## Input

User input:

> Run `/workflow-repair --auto --target_focus WS-002`. WS-002 is safe to fix, while an out-of-focus WS-001 remains P0 and unresolved.

## Expected Mode

Target-focused repair with auto follow-through evaluated only against the
focused scope, but with visible disclosure of the out-of-focus higher-severity
finding.

## Expected Key Behaviors

- exclude out-of-focus findings from the close-out safety decision itself
- surface the out-of-focus higher-severity finding clearly in the correction
  plan so the narrowed scope is visible to the user
- avoid implying that the full report is clean when only the focused scope was
  repaired
- leave room for a later close-out blocker if commit-scope wording would imply
  the out-of-focus work was also verified

## Must Not

- must not silently suppress the out-of-focus higher-severity finding
- must not let auto close-out imply that every report finding was addressed
- must not widen execution beyond the explicit `target_focus` just because an
  out-of-focus finding is more severe

# 10 Retained Disabled Subagent Carrier Is Not A Finding

## Purpose

Verify that `workflow-scan` does not emit a workflow finding merely because a
retained subagent/helper carrier still exists on disk when the temp project's
installed workflow explicitly says that carrier is currently unavailable and
temporarily disabled.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where a retained subagent carrier path still exists on disk for compatibility, but the installed workflow docs and runtime rules explicitly say the carrier is currently disabled/unavailable, and another active carrier already handles the supported workflow path.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect the retained carrier together with the temp project's installed docs,
  runtime rules, and active carrier surfaces
- recognize that “present on disk but intentionally disabled” is not, by
  itself, a workflow defect
- omit that observation from the `### WS-NNN` finding set when no installed
  surface contradicts the disabled contract
- emit a finding only if another installed surface still routes users into the
  supposedly disabled carrier, still teaches its usage in installed workflow
  docs, or still invokes it from hooks/config/runtime-control surfaces

## Must Not

- must not classify the retained disabled carrier as `design-debt` solely
  because it still exists on disk
- must not escalate the disabled carrier into `confirmed-defect` without a
  separate contradiction from temp-project evidence
- must not treat “currently unavailable / temporarily disabled” as equivalent
  to “missing adaptation defect”

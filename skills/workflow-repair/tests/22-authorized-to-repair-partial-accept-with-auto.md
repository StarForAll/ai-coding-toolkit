# 22 Authorized-To-Repair Partial Accept With Auto

## Purpose

Verify that `workflow-repair --auto` may continue after partial acceptance even
when the initial authorization mode was already `authorized-to-repair`.

## Input

User input:

> Fix the validated workflow findings and run `/workflow-repair --auto`, but after the correction plan is shown I only want to accept a subset of the adopted fixes. The accepted fixes succeed, and the skipped items remain documented.

## Expected Mode

Authorized-to-repair run with partial acceptance and auto follow-through.

## Expected Key Behaviors

- preserve the initial `authorized-to-repair` mode
- allow the user to accept only part of the proposed adopted fixes
- continue auto follow-through only if the skipped/unresolved items remain
  documented clearly enough to avoid misleading the commit

## Must Not

- must not force all adopted fixes just because the initial authorization mode
  was `authorized-to-repair`
- must not hide skipped or unresolved items during auto close-out
- must not treat partial acceptance as equivalent to a fully clean repair

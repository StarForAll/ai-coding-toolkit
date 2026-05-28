# 12 Workflow-Owned Shared Skill Surface Is A Finding

## Purpose

Verify that `workflow-scan` does emit a workflow finding when a shared-carrier
surface is truly owned by the embedded workflow according to temp-project
evidence.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where a shared skill or
> reference file under `.agents/skills/` contains a concrete contradiction, and
> the temp project's `.trellis/workflow-installed.json`, workflow patch
> markers/watermarks, and installed workflow docs/runtime rules together show
> that the current workflow explicitly owns or patched that surface.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect the shared-surface file together with the temp project's
  `workflow-installed.json`, patch markers/watermarks, and installed
  workflow docs/runtime rules
- recognize that the ownership gate is satisfied because temp-project evidence
  shows current workflow ownership of the surface
- emit a `### WS-NNN` finding instead of omitting the observation
- classify the finding as `workflow-source`
- when the contradiction is concrete and current, classify the finding as
  `confirmed-defect`

## Must Not

- must not drop the observation merely because the file still lives under a
  shared carrier directory
- must not downgrade a temp-project-proven owned surface to non-actionable
  context

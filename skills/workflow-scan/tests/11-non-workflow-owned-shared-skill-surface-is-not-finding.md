# 11 Non-Workflow-Owned Shared Skill Surface Is Not A Finding

## Purpose

Verify that `workflow-scan` does not emit a workflow defect merely because a
shared skill or reference file lives under an in-scope carrier such as
`.agents/skills/`.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where a shared baseline
> skill under `.agents/skills/` still contains helper-agent guidance, but the
> temp project's `.trellis/workflow-installed.json`, patch markers, and
> installed workflow docs/runtime rules do not show that the current workflow
> owns, patches, or routes through that skill surface.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect the shared-surface file together with the temp project's
  `workflow-installed.json`, any workflow patch markers/watermarks, and
  installed workflow docs/runtime rules
- recognize that shared-carrier placement alone is not ownership proof
- omit that observation from the `### WS-NNN` finding set when temp-project
  evidence does not show current workflow ownership of the surface
- allow escalation only when the temp project shows that the workflow
  explicitly claimed, patched, or actively routed through that same surface

## Must Not

- must not emit a `confirmed-defect` solely because the file exists under
  `.agents/skills/` or another in-scope shared carrier
- must not infer `workflow-source` ownership from carrier location alone
- must not require source-repo files as a prerequisite for deciding whether the
  shared surface belongs to the embedded workflow

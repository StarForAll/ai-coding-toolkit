# 14 Codex Secondary Skills Empty Is Not A Finding

## Purpose

Verify that `workflow-scan` does not emit a workflow finding merely because
`.codex/skills/` is empty while the temp project's active Codex workflow
skills live under `.agents/skills/`.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where
> `.trellis/workflow-installed.json` lists patched Codex skills, `.agents/skills/`
> contains the active `trellis-start` / `trellis-continue` /
> `trellis-finish-work` carriers, and `.codex/skills/` exists but is empty.
> The installed Codex docs describe `.agents/skills/` as the shared workflow
> primary carrier and `.codex/skills/` as a secondary carrier for Codex-local
> extras only.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect `.trellis/workflow-installed.json`, `.agents/skills/`, `.codex/skills/`,
  and installed Codex carrier docs/runtime rules together
- recognize that shared workflow skills may validly live only under
  `.agents/skills/`
- recognize that an empty `.codex/skills/` directory is not a defect when no
  installed surface claims a workflow-owned Codex-specific skill should live
  there
- omit this observation from the `### WS-NNN` finding set unless the temp
  project shows a separate contradiction

## Must Not

- must not classify an empty `.codex/skills/` directory as `confirmed-defect`
- must not classify missing shared workflow skills under `.codex/skills/` as
  `design-debt` when `.agents/skills/` already satisfies the active contract
- must not infer a missing Codex workflow surface from directory emptiness
  alone

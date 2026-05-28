# 16 Disabled Command Removal Without Marker Is Not A Finding

## Purpose

Verify that `workflow-scan` does not emit a workflow finding merely because an
intentionally disabled command or skill surface has been removed from the
active embedded workflow without leaving a separate disable marker file.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where
> `.trellis/workflow-installed.json` lists `disabled_commands: ["parallel"]`,
> installed workflow docs say `parallel/worktree` is intentionally disabled,
> and no active `parallel` command/skill file remains on disk because the
> installer removed it from the active surface.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect the install record, installed docs/runtime rules, and active command
  or skill surfaces together
- recognize that active absence is the expected disabled state for `parallel`
  under the current embedded workflow contract
- omit this observation from the `### WS-NNN` finding set unless another
  installed surface explicitly requires a retained active marker/stub

## Must Not

- must not classify missing active `parallel` files as `confirmed-defect`
- must not require a `.disabled` marker or placeholder command/skill file when
  the temp project's installed workflow contract does not require one
- must not treat successful removal from the active surface as a
  post-install-artifact defect

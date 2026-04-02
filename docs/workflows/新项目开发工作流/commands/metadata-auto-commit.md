# Deprecated: Metadata Auto-Commit Note

`metadata-auto-commit` no longer acts as a standalone workflow page or command.

The final close-out rules now live in:

- `commands/delivery.md`
- `工作流总纲.md`
- `命令映射.md`

Current rule:

- archive remains an explicit step
- `record-session` is used only for the **final close-out of the current completed task**
- `record-session` should run through the workflow helper

This file is kept temporarily as a migration note to avoid stale references during the transition.

Removal condition:

- Delete this file once old references to `metadata-auto-commit` have been cleared from workflow docs, install/upgrade compatibility paths, and downstream project copies.

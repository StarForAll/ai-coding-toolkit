# remove .current-task legacy mechanism

## Goal

Remove repo-local `.trellis/.current-task` legacy residue from the current
Trellis implementation in this repository, without changing the live
session-scoped runtime model or degraded active-task fallback behavior.

## In Scope

- remove code-level constants / exports that still present `.current-task` as a
  current mechanism
- update tests that still seed `.current-task` even though active task now
  resolves through `.trellis/.runtime/sessions/`
- update repo-local docs or comments that would mislead maintainers into
  treating `.current-task` as part of the live runtime contract

## Out Of Scope

- changing backup retention policy
- changing workflow product files under `docs/workflows/新项目开发工作流/`
- changing the session-scoped active task runtime model
- changing degraded mode semantics

## Acceptance Criteria

- no current runtime or test path depends on `.trellis/.current-task`
- code and docs describe session-scoped runtime as the active-task truth source
- targeted validation for touched runtime/test surfaces passes

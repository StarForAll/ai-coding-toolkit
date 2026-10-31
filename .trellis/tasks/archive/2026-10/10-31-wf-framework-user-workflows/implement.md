# Implementation Plan: wf User Workflow Design Contract

## Scope

Update only:

- `docs/workflows/wf-framework-design.md`
- `docs/workflows/wf-framework-design.index.md`

Do not edit the old Trellis-embedded workflow design/implementation documents, scripts, host integrations, or runtime assets. Preserve pre-existing modifications in both target documents and unrelated untracked files.

## Ordered Work

1. Re-read the current target docs and compare the working-tree diff with the task-start baseline. Retain the existing user changes about exceptional archive and abandoned-change disposition.
2. Add the design/evolution tone in §1.1: capability-gap evidence, complete core behavior, prefer existing mechanisms, lifecycle cost, and a stop condition; do not weaken complex-review requirements.
3. Define user workflow ownership and the bounded declarative contract. Separate project-owned workflow definitions from framework release assets; distinguish definitions from run instances and ordinary task records.
4. Reconcile §1.3 session binding, task pointer, and switch semantics with the immutable one-object-per-session rule. Reconcile §2.2 to allow multiple open sessions but forbid concurrent shared-worktree writers.
5. Reconcile task planning/entry, pause/handoff, task records, consistency/recovery, asset ownership, and upgrade behavior with the session binding and writer-lease contracts. Keep task status and task approval authoritative in ordinary task records; avoid a second task lifecycle.
6. Add the no-identity, writer-held, explicit handoff, stale-owner, compression/new-session, direct-write limitation, and shared-file invalidation acceptance scenarios to §8.2.
7. Update the unique-definition index: add definitions and all actual consumers, update consumed entries' lexical and semantic columns, and preserve the existing table structure/review-state contract.
8. Enumerate every new cross-section `§` reference and verify both lexical-candidate and semantic-consumer back-scans per `.trellis/spec/docs/wf-design-revision-gate.md`.

## Validation

Run:

```bash
/softwares/python/bin/python3 scripts/validate-wf-design.py
git diff --check
```

Review the full target-document diffs against the observed pre-existing user changes. Confirm the final working tree still contains only the task's intended documentation changes plus pre-existing work; do not stage or commit.

## Stop Gate

Present the revised design, trade-offs, unresolved technical limits, and validation evidence for the user's manual review. Keep this Trellis task in `planning`; do not run `task.py start`, `finish`, `archive`, commit, or another close-out operation until the user explicitly approves the design.

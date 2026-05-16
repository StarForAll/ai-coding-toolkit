# PRD: Settle Trellis 0.5.16 upgrade residue

## Background

The repository has already partially absorbed the Trellis `0.5.16` upgrade:

- live tracked files already include:
  - `.claude/hooks/session-start.py`
  - `.qoder/hooks/session-start.py`
  - `.kiro/skills/trellis-meta/references/customize-local/change-workflow.md`
  - `.trellis/.version`
  - `.trellis/.template-hashes.json`
- 26 `.new` files remain as unresolved upgrade candidates

Audit of the live repo against `/tmp/trellis-0.5.16` showed that most `.new`
files are upstream baselines that would regress this repository's actual live
Trellis contract if adopted blindly.

## Problem

The upgrade is not fully settled because:

1. only the Kiro copy of `change-workflow.md` was updated; the parallel shared
   / Claude / OpenCode / Qoder copies are still pending as `.new`
2. 22 `.new` files remain on disk even though they should be explicitly
   discarded
3. `.trellis/.template-hashes.json` and the template-hash regression test must
   match the final retained live files after cleanup

## Goals

1. Adopt the intended `change-workflow.md` route-table wording to the remaining
   live copies
2. Delete `.new` candidates that should not be merged into the live repo
3. Keep the current live Trellis runtime contract intact:
   - preserve stale-pointer handling
   - preserve degraded active-task fallback
   - preserve Codex inline-mode guardrails
   - preserve richer `trellis-research` tool routing and `Active task:` fallback
4. Reconcile hash metadata and regression tests with the final on-disk state
5. Run focused regression tests covering runtime/task/hash/workflow contracts

## Non-Goals

- Do not switch the repo to the product source tree under
  `docs/workflows/新项目开发工作流/`
- Do not weaken or rewrite the current live runtime semantics in
  `.trellis/scripts/**`, hooks, or platform carriers just to match upstream
- Do not introduce sub-agent execution in this Codex inline session
- Do not change unrelated active tasks or task archives

## Scope

### In Scope

- `change-workflow.md` live/reference copies under:
  - `.agents/skills/trellis-meta/...`
  - `.claude/skills/trellis-meta/...`
  - `.opencode/skills/trellis-meta/...`
  - `.qoder/skills/trellis-meta/...`
- deletion of the 22 rejected `.new` files
- `.trellis/.template-hashes.json`
- `.trellis/scripts/common/tests/test_template_hash_semantics.py`
- focused regression tests

### Out of Scope

- `.new` proposals that would alter live runtime behavior beyond the approved
  `change-workflow.md` wording fix
- fixes to the broader active-task session identity model beyond what is needed
  to complete this cleanup task

## Acceptance Criteria

- [ ] The four pending live `change-workflow.md` copies use the same approved
      wording already present in the Kiro live file
- [ ] All 22 rejected `.new` files are removed
- [ ] No rejected `.new` content is merged into live runtime files
- [ ] `.trellis/.template-hashes.json` is consistent with the final live files
- [ ] `test_template_hash_semantics.py` reflects the final overlay list
- [ ] Focused Trellis regression tests pass

## Implementation Notes

- Treat `/tmp/trellis-0.5.16` as the upstream baseline only, not as the source
  of truth for this repository's live contract
- Prefer keeping current live files whenever a `.new` would remove repository
  specific safeguards or richer tool access

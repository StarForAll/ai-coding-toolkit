# remove stale workflow helper residue

## Goal

Close the confirmed workflow-maintenance gap where `upgrade-compat.py` does not
detect or clean obsolete helper scripts that were removed from the current
managed helper set, so old embedded target projects cannot silently keep stale
workflow helper files after upgrade.

## What I already know

- The current workflow source no longer treats `record-session-helper.py` or
  `metadata-autocommit-guard.py` as managed helper scripts.
- Fresh install only deploys the helper names in `HELPER_SCRIPTS`, and uninstall
  removes the whole `.trellis/scripts/workflow/` directory.
- `upgrade-compat.py --check` currently validates only expected helper names for
  presence/content drift; it does not flag extra obsolete helper files.
- `upgrade-compat.py --merge` currently re-deploys expected helper names, but it
  does not remove obsolete helper files left by older workflow versions.
- Existing installer tests already cover helper missing/content drift cases, so
  the residue fix should extend the same test surface.

## Assumptions (temporary)

- The residue cleanup target is limited to obsolete files in
  `.trellis/scripts/workflow/` that were previously workflow-managed helper
  scripts but are no longer in the current helper set.
- This task should not change fresh install semantics or Trellis native close-out
  behavior.
- Historical archives and backup directories are not cleanup targets in this
  task.

## Open Questions

- None blocking. The current managed helper set in `workflow_assets.py` is the
  source of truth.

## Requirements (evolving)

- `upgrade-compat.py --check` must detect obsolete helper-script residue in
  `.trellis/scripts/workflow/`.
- `upgrade-compat.py --merge` must remove those obsolete helper files.
- Detection/cleanup must be derived from shared workflow asset definitions rather
  than ad-hoc duplicated lists.
- Tests must prove both the failing `--check` behavior and the cleanup behavior.
- Maintainer-facing docs that describe upgrade verification scope must mention
  obsolete helper residue handling if the behavior changes materially.

## Acceptance Criteria (evolving)

- [ ] A target project containing obsolete workflow helper files fails
      `upgrade-compat.py --check` with explicit residue diagnostics.
- [ ] Running `upgrade-compat.py --merge` on that target removes the obsolete
      helper files and preserves current managed helpers.
- [ ] Relevant installer tests cover both detection and cleanup.
- [ ] Any changed maintainer docs stay aligned with the script behavior.

## Definition of Done (team quality bar)

- Tests added/updated where needed
- Relevant validation commands run with results recorded truthfully
- Docs/specs updated where behavior changed

## Out of Scope (explicit)

- Cleaning historical references under `.trellis/tasks/archive/**`,
  `.trellis/workspace/**`, or `.trellis/.backup-*/**`
- Changing install-time close-out contracts
- Adding runtime `/tmp` audit coverage beyond the targeted script/test behavior

## Technical Notes

- Primary code paths:
  `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`,
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py`,
  `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- Primary spec/docs context:
  `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`,
  `.trellis/spec/scripts/workflow-command-doc-contracts.md`,
  `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- Static audit finding to implement:
  old target projects may retain stale helper files because upgrade checks only
  inspect expected helper names.

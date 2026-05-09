# Current State

- Current managed helper set is defined in
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py` via
  `HELPER_SCRIPTS`.
- `upgrade-compat.py --check` calls `detect_shared_script_conflicts()` and only
  iterates the expected helper names from that managed set.
- `upgrade-compat.py --merge` calls `deploy_scripts()` and only re-copies the
  expected helper names from the same managed set.
- `uninstall-workflow.py` deletes the entire
  `.trellis/scripts/workflow/` directory, so the stale-helper problem is limited
  to upgrade paths rather than full uninstall paths.
- Existing tests already verify missing-helper and drifted-helper detection, but
  there is no coverage for obsolete extra helper files.

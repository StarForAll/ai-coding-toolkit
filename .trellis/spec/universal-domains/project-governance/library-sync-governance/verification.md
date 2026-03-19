# Verification

Check the following:

* each reusable asset is registered in `manifest.yaml`
* each imported target-project asset is represented in `.trellis/library-lock.yaml`
* each imported `target_path` in `.trellis/library-lock.yaml` stays inside the managed `.trellis/` tree
* downstream sync respects `upstream_sync` and `local_state`
* `pinned` assets only update when an explicit override flag is used
* merge-mode analysis reports drift for already imported assets unless the caller explicitly disables that scan
* proposal generation outputs a reviewable report before patch application
* apply operations are restricted to approved proposals and whitelisted target paths
* source-library validation passes after applying any accepted upstream contribution

Failure indicators:

* source-library assets exist on disk but are missing from `manifest.yaml`
* target-project assets are overwritten despite `modified`, `diverged`, `pinned`, or `local-only` state
* an imported asset path escapes `.trellis/` without being surfaced as a migration or structural conflict
* upstream proposal patches include project-private or structure-changing edits without escalation
* apply tooling modifies paths outside the approved asset scope

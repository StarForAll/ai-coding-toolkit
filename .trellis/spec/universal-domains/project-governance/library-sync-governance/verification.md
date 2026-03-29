# Verification

Check the following:

* each reusable asset is registered in `manifest.yaml`
* each imported target-project asset is represented in `.trellis/library-lock.yaml`
* downstream sync respects `upstream_sync` and `local_state`
* proposal generation outputs a reviewable report before patch application
* apply operations are restricted to approved proposals and whitelisted target paths
* source-library validation passes after applying any accepted upstream contribution

Failure indicators:

* source-library assets exist on disk but are missing from `manifest.yaml`
* target-project assets are overwritten despite `modified`, `diverged`, `pinned`, or `local-only` state
* upstream proposal patches include project-private or structure-changing edits without escalation
* apply tooling modifies paths outside the approved asset scope

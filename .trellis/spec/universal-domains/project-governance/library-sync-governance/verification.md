# Verification

Check the following:

* each reusable asset is registered in `manifest.yaml`
* each imported target-project asset is represented in `.trellis/library-lock.yaml`
* downstream sync respects `upstream_sync` and `local_state`
* proposal generation outputs a reviewable report before patch application
* apply operations are restricted to approved proposals and whitelisted target paths
* source-library validation passes after applying any accepted upstream contribution
* cross-platform Skills/Agents differences are not reported as drift
* `.trellis/.template-hashes.json` has not been manually modified, unless a recovery explicitly backfilled missing managed keys or deleted stale managed keys using a matching fresh Trellis baseline
* when the managed template set changed, `.trellis/scripts/common/tests/test_template_hash_semantics.py` and any related contract tests were updated in the same change so removed paths are no longer indexed from recorded hashes
* at most one `.trellis/.backup-*` directory is retained

Failure indicators:

* source-library assets exist on disk but are missing from `manifest.yaml`
* target-project assets are overwritten despite `modified`, `diverged`, `pinned`, or `local-only` state
* upstream proposal patches include project-private or structure-changing edits without escalation
* apply tooling modifies paths outside the approved asset scope
* drift analysis incorrectly flags cross-platform Skills/Agents format differences as anomalies
* `.trellis/.template-hashes.json` has been manually edited outside the narrow baseline-matched missing-key backfill / stale-key deletion recovery paths, or contains hashes taken from current local customized file contents
* removed managed paths are still referenced by repo-local contract tests that index `recorded[...]` template hashes, or wording assertions still expect pre-reconciliation live text
* more than one `.trellis/.backup-*` directory exists at the same time

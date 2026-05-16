# Normative Rules

* `trellis-library/manifest.yaml` must be treated as the source-library registry for reusable assets, relations, and packs.
* A target project must track imported assets in `.trellis/library-lock.yaml`.
* The minimum import unit for complex reusable specs must be the concern directory, not an arbitrary single child file.
* Source-library assets must remain split and atomic in the source repository; compiled or merged views may exist only as derived outputs.
* Downstream sync must only auto-apply to assets whose `upstream_sync` state is `follow-upstream` and whose `local_state` is `clean`, unless an explicit recovery path is defined for `missing`.
* Assets marked `pinned`, `local-only`, `modified`, or `diverged` must not be silently overwritten by downstream sync.
* Target-project improvements must not flow back automatically into `trellis-library`.
* Upstream contribution must be proposal-driven and manually selected.
* Proposal generation must reject or explicitly warn on project-private, platform-crossing, technology-crossing, or structure-changing changes.
* `apply-library-sync` must only apply approved proposals or patches; it must not decide what should be contributed upstream.
* `apply-library-sync` must only write to whitelisted paths inside `trellis-library`.
* After any source-library change produced by sync tooling, `validate-library-sync` must run and pass before the change is considered valid.

### Drift Analysis and Operational Hygiene

* Cross-platform differences in Skills and Agents deployments (`.claude/`, `.opencode/`, `.codex/`, `.kiro/`, `.qoder/`, `.agents/`) are design-expected due to different formats and conventions per platform; they must not be flagged as drift.
* Only the latest `.trellis/.backup-*` directory must be retained; older backups must be cleaned up.
* `.trellis/.template-hashes.json` is a drift detector that records hashes of managed deployment files; it must not be manually edited in ordinary work.
* The only allowed recovery paths are:
  - backfilling missing managed keys with hash values copied from a matching fresh Trellis baseline for the same version and platform set when historical drift omitted those keys
  - deleting stale managed keys when the same matching fresh Trellis baseline no longer tracks those paths
* Recovery must never write hashes computed from the current local customized file contents into `.trellis/.template-hashes.json`; doing so would hide local modifications from future `trellis update`.
* When the managed template set changes, the repo-local regression tests that index recorded template hashes must be updated in the same change. In particular, `.trellis/scripts/common/tests/test_template_hash_semantics.py` must not keep removed paths in `overlays`, and any live wording assertions that were updated as part of the same template reconciliation must be kept aligned in the relevant contract tests.
* Hash mismatches reported by `.trellis/.template-hashes.json` are the detector working correctly, not the hash file itself being drifted.

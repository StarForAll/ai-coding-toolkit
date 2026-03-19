# Normative Rules

* `trellis-library/manifest.yaml` must be treated as the source-library registry for reusable assets, relations, and packs.
* A target project must track imported assets in `.trellis/library-lock.yaml`.
* Imported `target_path` values recorded in `.trellis/library-lock.yaml` must stay inside the managed `.trellis/` tree; moving assets outside that boundary requires manual migration review.
* The minimum import unit for complex reusable specs must be the concern directory, not an arbitrary single child file.
* Source-library assets must remain split and atomic in the source repository; compiled or merged views may exist only as derived outputs.
* Downstream sync must only auto-apply to assets whose `upstream_sync` state is `follow-upstream` and whose `local_state` is `clean`, unless an explicit recovery path is defined for `missing`.
* Assets marked `pinned`, `local-only`, `modified`, or `diverged` must not be silently overwritten by downstream sync.
* A `pinned` asset may only be updated when the caller passes an explicit override flag for that sync run; the default path must remain non-destructive.
* Target-project improvements must not flow back automatically into `trellis-library`.
* Upstream contribution must be proposal-driven and manually selected.
* Proposal generation must reject or explicitly warn on project-private, platform-crossing, technology-crossing, or structure-changing changes.
* `apply-library-sync` must only apply approved proposals or patches; it must not decide what should be contributed upstream.
* `apply-library-sync` must only write to whitelisted paths inside `trellis-library`.
* Merge-mode analysis should scan already imported assets for upstream or local drift by default so scoped operations do not hide other pending divergence.
* After any source-library change produced by sync tooling, `validate-library-sync` must run and pass before the change is considered valid.

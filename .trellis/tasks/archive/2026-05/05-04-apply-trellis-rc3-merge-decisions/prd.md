# apply trellis rc3 merge decisions

## Goal

Apply the agreed rc3 merge decisions across Trellis workflow assets, keeping current workflow contracts stable while selectively absorbing only approved annotation-level improvements.

## What I already know

* `trellis-continue`, `trellis-finish-work`, `session-start`, and `inject-subagent-context` `.new` files contain phase-number drift and contract changes that must not be merged wholesale.
* The `trellis-brainstorm` `.new` set is only partially acceptable: command-name phrasing may be updated, but the phase diagram must stay on the current workflow model.
* `session-start / inject-subagent-context / session-utils` may absorb comment/docstring improvements only, without changing runtime behavior or visible phase text.
* Current repo state already includes tracked rc3 updates in `.trellis/.version`, `.trellis/.template-hashes.json`, and a few platform files.

## Assumptions (temporary)

* The current Trellis workflow contract remains `1.2 -> 1.3 -> 2.x -> 3.1 -> 3.2` for the active repo docs.
* `.new` files are treated as review candidates, not automatically trusted sources of truth.
* Old backup directories should be removed once the latest backup is confirmed sufficient.

## Requirements

* Keep `trellis-continue` on the current phase numbering and route table.
* Keep `trellis-finish-work` on `record-session-helper.py` and the current commit/close-out contract.
* Keep `session-start / inject-subagent-context / session-utils` behavior unchanged except for approved comments/docstrings.
* Accept only the agreed `trellis-brainstorm` command-name wording updates, not the rewritten phase diagram.
* Remove obsolete `.new` files after their contents are resolved.
* Preserve current tracked rc3 changes that were already accepted.

## Acceptance Criteria

* [ ] `rg --files -uu -g '*.new' .` returns no remaining `.new` files after resolution.
* [ ] `trellis-continue` files still route through the current workflow phase numbers.
* [ ] `trellis-finish-work` files still reference `record-session-helper.py` and current phase 3.1/3.2 contract.
* [ ] `session-start / inject-subagent-context / session-utils` only gain approved annotation changes, with no behavior drift.
* [ ] `trellis-brainstorm` only receives the approved command-name wording updates, not the rewritten phase diagram.
* [ ] Obsolete backup directories are cleaned up so only the latest backup remains.

## Definition of Done

* Requested merge decisions applied exactly as approved.
* No unintended workflow-contract drift introduced.
* Verification commands run and reviewed.
* Remaining diffs limited to accepted changes.

## Out of Scope

* Rewriting the workflow phase model.
* Migrating finish-work to `add_session.py`.
* Expanding CLI support to new platforms.
* Any behavior changes not explicitly approved.

## Technical Notes

* Relevant specs: `.trellis/spec/docs/index.md`, `.trellis/spec/scripts/index.md`, `.trellis/spec/skills/index.md`, `.trellis/spec/guides/index.md`.
* Current review focus: shared skill/command docs, runtime hooks, and cross-layer workflow contract alignment.

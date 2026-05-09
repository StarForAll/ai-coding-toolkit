# codex-inline-no-manual-subagent-spec

## Goal

Add a project-level spec that makes Codex inline-mode behavior explicit:
when `codex.dispatch_mode` is `inline`, the main Codex session must not
manually spawn subagents. The rule should live in `.trellis/spec/` so future
sessions can discover it through the normal pre-development workflow, and it
should also be reflected in repo-local Codex explanation surfaces.

## What I already know

* `.trellis/config.yaml` documents `codex.dispatch_mode: inline` as the default.
* The current project spec tree has a `platforms/` layer, but it has no
  top-level `index.md`, so it is not yet a stable entry point for
  platform-specific project rules.
* Existing universal-domain rules discuss delegation in general, but they do
  not express this Codex-inline-specific constraint.

## Assumptions (temporary)

* This rule is project-specific platform behavior, so it belongs in
  `.trellis/spec/platforms/` rather than in workflow product docs.
* The same rule should be discoverable through `.trellis/spec/index.md`.

## Open Questions

* None blocking.

## Requirements

* Add a project-level spec entry point for the `platforms/` layer.
* Add a Codex-specific rule document that states:
  * when `codex.dispatch_mode` is `inline`, do not manually spawn subagents
  * if subagent behavior is required, switch to an explicit non-inline project
    configuration/path first rather than ad hoc spawning
* Update relevant spec indexes so future sessions can discover the rule.
* Reflect the same rule in repo-local Codex carrier explanations so the
  Codex-facing surfaces do not contradict the project spec.

## Acceptance Criteria

* [ ] `.trellis/spec/platforms/index.md` exists and references the Codex rule
* [ ] a Codex platform spec file exists with the inline/no-manual-subagent rule
* [ ] `.trellis/spec/index.md` references the `platforms` layer as a readable
      spec surface
* [ ] `.codex/config.toml` and/or relevant `.codex/agents/*.toml` files
      explicitly avoid implying that inline mode may manually spawn subagents

## Definition of Done (team quality bar)

* Spec changes are consistent with existing `.trellis/spec/` structure
* Relevant indexes are updated
* Validation result is reported truthfully

## Out of Scope (explicit)

* Changing runtime code, hooks, or Codex config behavior
* Updating workflow product docs under `docs/workflows/**`
* Enforcing the rule programmatically in this change

## Technical Notes

* Relevant current files:
  * `.trellis/config.yaml`
  * `.trellis/spec/index.md`
  * `.trellis/spec/platforms/cli/command-interface/*`
  * `.trellis/spec/universal-domains/agent-collaboration/delegation-policy/*`

# Taxonomy

This file is the short structural reference for `trellis-library`.

## Source-Library Role

`trellis-library` is the source asset library for future Trellis project
initialization. It is not a target project's live `.trellis/` directory.

## Top-Level Structure

* `specs/`
  normative reusable rules
* `templates/`
  reusable output and document templates
* `checklists/`
  reusable execution and review checklists
* `examples/`
  example asset combinations and assembled packs
* `schemas/`
  machine-readable validation schemas
* `scripts/`
  automation for validation, assembly, sync, and proposal flow

## Specs Axes

`specs/` is split into four axes:

* `specs/universal-domains/`
  cross-project stable rules
* `specs/scenarios/`
  process and execution scenarios
* `specs/platforms/`
  runtime-platform constraints
* `specs/technologies/`
  stack-, framework-, language-, and version-specific constraints

## Parallel Layers

These layers sit beside `specs/` and should stay aligned with registered assets:

* `templates/`
  mirror reusable output structures
* `checklists/`
  mirror execution and review actions
* `examples/`
  show recommended combinations and pack usage
* `schemas/`
  define machine-readable shapes for source and target metadata

## Asset Shapes

The library uses two source-asset shapes:

* complex concern directories
  usually a directory containing files such as `overview.md`,
  `scope-boundary.md`, `normative-rules.md`, and `verification.md`
* simple single-file assets
  usually a template, checklist, schema, example, or script

Target projects should import a complete concern directory for complex specs.

## Boundary Rules

* `platforms/` and `technologies/` do not cross-reference directly
* shared reusable rules move up into `specs/universal-domains/`
* process-triggered guidance belongs in `specs/scenarios/`
* target-project improvements should flow back through diff and proposal
  workflows rather than direct overwrite

## Control Points

* `manifest.yaml`
  source-library registry
* `.trellis/library-lock.yaml`
  target-project state record
* validation, diff, proposal, and apply scripts
  controlled sync workflow

If the library taxonomy, sync model, or asset boundaries change, this file and
the root `README.md` should be updated together.

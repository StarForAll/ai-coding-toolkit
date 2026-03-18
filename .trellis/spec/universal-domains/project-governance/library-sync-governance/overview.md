# Library Sync Governance

## Purpose

Define governance rules for how `trellis-library` assets flow between the source library and target Trellis projects, including initialization, downstream sync, local divergence handling, selective upstream contribution, and controlled proposal application.

## Applicability

Use this concern when:

* initializing Trellis assets into a target project
* synchronizing source library updates into a target project
* evaluating whether target-project improvements should flow back into `trellis-library`
* applying approved upstream proposals to the source library

This concern applies to:

* `specs/`
* `templates/`
* `checklists/`
* `examples/`
* `schemas/`
* `scripts/`

when those assets are registered in `trellis-library/manifest.yaml`.

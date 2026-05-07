# workflow-capability-audit: 新项目开发工作流

## Goal

Audit whether a newer Trellis version changed baseline capabilities or mechanics in ways that require compatibility adaptation for `docs/workflows/新项目开发工作流/`.

## What I already know

* Current Trellis version is `0.5.4`.
* Current compatibility anchor is `0.5.0-rc.5`.
* This audit is limited to `docs/workflows/新项目开发工作流/`.

## Requirements

* Create fresh `A` and `B` fixtures after the version gate passes.
* Discover current Trellis baseline capabilities dynamically.
* Compare workflow-managed and workflow-dependent Trellis-native surfaces.
* Produce `capability-report.md` and stop for user confirmation.

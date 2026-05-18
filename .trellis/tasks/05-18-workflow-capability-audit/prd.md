# workflow-capability-audit: 新项目开发工作流

## Goal

Audit whether the current Trellis version relationship to the workflow compatibility anchor requires compatibility adaptation for `docs/workflows/新项目开发工作流/`.

## What I already know

* Current Trellis version is `0.5.17`.
* Current compatibility anchor is `0.5.16`.
* This audit is limited to `docs/workflows/新项目开发工作流/`.

## Requirements

* Create fresh `A` and `B` fixtures after the version gate allows continuation.
* Discover current Trellis baseline capabilities dynamically.
* Compare workflow-managed and workflow-dependent Trellis-native surfaces.
* Produce `capability-report.md` and stop for user confirmation.

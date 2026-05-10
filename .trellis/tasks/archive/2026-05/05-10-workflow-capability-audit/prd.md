# workflow-capability-audit: 新项目开发工作流

## Goal

Audit whether a newer Trellis version changed baseline capabilities or mechanics in ways that require compatibility adaptation for `docs/workflows/新项目开发工作流/`.

## What I already know

* Current Trellis version is `0.5.10`.
* Current compatibility anchor is `0.5.9`.
* This audit is limited to `docs/workflows/新项目开发工作流/`.
* A prior compatibility-audit fix already corrected initial managed-surface discovery for enhanced `trellis-research` and install-only `todo.txt`.
* A new review batch identifies 27 candidate issues spanning code contracts, docs drift, tests, and low-risk cleanup items.

## Assumptions (temporary)

* Not every reported issue is real; each item must be revalidated against source, tests, and current contracts before fixing.
* Priority is code-contract correctness first, then doc/asset alignment, then low-risk cleanup only when evidence is strong and blast radius is low.
* Similar-issue sweeps are required where the same contract appears in multiple CLIs, docs, or regression paths.

## Open Questions

* none yet; current blockers are derivable from repo code and docs.

## Requirements (evolving)

* Revalidate all user-reported issues against current repository state.
* Fix real `upgrade-compat.py` early-exit / writeback / restore / cleanup defects without regressing legacy compatibility paths.
* Fix real `analyze-upgrade.py` coverage gaps for workflow-managed / installer-managed surfaces and structural-risk signaling.
* Fix real `workflow-capability-audit.py` output/coverage gaps if current code still under-reports or inconsistently reports evidence.
* Update product docs when they contradict current installer / upgrade / runtime contracts.
* Sweep similar variants where the same source-of-truth or carrier contract appears in multiple files.

## Acceptance Criteria (evolving)

* [ ] Each reported issue is classified as real / false alarm / partial, with source evidence.
* [ ] All real code-contract issues fixed in source and covered by regression tests.
* [ ] `upgrade-compat.py` writes expected install-record fields in supported merge/force paths and handles attempt-record cleanup correctly.
* [ ] `analyze-upgrade.py` covers the intended managed/legacy surfaces and emits actionable structural-risk guidance when required.
* [ ] Docs about enhanced `trellis-research`, install-record fields, and embed/upgrade contracts match current code behavior.
* [ ] Verification passes for modified scripts/tests.

## Out of Scope (explicit)

* Changing Trellis upstream behavior outside this repository
* Blindly deleting low-level helpers or assets merely because they look unused, without contract proof
* Auto-finalizing the current capability-audit lifecycle before code/doc fixes are verified

## Technical Notes

* Primary code surfaces:
  * `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  * `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
* Primary regression surfaces:
  * `commands/test_workflow_installers.py`
  * `commands/test_upgrade_analysis.py`
  * `commands/test_workflow_capability_audit.py`
* Primary doc surfaces:
  * `工作流总纲.md`
  * `CLI原生适配边界矩阵.md`
  * `目标项目兼容升级方案指导.md`
  * `工作流嵌入执行规范.md`
  * `结构性迁移设计.md`
  * `命令映射.md`
  * `docs/Trellis元数据自动提交失败恢复指南.md`

## Requirements

* Create fresh `A` and `B` fixtures after the version gate passes.
* Discover current Trellis baseline capabilities dynamically.
* Compare workflow-managed and workflow-dependent Trellis-native surfaces.
* Produce `capability-report.md` and stop for user confirmation.

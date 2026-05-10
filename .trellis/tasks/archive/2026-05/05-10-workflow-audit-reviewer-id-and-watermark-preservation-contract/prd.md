# workflow-audit reviewer-id and watermark-preservation contract

## Goal

Update the repo-local workflow product under `docs/workflows/新项目开发工作流/` so it fully implements two confirmed maintenance requirements: standardize multi-reviewer `reviewer-id` assignment away from CLI names and onto letter-based IDs, and extend the ownership-proof/source-watermark chain so target-project project-level spec and phase gates require later edits to preserve watermark effects with an automatic repair path for repairable drift.

## What I already know

* `review-gate`, `project-audit`, and the shared `multi-cli-review` / `multi-cli-review-action` pair currently require explicit `--reviewer-id`, but they do not define a letter-only contract.
* Workflow examples still use CLI-shaped reviewer IDs such as `claude`, `opencode`, `claude-reviewer-a`, and similar variants.
* The current ownership-proof chain freezes watermark strategy in `assessment.md` and `source-watermark-plan.md`, then validates task/delivery artifacts via `ownership-proof-validate.py`.
* The current workflow does not require later source changes to preserve watermark effects and does not ship an automatic repair helper for drift in protected watermark snippets.

## Assumptions (temporary)

* Letter-based reviewer IDs should use a simple bounded set such as `a` / `b` / `c` / `d`, while actual reviewer CLI identity remains recorded separately in reviewer report metadata via `source-cli`.
* Automatic repair should be limited to explicitly declared, low-risk watermark snippets with deterministic reinsertion rules; unrecoverable drift should still block with a clear error.
* The workflow product version should be advanced because this changes installed workflow behavior, helper-script distribution, and target-project phase-gate expectations.

## Open Questions

* None blocking from repo context. Implementation can proceed with the bounded repairability assumption above.

## Requirements (evolving)

* Standardize reviewer command packaging so default multi-reviewer flows assign `reviewer-id` as letters rather than CLI names.
* Keep `source-cli` as the field that records which CLI produced a reviewer report.
* Propagate the reviewer-id rule consistently across workflow docs, shared skills, repo-local specs, examples, and persisted workflow tests/examples that act as protocol references.
* Extend project-level spec and source-watermark design guidance so protected watermark-bearing source files must declare preservation/repair metadata after watermark insertion.
* Add a workflow helper script that can validate protected watermark snippets in target-project source files and automatically repair explicitly repairable drift.
* Wire the new helper into workflow helper distribution, command docs, maintainer boundary docs, and regression tests.

## Acceptance Criteria (evolving)

* [ ] `review-gate`, `project-audit`, workflow summary/mapping docs, and shared multi-reviewer skills all describe reviewer IDs as letter-based rather than CLI-based.
* [ ] Shared `multi-cli-review` protocol examples, metadata rules, and paired `multi-cli-review-action` intake rules remain aligned after the reviewer-id change.
* [ ] Source-watermark design/spec docs require a machine-readable protected-file repair registry or equivalent deterministic repair contract.
* [ ] A workflow helper script validates protected watermark snippets against target-project source files and repairs declared low-risk drift when invoked in repair mode.
* [ ] Check/delivery/project-spec guidance references the new watermark preservation guard consistently.
* [ ] Relevant tests pass for helper deployment and watermark guard behavior.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Redesigning the entire multi-reviewer workflow beyond reviewer-id normalization
* Building a fully general AST-aware watermark engine for arbitrary languages
* Runtime `/tmp` install audit of the workflow in this task unless verification requires it

## Technical Notes

* Likely impacted workflow docs: `工作流总纲.md`, `命令映射.md`, `工作流全局流转说明（通俗版）.md`, `commands/review-gate.md`, `commands/project-audit.md`, `commands/design.md`, `commands/check.md`, `commands/delivery.md`, `源码水印与归属证据链执行卡.md`, CLI README/boundary docs.
* Likely impacted shared skills/specs: `skills/multi-cli-review/SKILL.md`, `skills/multi-cli-review-action/SKILL.md`, `.trellis/spec/docs/index.md`, `.trellis/spec/skills/index.md`, `.trellis/spec/commands/index.md`.
* Likely impacted helper/tooling: `commands/workflow_assets.py`, `commands/test_workflow_installers.py`, `commands/shell/ownership-proof-validate.py`, new helper under `commands/shell/`, and related tests.

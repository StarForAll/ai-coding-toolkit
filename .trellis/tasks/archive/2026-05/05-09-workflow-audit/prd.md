# workflow-audit: 新项目开发工作流

## Goal

Audit whether `docs/workflows/新项目开发工作流/` already satisfies four candidate requirements raised by the user, with evidence-first conclusions and runtime validation when static analysis is insufficient.

## What I already know

* The supported workflow root for `workflow-audit` is fixed to `docs/workflows/新项目开发工作流/`.
* `workflow-audit` requires exact version equality between `docs/workflows/新项目开发工作流/commands/workflow_assets.py:COMPATIBLE_TRELLIS_VERSION` and local `trellis -v`.
* Version preflight passed: `COMPATIBLE_TRELLIS_VERSION = 0.5.9` and local `trellis -v = 0.5.9`.
* The user explicitly requires a detailed audit and rejects static-only analysis.
* Candidate issues to validate:
* 1. Workflow must use Trellis native agents.
* 2. Workflow docs should become pure English except necessary maintainer-human-reading docs; this conversation must not use subagents.
* 3. After embed into target project, default project-level spec should require bilingual README updates and Chinese as the default README.
* 4. `grill-me` can be deleted because Trellis native brainstorm already covers that capability.
* Later user instruction narrowed this remediation round to item 1 and item 3 only; item 4 must remain explicitly not executed rather than left undecided.

## Assumptions (temporary)

* Requirement 2 is about workflow source docs and installed workflow docs, not about repository-global docs outside the workflow root unless they are part of the workflow contract.
* Requirement 3 needs runtime validation because it concerns generated target-project state after embed.
* The current executor is Codex, so any formal embed step under Step D must stop at the Codex handoff boundary.

## Open Questions

* None blocking. Candidate issue 4 is explicitly closed as "reviewed but not executed in this round" per user instruction.

## Requirements (evolving)

* Determine whether each of the four candidate requirements is already satisfied, partially satisfied, or not satisfied.
* Distinguish source-repo evidence, runtime command output, and generated target-project evidence.
* Trigger runtime validation where required by the workflow-audit contract.
* Do not use subagents in this conversation.
* Keep item 4 (`grill-me` removal) recorded as an explicit no-op decision for this round, not an unresolved dangling candidate.

## Acceptance Criteria (evolving)

* [ ] Version preflight result is recorded.
* [ ] Step 2 A/B/C evidence is collected for all four candidate requirements.
* [ ] Runtime-validation boundary is judged explicitly.
* [ ] Final audit conclusion distinguishes confirmed issues, false alarms, and evidence gaps.
* [ ] Recommended next step is controlled and does not auto-continue.

## Definition of Done (team quality bar)

* Evidence is tied to exact files, scripts, or command outputs.
* No claim of verification is made without actual verification.
* If runtime validation is blocked by the Codex handoff boundary, the report says so explicitly.

## Out of Scope (explicit)

* Auditing other workflows under `docs/workflows/`.
* Cross-version capability audit; that belongs to `workflow-capability-audit`.
* Claiming formal post-install success under Codex without non-Codex handoff evidence.

## Technical Notes

* Current task path: `.trellis/tasks/05-09-workflow-audit`
* Core audit contract sources:
* `.trellis/spec/skills/workflow-audit.md`
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
* `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`

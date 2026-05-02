# workflow-audit skill coverage for trellis-native capability audit

## Goal

Assess whether the existing `workflow-audit` skill can cover a maintainer-side audit scenario that compares a pure `trellis init` baseline project with a workflow-embedded project, identifies which Trellis native capabilities are missing from the embedded workflow, distinguishes intentional non-adoption from accidental omission, and then proposes a repo-local skill strategy before any implementation work.

## What I already know

* The user does **not** want the `/tmp` A/B validation procedure executed now; the current task is to evaluate skill coverage only.
* The existing `workflow-audit` skill already covers workflow source-asset audit, embed/install/post-install validation, CLI adaptation checks, Codex handoff, and `/tmp + trellis init` runtime validation when needed.
* The existing `workflow-audit` contract is centered on evidence steps A/B/C/D/E and outputs confirmed issues, blocked items, per-CLI conclusions, and fix directions.
* The workflow under `docs/workflows/新项目开发工作流/` already documents some Trellis-native capability boundaries:
* `research -> implement -> check-agent` is explicitly documented as the implementation-internal subagent chain.
* `parallel/worktree` is explicitly disabled by `commands/parallel-disabled.md`.
* `plan agent` readiness concepts are partially adopted, but `plan -> dispatch` is explicitly not part of the current workflow mainline.
* `record-session` remains largely a Trellis baseline capability plus workflow helper/patch semantics.
* Current `workflow-audit` docs/tests do **not** explicitly model a dedicated "baseline capability diff" analysis that classifies each Trellis native capability as adopted / intentionally not adopted / missing / drifted.
* The user explicitly wants the new sibling skill to follow `workflow-audit`-like steps, but with a mandatory first phase that understands the latest Trellis baseline mechanisms and advantages before performing A/B comparison.
* The user explicitly requires A/B comparison as a mandatory part of the new skill, not an optional escalation path.
* The user explicitly requires the new skill to judge not only whether a Trellis capability exists, but also whether it is compatible with the current workflow model; incompatible capabilities should lead to workflow adaptation recommendations inside `docs/workflows/新项目开发工作流/`.

## Assumptions (temporary)

* The main design question is not whether `workflow-audit` can execute static/runtime evidence collection, but whether its semantic model is broad enough for capability-diff analysis.
* The desired future analysis should stay limited to `docs/workflows/新项目开发工作流/` and avoid data drift across docs/scripts/tests.

## Open Questions

* No open design question currently recorded; ready to summarize the converged contract for `workflow-capability-audit`.

## Requirements (evolving)

* Determine the current coverage boundary of `workflow-audit` based on repo evidence, not assumption.
* Identify the mismatch between the requested scenario and the current `workflow-audit` contract.
* Distinguish execution capability from semantic completeness.
* The solution direction is now fixed: create a new adjacent skill derived from `workflow-audit`, not extend `workflow-audit` directly.
* The new skill must first understand the latest Trellis baseline capabilities/mechanisms before concluding anything about workflow capability gaps.
* The new skill must include A/B comparison as a required evidence phase.
* The new skill's primary output is now fixed: a Trellis-native capability matrix, not a plain issue list.
* The new skill must judge compatibility between each Trellis native capability and the current workflow model, and must propose workflow-side adaptation when a capability is incompatible but valuable.
* Compatibility must be explicit in the classification model rather than implied in prose.
* First version scope is fixed to `docs/workflows/新项目开发工作流/` only; do not pretend it is generic for arbitrary workflow roots.
* The new skill must be a repo-local maintainer skill, with mirrored skill surfaces under `.agents/skills/` and `.claude/skills/`, plus a repo-local behavioral spec under `.trellis/spec/skills/`.
* First version uses task-based execution only; no lightweight mode.
* The new skill should use its own dedicated task-based audit flow rather than reusing `brainstorm` as the control container.
* First version should maintain a single canonical report file rather than split matrix/adaptation artifacts.
* A/B runtime evidence must come from fresh temporary projects created by the skill itself; first version does not accept user-supplied existing A/B roots.
* Baseline capability discovery should be dynamic per fresh Trellis version, not a hardcoded fixed checklist.
* User supplementation of missed capabilities happens after the AI's discovery pass, not as part of the initial input contract.
* The user's proposed pre-run version gate cannot use existing fields as-is:
* `WORKFLOW_VERSION` / `workflow_version` identify the workflow, not the Trellis baseline compatibility anchor.
* `.trellis/.version` / install-record `trellis_version` identify target-project runtime state, not source-maintenance compatibility state.
* A dedicated source-side Trellis compatibility-version anchor is needed.
* `docs/workflows/新项目开发工作流/commands/workflow_assets.py` is the best current anchor candidate because it already serves as the workflow version single-source module for install/upgrade/analysis logic.
* When current `trellis --version` matches the compatibility anchor, the skill should terminate further execution rather than merely skipping the full audit.
* If the user points out an omitted capability after one discovery pass, the skill should validate that point within the same audit round using the same A/B fixtures and the same `capability-report.md`, rather than restarting from scratch.
* Version gating must happen before any task creation or audit-file creation.
* The compatibility-version anchor should update only after the audit conclusion is confirmed and compatibility maintenance has been validated as complete.
* Compatibility-anchor update does not require source edits if the confirmed full-audit conclusion is that the workflow is already compatible as-is.
* `COMPATIBLE_TRELLIS_VERSION` should be stored as a concrete value only in `docs/workflows/新项目开发工作流/commands/workflow_assets.py`; other skill/spec/test/docs surfaces should reference the rule but not duplicate the value.
* The single-source rule for `COMPATIBLE_TRELLIS_VERSION` must be written into repo-local spec, not left as an implementation convention.
* `trellis --version` and fresh `.trellis/.version` should be treated as the same source lineage for version-gate purposes in first-version design.
* If `trellis --version` fails or returns empty output, the skill must terminate immediately as `Blocked / Environment Error`.
* Version-direction judgment must use semantic-version comparison rather than raw string ordering.
* For the same numeric base version, prerelease precedence is `beta < rc < stable` (no prerelease marker).
* Only `current > COMPATIBLE_TRELLIS_VERSION` enters full audit; equality terminates, lower versions block.
* If version parsing fails, the skill must terminate as `Blocked / Version Parse Error`.
* After full audit, the skill must stop at the audit-conclusion boundary and wait for user confirmation before any workflow source edits.
* `capability-report.md` must include an explicit `Structural-Break Judgment` section rather than burying that conclusion inside adaptation notes.
* `Structural-Break Judgment` should use tri-state semantics: `no / possible / yes`.
* `Structural-Break Judgment = possible` should stop the skill and require explicit user confirmation rather than letting the normal adaptation path continue.
* `Structural-Break Judgment = possible` should use a dedicated stop-and-confirm template/reference rather than ad-hoc prose.
* Version-gate termination states should use dedicated fixed templates/references rather than ad-hoc prose.
* Version-gate termination should use one unified template/reference with a typed `Gate Result` field rather than multiple per-state templates in first version.
* Fresh A/B temporary projects should be preserved throughout the compatibility-fix lifecycle and destroyed only after the correction work is complete.
* `capability-report.md` should remain the single evolving evidence artifact through audit, confirmed fix scope, applied corrections, and post-fix revalidation.
* Even after compatibility correction is complete, A/B fixture destruction should require an explicit final confirmation step.
* If a non-audit active task already exists, `workflow-capability-audit` should create a dedicated child audit task and switch execution into it immediately.
* The capability matrix/report scope should cover both workflow-managed assets and Trellis-native capabilities that the workflow depends on even when they are not installer-managed.
* `capability-report.md` should separate `workflow-managed surface` and `workflow-dependent Trellis-native surface` into distinct sections.
* `workflow-capability-audit` should ship with persisted scenario test files mirroring the `workflow-audit` style rather than keeping behavior validation implicit in prose.
* `capability-report.md` should use one unified capability matrix organized by capability rows, with per-CLI evidence/classification columns plus an overall summary.
* Row-level `overall summary` should be derived by the most severe / most action-demanding per-CLI classification, rather than a neutral average.
* Confirmed user-supplemented capabilities should be inserted into the matrix at the appropriate logical position rather than appended uniformly at the end.
* `capability-report.md` should include a dedicated `Rejected / Unconfirmed Supplemental Points` section for user-supplemented capabilities that do not validate.
* Each formal capability row should include an explicit `Discovery Source` field.
* `Discovery Source` should use a fixed first-version enum rather than free text.
* Each capability row should include a stable `Capability ID` field for cross-referencing fixes and revalidation.
* `Capability ID` should use surface-prefixed first-version formats such as `WM-*` and `TN-*`.
* Once assigned, `Capability ID` should remain stable for the life of the audit/fix cycle; later supplemental insertion must not trigger renumbering.
* Per-CLI classification should support an explicit `not-applicable` state for capabilities that do not meaningfully apply to a given CLI.
* `not-applicable` should sit at the lowest-interference position in `overall summary` derivation and must not override any more action-demanding state.
* `COMPATIBLE_TRELLIS_VERSION` alone is sufficient for the pre-run gate; the skill is scoped to Trellis version-upgrade compatibility rather than ordinary workflow-source drift after same-version operation.
* Missing `COMPATIBLE_TRELLIS_VERSION` should not auto-bootstrap the audit; the user must supplement the value first.
* If the user supplements `COMPATIBLE_TRELLIS_VERSION`, that value must be written into `docs/workflows/新项目开发工作流/commands/workflow_assets.py` before the audit continues.
* The skill may need a narrowly scoped exception to the normal “no source edits before audit conclusion” rule when initializing a missing compatibility-version anchor.
* Writing a missing `COMPATIBLE_TRELLIS_VERSION` into `workflow_assets.py` should be the sole allowed pre-audit source edit exception.
* Final `COMPATIBLE_TRELLIS_VERSION` promotion after a confirmed compatibility conclusion should not be auto-written by the audit skill itself; it belongs to the subsequent confirmed implementation/update step.
* Keep recommendations scoped to repo-local workflow assets under `docs/workflows/新项目开发工作流/` and related skill/spec/test files.

## Acceptance Criteria

* [x] Evidence-backed summary states what `workflow-audit` already covers. → "What I already know" § (lines 7-20) + Technical Notes (lines 119-131)
* [x] Evidence-backed summary states what the requested scenario adds beyond current coverage. → Requirements §: capability-diff analysis, A/B comparison, compatibility matrix, version gating, structural-break judgment — none of which exist in current `workflow-audit`
* [x] A concrete decision fork is presented: extend existing skill vs create sibling skill. → DECIDED: create new sibling skill `workflow-capability-audit`
* [x] All design questions resolved through extensive user-decision capture (47+ user decisions recorded in Requirements §); no unresolved questions remain

## Definition of Done

* Scope and decision boundary are clear enough to choose the skill strategy.
* The next implementation step is obvious and bounded.

## Out of Scope (explicit)

* Actually creating `/tmp` project A/B fixtures right now
* Running `trellis init` or `install-workflow.py` as part of this turn's analysis
* Editing `docs/workflows/新项目开发工作流/` before the skill-strategy decision is confirmed

## Technical Notes

* Key files inspected:
* `.agents/skills/workflow-audit/SKILL.md`
* `.trellis/spec/skills/workflow-audit.md`
* `.agents/skills/workflow-audit/tests/02-nontrivial-full-audit.md`
* `.agents/skills/workflow-audit/tests/03-codex-handoff.md`
* `.agents/skills/workflow-audit/tests/04-task-based-static.md`
* `docs/workflows/新项目开发工作流/工作流总纲.md`
* `docs/workflows/新项目开发工作流/commands/codex/README.md`
* `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
* `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
* `docs/workflows/新项目开发工作流/commands/parallel-disabled.md`
* User decision captured:
* Create a new sibling skill instead of extending `workflow-audit`.
* User decision captured:
* The new skill must perform mandatory A/B comparison after understanding the latest Trellis baseline.
* User decision captured:
* The new skill must use a capability-matrix report and include compatibility/adaptation judgment.
* User decision captured:
* Compatibility must be a first-class explicit classification dimension.
* User decision captured:
* First version is dedicated to `docs/workflows/新项目开发工作流/` only.
* User decision captured:
* The skill is repo-local maintainer scope and must include `.claude/skills`, `.agents/skills`, and `.trellis/spec`.
* User decision captured:
* The new skill should keep only task-based mode.
* User decision captured:
* The new skill should use an independent task-based audit flow rather than the `brainstorm` control container.
* User decision captured:
* The canonical task report should be a single `capability-report.md` file.
* User decision captured:
* A/B comparison must use fresh temporary projects created during the run.
* User decision captured:
* The report should separate dynamic baseline capability discovery from the stable compatibility-classification matrix.
* User decision captured:
* The capability matrix/report must cover both workflow-managed assets and Trellis-native capabilities that the workflow depends on even when they are not installer-managed.
* User decision captured:
* `capability-report.md` should separate `workflow-managed surface` and `workflow-dependent Trellis-native surface` into explicit sections.
* User decision captured:
* `workflow-capability-audit` should ship with persisted scenario test files in the `workflow-audit` style.
* User decision captured:
* `capability-report.md` should use one unified capability matrix with per-CLI evidence/classification columns and an overall summary.
* User decision captured:
* Row-level `overall summary` should prioritize the most severe / most action-demanding per-CLI classification.
* User decision captured:
* Confirmed user-supplemented capabilities should be inserted into the matrix at the appropriate logical position rather than appended at the end.
* User decision captured:
* `capability-report.md` should include a dedicated `Rejected / Unconfirmed Supplemental Points` section.
* User decision captured:
* Each formal capability row should include an explicit `Discovery Source` field.
* User decision captured:
* `Discovery Source` should use a fixed first-version enum: `ai-discovered` or `supplemental-confirmed`.
* User decision captured:
* Each capability row should include a stable `Capability ID` field.
* User decision captured:
* `Capability ID` should use surface-prefixed first-version formats such as `WM-*` and `TN-*`.
* User decision captured:
* `Capability ID` remains stable for the whole audit/fix lifecycle; later supplemental insertion does not trigger renumbering.
* User decision captured:
* Per-CLI classification should support an explicit `not-applicable` state.
* User decision captured:
* `not-applicable` sits at the lowest-interference position in `overall summary` derivation and must not override any more action-demanding state.
* User decision captured:
* If the AI misses a Trellis capability but the user supplements it, the point must be treated as a hypothesis, validated against current-version evidence, and appended only if confirmed.
* User decision captured:
* Missed capability supplementation is a post-analysis correction loop, not an initial input field.
* User decision captured:
* Before expensive runtime work, compare the current `trellis --version` with the workflow-side corresponding Trellis version; only mismatch should trigger the full audit path by default.
* User decision captured:
* The workflow source needs a dedicated Trellis compatibility-version anchor.
* User decision captured:
* Version equality should terminate further execution and explain why, rather than silently skipping or auto-overriding.
* `Structural-Break Judgment = possible` should stop and require explicit user confirmation before any normal adaptation path is recommended.
* User decision captured:
* Post-analysis supplementation should reuse the same audit round's A/B fixtures and `capability-report.md`.
* User decision captured:
* The skill begins with version comparison; task creation and audit artifacts only happen after the version gate passes.
* User decision captured:
* `COMPATIBLE_TRELLIS_VERSION` updates only after the audit is complete, the user confirms the conclusion, and compatibility repair/verification is complete.
* User decision captured:
* If a confirmed full audit concludes the workflow is already compatible with the current Trellis version, the compatibility-version anchor may still be updated without source edits.
* User decision captured:
* `COMPATIBLE_TRELLIS_VERSION` uses `workflow_assets.py` as the single concrete value source; other surfaces must not duplicate the literal version.
* User decision captured:
* The single-source rule for `COMPATIBLE_TRELLIS_VERSION` must be recorded in spec so future maintenance does not forget it.
* User decision captured:
* `trellis --version` and fresh `.trellis/.version` are treated as same-source signals from the current Trellis version lineage.
* User decision captured:
* `trellis --version` failure should terminate the skill as `Blocked / Environment Error`.
* User decision captured:
* Version-direction comparison must use semantic-version comparison, and parse failure must terminate as `Blocked / Version Parse Error`.
* User decision captured:
* For the same numeric base version, prerelease precedence is `beta < rc < stable`.
* User decision captured:
* Only `current > COMPATIBLE_TRELLIS_VERSION` enters full audit; equality terminates, lower versions block.
* User decision captured:
* `workflow-capability-audit` must stop after producing the audit conclusion and wait for user confirmation before any source edits.
* User decision captured:
* `Structural-Break Judgment` must be an explicit required section in `capability-report.md`.
* User decision captured:
* `Structural-Break Judgment` should use `no / possible / yes`.
* User decision captured:
* `Structural-Break Judgment = possible` should use a dedicated stop-and-confirm template/reference.
* User decision captured:
* Version-gate termination states should use dedicated fixed templates/references.
* User decision captured:
* Version-gate termination should use a single unified template/reference with a typed `Gate Result` field.
* User decision captured:
* Fresh A/B temporary projects must remain available until compatibility correction is complete, and only then be destroyed.
* User decision captured:
* `capability-report.md` remains the single evolving evidence artifact throughout the subsequent confirmed compatibility-fix and revalidation phase.
* User decision captured:
* A/B fixture destruction requires an explicit final confirmation step even after compatibility correction is complete.
* User decision captured:
* When a non-audit active task exists, `workflow-capability-audit` creates a dedicated child audit task and immediately switches into it.
* User decision captured:
* No extra compatibility-audit snapshot anchor is needed; the skill only judges Trellis version-upgrade compatibility, so same Trellis version means no compatibility audit is needed.
* User decision captured:
* If `COMPATIBLE_TRELLIS_VERSION` is missing, the user supplements the value instead of auto-running a bootstrap audit.
* User decision captured:
* User-supplemented `COMPATIBLE_TRELLIS_VERSION` must be written into `workflow_assets.py` before the skill proceeds.
* User decision captured:
* The skill itself should write the supplemented `COMPATIBLE_TRELLIS_VERSION` into `workflow_assets.py` before continuing.
* User decision captured:
* Writing a missing `COMPATIBLE_TRELLIS_VERSION` into `workflow_assets.py` is the sole allowed pre-audit source edit exception.
* User decision captured:
* Final `COMPATIBLE_TRELLIS_VERSION` updates after a confirmed successful audit belong to the subsequent confirmed implementation step, not to the audit skill itself.

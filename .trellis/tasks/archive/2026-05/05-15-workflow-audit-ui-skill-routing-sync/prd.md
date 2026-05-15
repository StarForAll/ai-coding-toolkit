# workflow-audit-ui-skill-routing-sync

## Goal

Synchronize the workflow's UI design/prototype-restoration skill routing rules so the design stage explicitly requires `ui-ux-pro-max` as the base skill and conditionally routes additional skills by platform, framework, styling stack, and current stage. Propagate the rule consistently across the canonical command doc, the global mapping doc, and the walkthrough doc.

## What I already know

* The workflow already forbids Codex from being the primary executor for `UI 原型生成` and `UI -> 首版代码界面`.
* The workflow currently names `ui-ux-pro-max` in `commands/design.md` but does not document the positive conditional routing for related UI skills.
* The user confirmed the desired policy:
  * `ui-ux-pro-max` is mandatory.
  * Other skills are routed conditionally by platform, framework, styling stack, and current stage.
  * Sync must cover `commands/design.md`, `命令映射.md`, and `多CLI通用新项目完整流程演练.md`.
* Relevant applicable skills for the current repo context:
  * Web: `shadcn-ui`, `vue-best-practices`, `unocss`, `agent-browser`, `webapp-testing`, `accessibility-a11y`
  * iOS: `mobile-ios-design`, `ios-application-dev`
  * Android: `mobile-android-design`, `android-native-dev`
  * Cross-platform Flutter: `flutter-expert`, with platform design skills added only when platform-native visual alignment is required

## Assumptions (temporary)

* This is a documentation-only change; no workflow installer/runtime code changes are needed.
* `commands/design.md` remains the canonical source for the detailed routing rule.
* `命令映射.md` should carry only a compressed principle-level version.
* `多CLI通用新项目完整流程演练.md` should carry a user-facing operational version, not a full duplicate table.

## Open Questions

* None blocking. User already confirmed the desired wording direction and sync scope.

## Requirements (evolving)

* Update `docs/workflows/新项目开发工作流/commands/design.md` to:
  * keep `ui-ux-pro-max` as mandatory for UI design / prototype restoration
  * add a conditional routing table for additional skills
  * preserve the existing external-tool boundary and Codex prohibition
* Update `docs/workflows/新项目开发工作流/命令映射.md` to reflect the new design-stage routing principle without expanding it into a full repeated table
* Update `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md` to explain the same rule in walkthrough form
* Keep wording aligned across the three docs and avoid introducing cross-document drift

## Acceptance Criteria (evolving)

* [ ] `commands/design.md` explicitly states `ui-ux-pro-max` is mandatory and other UI skills are conditionally routed by platform / framework / styling stack / current stage
* [ ] `命令映射.md` reflects the compressed design-stage routing principle
* [ ] `多CLI通用新项目完整流程演练.md` reflects the walkthrough-facing version of the same rule
* [ ] No document frames the Web routing as a single fixed skill bundle
* [ ] No document incorrectly applies `accessibility-a11y` to iOS/Android native work

## Definition of Done (team quality bar)

* Relevant docs updated coherently
* Targeted validation command run
* No broken rule-propagation gaps across the touched docs

## Out of Scope (explicit)

* Changing workflow installer/runtime behavior
* Adding new skills or removing existing ones
* Extending the rule into unrelated workflow docs unless propagation evidence requires it

## Technical Notes

* Relevant specs:
  * `.trellis/spec/docs/index.md`
  * `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  * `.trellis/spec/guides/cross-layer-thinking-guide.md`
* Canonical source doc to update first:
  * `docs/workflows/新项目开发工作流/commands/design.md`
* Sync targets:
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`

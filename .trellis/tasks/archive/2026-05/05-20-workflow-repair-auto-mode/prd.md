# Add workflow-repair auto mode

## Goal

Add a documented `--auto` input mode to `skills/workflow-repair/` so the skill can continue through its normal post-plan and post-repair wrap-up flow automatically after the user has chosen to execute the current task, including using `ok` for any commit-confirmation prompt and then running the Trellis finish-work command for the current task.

## What I already know

- The user wants this implemented in the current repository's `skills/workflow-repair/` asset.
- This repository is Trellis-managed and currently runs Codex in inline mode, so implementation stays in the main session.
- `skills/workflow-repair/SKILL.md` is the primary installable skill surface.
- `.trellis/spec/skills/workflow-repair.md` is the repo-local behavioral spec for this skill and should stay aligned with the skill text.
- `scripts/validate-skills.sh` contains targeted workflow-scan/workflow-repair contract checks and is the relevant validation entrypoint.
- The requested `--auto` behavior concerns repair-side execution and wrap-up behavior, not the shared `WORKFLOW_QUESTIONS.md` schema.

## Assumptions (temporary)

- `--auto` is a repair-side execution option that should be documented as opt-in and conservative rather than becoming the default mode.
- "原本的基础上自动执行后续流程直到对应任务完成" means the skill should still follow its existing verification and correction-plan flow, then continue automatically only after repair execution is authorized.
- "如果询问提交则输入ok即可" refers to the Phase 3.4 commit confirmation flow before finish-work.
- Running finish-work should be documented as using whichever Trellis command surface is available in the current environment, with `trellis-finish-work` and `/trellis:finish-work` both acknowledged as examples rather than a guaranteed universal command string.

## Open Questions

- None currently blocking; the requested behavior is specific enough to implement from repo context.

## Requirements (evolving)

- Add `--auto` to the `workflow-repair` skill input contract.
- Define `--auto` as an explicit opt-in mode that preserves the existing report validation, correction-plan, repair, and post-repair verification flow.
- Define the extra automatic continuation after repair:
  - if a commit confirmation prompt appears for the current task, respond with `ok`
  - after the current task work is complete, invoke the Trellis finish-work command surface to archive and record the task
- Keep the skill main-session inline and do not broaden it to agent mode.
- Keep the shared workflow-scan/workflow-repair report protocol unchanged unless evidence shows a real coupling need.
- Update repo-local spec/validation surfaces as needed so the new behavior is documented and checked consistently.

## Acceptance Criteria (evolving)

- [ ] `skills/workflow-repair/SKILL.md` documents `--auto`, including when it applies and what extra steps it performs.
- [ ] `.trellis/spec/skills/workflow-repair.md` reflects the new repair-side behavior and review expectations.
- [ ] Any validation or contract-check surface that should guard this behavior is updated in the same change.
- [ ] `./scripts/validate-skills.sh` passes.

## Definition of Done (team quality bar)

- Tests added/updated (unit/integration where appropriate)
- Lint / typecheck / CI green
- Docs/notes updated if behavior changes
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- Changing the shared `WORKFLOW_QUESTIONS.md` protocol version or schema
- Introducing repair-side agents or sub-agents
- Changing Trellis finish-work command implementation outside the scope needed to document skill behavior

## Technical Notes

- Relevant files:
  - `skills/workflow-repair/SKILL.md`
  - `.trellis/spec/skills/workflow-repair.md`
  - `scripts/validate-skills.sh`
- Coupling review required against:
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `skills/workflow-repair/references/*.md`
- Shared guidance consulted:
  - `.trellis/spec/skills/index.md`
  - `.trellis/spec/guides/code-reuse-thinking-guide.md`
  - `.trellis/spec/guides/cross-layer-thinking-guide.md`

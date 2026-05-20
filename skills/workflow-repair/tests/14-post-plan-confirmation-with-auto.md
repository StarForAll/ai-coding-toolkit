# 14 Post-Plan-Confirmation With Auto

## Purpose

Verify that an analysis-first run with `--auto` may transition into
`post-plan-confirmation`, execute repairs, and then continue into auto
follow-through.

## Input

User input:

> Run `/workflow-repair --auto` to analyze first. After the correction plan is shown, the user explicitly accepts all or partial execution, repairs succeed sufficiently, and the close-out flow remains safe with the normal `continue`-driven progression.

## Expected Mode

Analysis-first repair run that transitions into execution-time
`post-plan-confirmation` and then enters auto follow-through.

## Expected Key Behaviors

- present the correction plan with continuation mode / blocker disclosure before execution
- switch authorization state from `analysis-only` to `post-plan-confirmation`
  only after explicit approval
- execute the confirmed repairs
- re-enter the current repair task through `continue` only after repair
  execution actually ran
- keep using `continue` after commit until the task reaches `finish-work` or
  `reached-task-close`

## Must Not

- must not treat `--auto` as active before explicit execution approval
- must not skip the Step 8 approval boundary
- must not jump directly from post-plan-confirmation execution to
  `finish-work` without the `continue` loop
- must not lose the continuation-mode disclosure when transitioning into
  `post-plan-confirmation`

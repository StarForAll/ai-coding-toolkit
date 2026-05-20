# 14 Post-Plan-Confirmation With Auto

## Purpose

Verify that an analysis-first run with `--auto` may transition into
`post-plan-confirmation`, execute repairs, and then continue into auto
follow-through.

## Input

User input:

> Run `/workflow-repair --auto` to analyze first. After the correction plan is shown, the user explicitly accepts all or partial execution, repairs succeed sufficiently, and the close-out flow remains safe.

## Expected Mode

Analysis-first repair run that transitions into execution-time
`post-plan-confirmation` and then enters auto follow-through.

## Expected Key Behaviors

- present the correction plan with continuation mode / blocker disclosure before execution
- switch authorization state from `analysis-only` to `post-plan-confirmation`
  only after explicit approval
- execute the confirmed repairs
- continue into Step 12 auto wrap-up only after repair execution actually ran

## Must Not

- must not treat `--auto` as active before explicit execution approval
- must not skip the Step 8 approval boundary
- must not lose the continuation-mode disclosure when transitioning into
  `post-plan-confirmation`

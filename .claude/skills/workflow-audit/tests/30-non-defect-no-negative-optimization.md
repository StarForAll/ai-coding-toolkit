# 30 Non-defect No Negative Optimization

## Purpose

Verify that `workflow-audit` does not convert evidence-backed non-defects into
cleanup or optimization work, especially when the current behavior is
intentional, operationally valid, and aligned with actual development use.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/` and tell me whether we should unify all
> CLI carrier layouts so they look more symmetrical, even if the current setup
> already works.

## Expected Mode

Lightweight static mode unless Step 2 findings prove runtime validation is
required to decide whether the asymmetry is a real defect.

## Expected Key Behaviors

- treat the user's proposed optimization as a hypothesis, not a defect
- check whether the current asymmetry is supported by official docs, repo-local
  evidence, and practical development-use evidence
- if the current setup is evidence-backed and behaviorally sound, classify the
  idea as a false alarm / non-defect rather than a confirmed issue
- avoid recommending cleanup that would remove a valid primary vs conditional
  carrier split only for cosmetic symmetry

## Must Not

- must not create a confirmed issue solely because the current setup is less
  uniform than another possible design
- must not emit a fix direction for an evidence-backed non-defect
- must not frame negative optimization as required maintenance

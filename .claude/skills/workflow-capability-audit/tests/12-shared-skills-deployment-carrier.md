# 12 Shared Skills Deployment Carrier Coverage

## Purpose

Verify that `workflow-capability-audit` tracks `.agents/skills/` as a shared deployment carrier for OpenCode and Codex in the Workflow-Dependent Trellis-Native Surface Matrix.

## Input

User input:

> Audit whether the new Trellis version changed capabilities that affect `docs/workflows/新项目开发工作流/`.

## Expected Mode

Task-based full compatibility audit.

## Expected Key Behaviors

- `capability-report.md` must include a row with `shared-skills-deployment-carrier` in the Workflow-Dependent Trellis-Native Surface Matrix
- the row must have `not-applicable` for Claude (no `.agents/skills` path in Claude surface)
- the row must have `adopted-compatible` for OpenCode when `.agents/skills/` exists in both A and B fixtures
- the row must have `adopted-compatible` for Codex when `.agents/skills/` exists in both A and B fixtures
- if `.agents/skills/` exists in A but not in B, both OpenCode and Codex must classify as `missing-but-valuable`

## Must Not

- must not classify the shared-skills carrier as `not-applicable` for OpenCode or Codex when `.agents/skills/` exists in the A fixture
- must not omit the shared-skills carrier row from the dependent surface matrix

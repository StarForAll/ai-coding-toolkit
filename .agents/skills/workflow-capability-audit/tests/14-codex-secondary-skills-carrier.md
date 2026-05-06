# 14 Codex Secondary Skills Carrier Coverage

## Purpose

Verify that `workflow-capability-audit` tracks `.codex/skills/` as a distinct Codex-local/secondary skills carrier (TN-012) in the Workflow-Dependent Trellis-Native Surface Matrix, and that it does NOT replace or merge with the shared-skills-deployment-carrier.

## Input

User input:

> Audit whether the new Trellis version changed capabilities that affect `docs/workflows/新项目开发工作流/`.

## Expected Mode

Task-based full compatibility audit.

## Expected Key Behaviors

- `capability-report.md` must include a row with `codex-secondary-skills-carrier` in the Workflow-Dependent Trellis-Native Surface Matrix
- the row must have `not-applicable` for Claude (no `.codex/skills` path in Claude surface)
- the row must have `not-applicable` for OpenCode (no `.codex/skills` path in OpenCode surface)
- the row must have `adopted-compatible` for Codex when `.codex/skills/` exists in both A and B fixtures
- if `.codex/skills/` exists in A but not in B, Codex must classify as `missing-but-valuable`
- the row must NOT overlap with or replace the `shared-skills-deployment-carrier` row (which covers `.agents/skills/`)
- both carriers must appear as separate rows in the dependent surface matrix

## Must Not

- must not merge `codex-secondary-skills-carrier` into `shared-skills-deployment-carrier`
- must not classify the codex-secondary-skills carrier as `not-applicable` for Codex when `.codex/skills/` exists in the A fixture
- must not omit the codex-secondary-skills carrier row from the dependent surface matrix
- must not use `codex-native-skills-carrier` as the carrier name (it is secondary/local, not native)

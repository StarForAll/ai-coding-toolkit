---
name: workflow-capability-audit
description: Use when auditing whether `docs/workflows/新项目开发工作流/` remains compatible after a newer Trellis version changes baseline capabilities, carrier models, or upgrade-sensitive mechanics.
---

# workflow-capability-audit

`workflow-capability-audit` is the repo-local maintainer entry point for **Trellis version-upgrade compatibility** of `docs/workflows/新项目开发工作流/`.

If this file conflicts with `.trellis/spec/skills/workflow-capability-audit.md`, treat the spec file as the behavioral source of truth.

## Purpose

Use this skill to:

- decide whether a newer Trellis version changed capabilities/mechanics that affect the workflow
- compare a fresh Trellis baseline (`A`) and a fresh workflow-embedded state (`B`)
- build a capability/compatibility matrix across workflow-managed and workflow-dependent Trellis-native surfaces
- decide whether the workflow needs normal compatibility adaptation or structural-break follow-up

Do not use this skill to:

- review ordinary business code
- re-audit same-version workflow maintenance
- auto-execute workflow source remediation before the user confirms the audit conclusion

## Trigger Conditions

Trigger this skill when the user wants to:

- check whether a newer Trellis version is still compatible with `docs/workflows/新项目开发工作流/`
- audit missing / disabled / incompatible Trellis-native capabilities after version upgrade
- confirm whether the workflow now needs compatibility fixes or structural-break handling

## Scope

First-version support is limited to:

- `docs/workflows/新项目开发工作流/`

If another workflow root is requested, stop and report that first-version support is limited to this workflow.

## Version Gate First

Before any task creation or audit artifact creation:

1. Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
2. Run `trellis --version`
3. Apply semantic-version comparison

Rules:

- if `COMPATIBLE_TRELLIS_VERSION` is missing:
  - stop and ask the user to supply it
  - after the user supplies it, you may perform the sole allowed pre-audit source edit:
    - write the supplied value into `workflow_assets.py`
  - rerun the gate
- if `trellis --version` fails or returns empty output:
  - stop as `Blocked / Environment Error`
- if version parsing fails:
  - stop as `Blocked / Version Parse Error`
- if `current == compatible`:
  - stop
- if `current < compatible`:
  - stop as unsupported older-version direction
- only if `current > compatible`:
  - continue into full audit

For the same numeric base version:

- `beta` < `rc` < stable (no prerelease marker)

Use the fixed version-gate stop template from `references/version-gate-stop-template.md`.

## Task Model

This skill is task-based only **after** the version gate passes.

Rules:

- if no active task exists: create a top-level audit task
- if a non-audit active task exists: create a dedicated child audit task and switch into it immediately
- maintain:
  - `prd.md`
  - `capability-report.md`

`capability-report.md` is the single evolving evidence artifact across audit, confirmed fix scope, applied corrections, and post-fix revalidation.

## A/B Fixtures

Create fresh temporary projects only after the version gate passes:

- `A`: fresh Trellis baseline
- `B`: fresh Trellis baseline + installed current workflow

Rules:

- do not reuse user-supplied A/B roots
- preserve A/B through the whole compatibility-fix lifecycle
- destroy A/B only after correction is complete and the user gives explicit final confirmation

## Main Audit Flow

### Step A: Discover current Trellis baseline capabilities

Use fresh `A` to discover current-version Trellis capabilities dynamically.

Do not rely on a hardcoded fixed capability list.

### Step B: Build fresh workflow-embedded state

Use fresh `B` to discover what the workflow:

- manages directly
- patches
- disables intentionally
- depends on without installer ownership

### Step C: Build capability matrix

Use one unified matrix organized by capability rows.

Every row must include:

- `Capability ID`
- `Capability`
- `Surface`
- `Latest Trellis Mechanism / Benefit`
- `Discovery Source`
- `Claude Evidence`
- `OpenCode Evidence`
- `Codex Evidence`
- `Claude Classification`
- `OpenCode Classification`
- `Codex Classification`
- `Overall Summary`
- `Structural Signal`
- `Adaptation Decision`

Surfaces must be separated into:

- `workflow-managed surface`
- `workflow-dependent Trellis-native surface`

### Step D: Structural-Break Judgment

Include explicit judgment:

- `no`
- `possible`
- `yes`

If the result is `possible`:

- stop
- require explicit user confirmation
- use the dedicated template from `references/structural-break-possible-template.md`

### Step E: Stop and wait

After producing the audit conclusion:

- stop
- wait for user confirmation
- do not auto-enter workflow source remediation

## Classification Rules

Per-CLI classification supports:

- `adopted-compatible`
- `patched-compatible`
- `intentionally-disabled`
- `present-but-incompatible`
- `missing-but-valuable`
- `unclear`
- `not-applicable`

`Overall Summary` uses the most severe / most action-demanding state.

Severity order:

1. `present-but-incompatible`
2. `missing-but-valuable`
3. `unclear`
4. `intentionally-disabled`
5. `patched-compatible`
6. `adopted-compatible`
7. `not-applicable`

## Identity Rules

### Capability ID

Use:

- `WM-*` for workflow-managed rows
- `TN-*` for workflow-dependent Trellis-native rows

Once assigned, IDs remain stable through the whole audit/fix lifecycle.

Later supplemental insertion must not trigger renumbering.

### Discovery Source

Allowed first-version values:

- `ai-discovered`
- `supplemental-confirmed`

## Supplemental Capability Loop

If the AI misses a capability and the user points it out after one discovery pass:

1. treat it as a hypothesis
2. validate it using the same audit round
3. reuse the same A/B fixtures
4. reuse the same `capability-report.md`

If confirmed:

- insert it into the correct logical matrix position
- mark `Discovery Source = supplemental-confirmed`

If not confirmed:

- do not add it to the matrix
- record it under `Rejected / Unconfirmed Supplemental Points`

## References

Read these when needed:

- `references/version-gate-stop-template.md`
- `references/structural-break-possible-template.md`
- `references/capability-report-template.md`
- `references/input-template.md`
- `references/execution-runbook.md`

The canonical execution engine is:

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`

## Tests

Use persisted scenario files under `tests/` to validate first-version behavior boundaries.

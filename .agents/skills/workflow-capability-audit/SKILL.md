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

## Input Contract

- `current_cli` — **always pass this value** inferred from the current runtime:
  - in Claude Code: `claude`
  - in OpenCode: `opencode`
  - in Codex CLI: `codex`
  - the script does not auto-detect the CLI; the caller is responsible for inference
  - values outside `claude|opencode|codex` must be rejected before any full-audit task or fixture setup begins
- `workflow_path` — default and only supported value in first version: `docs/workflows/新项目开发工作流/`

## Version Gate First

Before any task creation or audit artifact creation:

1. Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
2. Run `trellis -v`
3. Apply semantic-version comparison

Rules:

- if `COMPATIBLE_TRELLIS_VERSION` is missing:
  - stop and ask the user to supply it
  - after the user supplies it, you may perform the sole allowed pre-audit source edit:
    - write the supplied value into `workflow_assets.py`
  - rerun the gate
- if `trellis -v` fails or returns empty output:
  - stop as `Blocked / Environment Error`
- when running under Codex, do not treat a Codex-local `trellis init` runtime
  failure during A/B fixture creation as sufficient proof that the user's actual
  machine environment is broken
  - distinguish Codex runtime evidence from real shell / non-Codex executor behavior
  - require one non-Codex recheck before concluding that the machine environment
    itself is broken
  - if no non-Codex recheck is available, stop as evidence gap rather than
    asserting a confirmed machine-environment defect
- if version parsing fails:
  - stop as `Blocked / Version Parse Error`
- if `current == compatible`:
  - stop
- if `current < compatible`:
  - stop as `Blocked / Unsupported Direction`
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
- if a `workflow-capability-audit` task is already active: stop and ask the user to resume or complete the existing audit before starting a new full audit
- if child-audit setup fails after task creation, rollback must remove the created task directory, restore the prior active-task pointer, and remove any stale parent `children` link
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
- do not recycle earlier unrelated fixtures
- preserve A/B through the whole compatibility-fix lifecycle
- destroy A/B only after correction is complete and the user gives explicit final confirmation

## Main Audit Flow

The audit follows a **script-driven + AI-review** hybrid model. The canonical execution engine (`docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`) generates the baseline matrix; the AI then reviews completeness, handles supplemental capabilities, and manages the fix lifecycle.

For exact invocation forms, see `references/execution-runbook.md`.

### Step A: Run the canonical execution engine

Run the script to:

- pass the version gate
- create the audit task
- create fresh A/B fixtures
- generate initial `prd.md`
- generate `capability-report.md` with the baseline capability matrix

The script discovers managed-surface rows from `workflow_assets.py` specs and dependent-surface rows from known Trellis-native carrier definitions (project-rules, claude-hooks, opencode-plugin, codex-hooks, implementation-agent, runtime-workflow-guide, shared-skills-deployment-carrier, claude-native-skills-carrier, opencode-native-skills-carrier, opencode-lib-carrier, trellis-hooks-script-carrier, codex-secondary-skills-carrier).

First-version limitation:

- dependent-surface discovery starts from a maintained known-carrier seed list in the execution engine
- newly introduced Trellis-native carriers may still require the AI supplemental capability loop before they enter the formal matrix

### Step B: AI reviews the generated report

After the script completes, review `capability-report.md` for:

- **completeness** — are there capabilities visible in the A/B fixtures that the script missed?
- **classification accuracy** — do the per-CLI classifications match the actual file evidence?
- **structural signals** — does the auto-generated structural-break judgment need refinement based on closer inspection?

### Step C: Handle supplemental capabilities

If the AI or user identifies an omitted capability after the initial discovery pass, use the supplemental capability loop (see [Supplemental Capability Loop](#supplemental-capability-loop)). Reuse the same A/B fixtures and the same `capability-report.md`.

### Step D: Finalize structural-break judgment

Include explicit judgment:

- `no`
- `possible`

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

`capability-report.md` rows must preserve the emitted first-version matrix column order:

- `Claude Evidence`
- `Claude Classification`
- `OpenCode Evidence`
- `OpenCode Classification`
- `Codex Evidence`
- `Codex Classification`

Per-CLI classification supports:

- `adopted-compatible`
- `patched-compatible`
- `intentionally-disabled`
- `present-but-incompatible`
- `missing-but-valuable`
- `unclear`
- `present-but-gated`
- `not-applicable`

`Overall Summary` uses the most severe / most action-demanding state.

Severity order:

1. `present-but-incompatible`
2. `missing-but-valuable`
3. `unclear`
4. `present-but-gated`
5. `intentionally-disabled`
6. `patched-compatible`
7. `adopted-compatible`
8. `not-applicable`

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

## Compatibility-Version Anchor Update Rules

- the initialization exception above is the sole allowed pre-audit source edit
- after a confirmed successful audit, `COMPATIBLE_TRELLIS_VERSION` **must** be set to the exact `trellis -v` output value in `workflow_assets.py`; this is a mandatory post-audit step, not optional
- anchor write-back must occur only after `--task-dir` is validated as a real `workflow-capability-audit` task for the confirmed fix-lifecycle update
- the version value written must be the literal string from `trellis -v`, including any prerelease suffix (e.g., `-rc.3`, `-beta.1`)
- do not round up to a stable version (e.g., writing `"0.5.0"` when `trellis -v` returns `"0.5.0-rc.3"`) — this breaks downstream version gates in `workflow-audit` and causes false re-triggers in subsequent `workflow-capability-audit` runs
- this rule applies even if the workflow was already compatible as-is or no workflow source edits were needed beyond the initialization exception

### Known limitation: coarser classification for workflow-managed surfaces

The supplemental path classifies capabilities by file existence alone (adopted-compatible / missing-but-valuable / not-applicable / unclear). It cannot derive patched-compatible or intentionally-disabled because it lacks the `spec.category` metadata from `workflow_assets.py` that the main audit path uses. For supplemental workflow-managed capabilities, adopted-compatible is the default classification; finer categorization belongs to the AI post-review phase.

### Known limitation: Codex hook carrier scans file presence, not runtime activation truth

- `codex-hooks-and-config-carrier` intentionally checks file/config carrier presence such as `.codex/hooks.json`, `.codex/config.toml`, and `.codex/hooks/inject-workflow-state.py`
- it does **not** treat `.codex/hooks/session-start.py` as a required compatibility path in the current model
- the emitted `present-but-gated` classification means the carrier exists on disk but real activation can still depend on user-level feature flags and hook approval outside workflow-managed files
- capability audit therefore does not prove Codex runtime activation end to end by file presence alone

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

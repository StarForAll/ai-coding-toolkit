---
name: workflow-capability-audit
description: Use when auditing whether `docs/workflows/新项目开发工作流/` remains compatible under newer-version drift or an explicitly requested same-version full audit.
---

# workflow-capability-audit

`workflow-capability-audit` is the repo-local maintainer entry point for **Trellis compatibility audit** of `docs/workflows/新项目开发工作流/`.

If this file conflicts with `.trellis/spec/skills/workflow-capability-audit.md`, treat the spec file as the behavioral source of truth.

## Version History

- `v1.2`: allow full audit only on newer-version drift and add explicit same-version continuation override
- `v1.1`: surfaced sync rules, error/edge handling, Codex inline execution constraints, and explicit scenario-test/reference contracts
- `v1.0`: established the first-version capability-audit contract

## Purpose

Use this skill to:

- decide whether the current Trellis version relationship to the compatibility anchor changed capabilities/mechanics that affect the workflow
- allow explicit same-version full audit when the user wants deeper confirmation even without version drift
- compare a fresh Trellis baseline (`A`) and a fresh workflow-embedded state (`B`)
- build a capability/compatibility matrix across workflow-managed and workflow-dependent Trellis-native surfaces
- decide whether the workflow needs normal compatibility adaptation or structural-break follow-up

Do not use this skill to:

- review ordinary business code
- re-audit same-version workflow maintenance unless the user explicitly requests a same-version full audit
- auto-execute workflow source remediation before the user confirms the audit conclusion

## Trigger Conditions

Trigger this skill when the user wants to:

- check whether the current Trellis version relationship to the compatibility anchor is still compatible with `docs/workflows/新项目开发工作流/`
- audit missing / disabled / incompatible Trellis-native capabilities after version change or drift
- continue into a same-version full audit explicitly instead of stopping at the default equal-version gate
- confirm whether the workflow now needs compatibility fixes or structural-break handling

## Scope

First-version support is limited to:

- `docs/workflows/新项目开发工作流/`

If another workflow root is requested, stop and report that first-version support is limited to this workflow.

## Input

- `current_cli` — pass this value inferred from the current runtime whenever the run may continue past the version gate:
  - in Claude Code: `claude`
  - in OpenCode: `opencode`
  - in Codex CLI: `codex`
  - the script does not auto-detect the CLI; the caller is responsible for inference
  - version-gate-only calls may omit it because they stop before any CLI-specific full-audit setup begins
  - once execution may continue past the version gate into full-audit setup, values outside `claude|opencode|codex` must be rejected before any task or fixture setup begins
- `workflow_path` — default and only supported value in first version: `docs/workflows/新项目开发工作流/`
- `allow_equal_version_continue` — optional explicit override:
  - default: `false`
  - set to `true` only when the user explicitly wants a same-version full audit
  - has effect only when `current == compatible`

## Supported Surface

Current first-version audit coverage is limited to the same three CLI surfaces
implied by `current_cli`:

- `Claude Code`
- `OpenCode`
- `Codex`

Other repo-local hidden directories such as `.kiro/` and `.qoder/` may exist as
Trellis carrier surfaces in this repository, but they are not part of this
skill's first-version matrix unless the workflow-side managed-surface contract
is explicitly expanded.

## Execution Constraints

- when `current_cli = codex` in this repository, keep the audit inline in the
  main Codex session
- follow `.trellis/spec/platforms/codex-workflow-behavior.md`
- do not manually spawn subagents for Step B read-only analysis or official-doc
  comparison work
- treat the Codex execution-model rule as separate from the Codex runtime
  boundary around fresh `trellis init` execution

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
  - default: stop
  - continue only when the explicit same-version continuation input is provided
- if `current > compatible`:
  - continue into full audit
- if `current < compatible`:
  - abort with a non-zero workflow-contract violation error
  - do not treat this as a normal audit path

For the same numeric base version:

- `beta` < `rc` < stable (no prerelease marker)

Use the fixed version-gate stop template from `references/version-gate-stop-template.md`.

## Task Model

This skill is task-based only **after** `current > compatible` or explicit same-version continuation is allowed.

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

Create fresh temporary projects only after `current > compatible` or explicit same-version continuation is allowed:

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

- pass the version gate or explicit same-version continuation gate
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

For Claude Code / OpenCode / Codex native-adaptation judgments, combine both:

- the latest official CLI documentation available at audit time
- workflow-source evidence plus, when available, the A/B fixtures or runtime observations

Minimum workflow-source evidence pack:

- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- the relevant platform README under `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/README.md`
- the workflow source definitions behind the claim (`commands/workflow_assets.py`, `commands/install-workflow.py`, `commands/upgrade-compat.py`)
- the temporary A/B fixture files that show the installed target-project result

When filling `## Native CLI Adaptation Evidence`, capture at least:

- per-CLI official docs source checked
- per-CLI workflow-source / A/B evidence checked
- per-CLI agreement / discrepancy status
- discrepancy resolution and conservative-classification rationale when a disagreement exists

If official docs and workflow-source / A/B evidence disagree:

- record the discrepancy explicitly in `capability-report.md`
- explain whether it is a workflow-source contract issue, stale product documentation, or an unresolved evidence gap
- prefer `unclear`, `present-but-gated-expected`, or another evidence-backed conservative value over unsupported assumptions
- if the generated `capability-report.md` does not already contain the `## Native CLI Adaptation Evidence` section, add it during Step B before finalizing the audit conclusion

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

## Output

This skill has three output modes:

1. Version-gate stop:
   - use `references/version-gate-stop-template.md`
   - do not create a task, `prd.md`, `capability-report.md`, or A/B fixtures
2. Full task-based audit:
   - maintain task-scoped `capability-report.md`
   - follow `references/capability-report-template.md`
   - stop after the audit conclusion and wait for user confirmation
3. Structural-break possible stop:
   - use `references/structural-break-possible-template.md`
   - require explicit user confirmation before any deeper analysis or normal adaptation recommendation continues

## Error Handling And Edge Cases

- `equal-version-stop`:
  - trigger: `trellis -v == COMPATIBLE_TRELLIS_VERSION` and no explicit same-version continuation input is provided
  - action: stop before task creation, `prd.md`, `capability-report.md`, or A/B fixtures
- `missing-compatible-anchor`:
  - trigger: `COMPATIBLE_TRELLIS_VERSION` missing
  - action: ask the user for the value; only the compatibility-anchor write is allowed before the audit
- `environment-error`:
  - trigger: `trellis -v` fails or returns empty output
  - action: stop before full audit setup
- `version-parse-error`:
  - trigger: semantic-version parsing fails
  - action: stop immediately
- invalid input:
  - trigger: unsupported workflow root or invalid `current_cli`
  - action: reject before task or fixture setup
- duplicate active capability audit:
  - trigger: a `workflow-capability-audit` task is already active
  - action: stop and resume/complete the existing audit first
- Codex runtime-only fixture failure:
  - trigger: `trellis init` fails only under the current Codex runtime
  - action: require non-Codex recheck or report an evidence gap rather than asserting a confirmed machine-environment defect
- supplemental capability unconfirmed:
  - trigger: the omitted point is not supported by the current A/B evidence
  - action: record it under `Rejected / Unconfirmed Supplemental Points` and do not add a matrix row
- structural-break possible:
  - trigger: final structural judgment is `possible`
  - action: use the dedicated stop template and wait for explicit user confirmation

### Contract-violation path

- `older-version-contract-violation`:
  - trigger: `current < compatible`
  - action: abort with a non-zero error and treat it as a workflow-contract violation instead of a normal gate result
  - note: this is **not** emitted as a `gate_result`; the script raises a `RuntimeError` instead

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
- `present-but-gated-unexpected`
- `present-but-gated-expected`
- `not-applicable`

`Overall Summary` uses the most severe / most action-demanding state.

Severity order:

1. `present-but-incompatible`
2. `missing-but-valuable`
3. `unclear`
4. `present-but-gated-unexpected`
5. `present-but-gated-expected`
6. `intentionally-disabled`
7. `patched-compatible`
8. `adopted-compatible`
9. `not-applicable`

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
- the emitted `present-but-gated-expected` classification means the carrier exists on disk and the remaining runtime gate is an explicitly modeled design expectation, so it should remain a follow-up signal rather than an automatic structural-break trigger
- `present-but-gated-unexpected` is reserved for gated behavior that is not explicitly modeled as an expected design-time runtime gate, and it should continue to block normal adaptation recommendations
- capability audit therefore does not prove Codex runtime activation end to end by file presence alone

## References

Read these when needed:

- `references/version-gate-stop-template.md`
  - fixed output contract for version-gate termination states
- `references/structural-break-possible-template.md`
  - fixed stop-and-confirm template for `Structural-Break Judgment = possible`
- `references/capability-report-template.md`
  - task-based report contract, including `## Native CLI Adaptation Evidence`
- `references/input-template.md`
  - copyable invocation format for the first-version input contract
- `references/execution-runbook.md`
  - canonical script invocations, fix-lifecycle update flags, Codex execution note, and native-adaptation evidence follow-through

The canonical execution engine is:

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`

## Tests

Required persisted scenario files:

- `tests/01-version-equal-stop.md`
- `tests/02-missing-compatible-anchor.md`
- `tests/03-full-audit-newer-path.md`
- `tests/04-structural-break-possible-stop.md`
- `tests/05-post-analysis-supplemental-capability.md`
- `tests/06-child-audit-task-and-fixture-lifecycle.md`
- `tests/07-version-parse-error.md`
- `tests/08-environment-error.md`
- `tests/09-older-version-contract-violation.md`
- `tests/10-final-compatibility-promotion-mandatory.md`
- `tests/11-existing-active-capability-audit-stop.md`
- `tests/12-shared-skills-deployment-carrier.md`
- `tests/13-codex-runtime-boundary-recheck.md`
- `tests/14-codex-secondary-skills-carrier.md`
- `tests/15-native-cli-adaptation-evidence-contract.md`
- `tests/16-codex-inline-main-session-analysis.md`
- `tests/17-equal-version-explicit-continue.md`

Every test file must use the same structure:

- `Purpose`
- `Input`
- `Expected Mode`
- `Expected Key Behaviors`
- `Must Not`

Critical maintained behavior notes:

- `tests/15-native-cli-adaptation-evidence-contract.md` is the persisted scenario for the Native CLI Adaptation Evidence contract that is also reflected in `references/execution-runbook.md` and `references/capability-report-template.md`
- `tests/16-codex-inline-main-session-analysis.md` is the persisted scenario for the repo-local Codex inline analysis boundary

## Examples

### Example 1: Equal-version stop

User asks whether the workflow needs a Trellis compatibility audit.

Expected path:

- run the version gate first
- if `trellis -v == COMPATIBLE_TRELLIS_VERSION`, stop with `Gate Result = equal-version-stop`
- do not create a task or A/B fixtures

### Example 2: Equal-version explicit continue

User asks for the same compatibility audit and explicitly wants it to continue
even though the versions match.

Expected path:

- run the version gate first
- detect `trellis -v == COMPATIBLE_TRELLIS_VERSION`
- continue only when the explicit same-version continuation input is passed
- create the audit task, fresh A/B fixtures, and `capability-report.md`

### Example 3: Full newer-path audit

User asks whether the newer Trellis version changed capabilities that affect
`docs/workflows/新项目开发工作流/`.

Expected path:

- pass `current_cli`
- run the canonical execution engine
- review and update `capability-report.md`
- stop for user confirmation before any workflow source remediation

### Example 4: Unexpected older-version contract violation

User runs the audit in an environment where `trellis -v` is older than the workflow compatibility anchor.

Expected path:

- detect `current < compatible`
- abort with a non-zero error
- treat the state as a workflow-contract violation rather than a normal audit path

### Example 5: Codex inline audit analysis

User asks for the same compatibility audit from a Codex session in this
repository.

Expected path:

- keep the audit in the main Codex session
- do not manually spawn subagents for Step B analysis
- still apply the separate Codex runtime boundary rule if fresh `trellis init`
  fails only inside the current Codex runtime

## Sync Rules

Behavioral source of truth:

- `.trellis/spec/skills/workflow-capability-audit.md`

Executable entry artifacts:

- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`

Canonical runtime artifacts:

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`

Behavior-affecting changes must update the spec, both entry artifacts, and any
affected runtime artifacts in the same change.

When behavior changes affect maintained references/tests, update the affected
counterparts in the same change, including:

- `.agents/skills/workflow-capability-audit/references/*`
- `.claude/skills/workflow-capability-audit/references/*`
- `.agents/skills/workflow-capability-audit/tests/*`
- `.claude/skills/workflow-capability-audit/tests/*`

When the Native CLI Adaptation Evidence contract changes, also review/update:

- `references/execution-runbook.md`
- `references/capability-report-template.md`
- `tests/15-native-cli-adaptation-evidence-contract.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/README.md`

When the repo-local Codex execution model changes, also review/update:

- `.trellis/spec/platforms/codex-workflow-behavior.md`
- `references/execution-runbook.md`
- `tests/16-codex-inline-main-session-analysis.md`

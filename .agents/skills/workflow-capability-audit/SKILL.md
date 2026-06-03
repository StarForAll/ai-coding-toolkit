---
name: workflow-capability-audit
description: Use when auditing whether `docs/workflows/新项目开发工作流/` remains compatible under newer-version drift or an explicitly requested same-version full audit.
---

# workflow-capability-audit

> Repo-local maintainer skill contract for auditing whether `docs/workflows/新项目开发工作流/` remains compatible under Trellis version drift or an explicitly requested same-version full audit.

---

## Purpose

`workflow-capability-audit` exists to judge **Trellis compatibility** for the repo-local workflow source under `docs/workflows/新项目开发工作流/`.

This skill covers:

- pre-run Trellis version gating for workflow compatibility audits
- fresh `/tmp + trellis init` baseline discovery for the current Trellis version
- A/B comparison between:
  - `A`: fresh Trellis baseline
  - `B`: fresh Trellis baseline prepared for current workflow install, with formal embed continuation delegated to a human-operated shell
- capability/compatibility judgment for:
  - workflow-managed surfaces
  - Trellis-native capabilities that the workflow depends on even when they are not installer-managed
- structural-break risk judgment before any workflow source adaptation work starts
- explicit same-version full-audit continuation when the user requests deeper confirmation

It does not cover:

- ordinary business code review
- routine workflow-source drift analysis when the Trellis version has not changed and no explicit same-version full audit was requested
- automatic workflow source remediation before the user confirms the audit conclusion

---

## Trigger Conditions

Use `workflow-capability-audit` when the user wants to:

- determine whether the current Trellis version relationship to the compatibility anchor changed capabilities or mechanics that affect `docs/workflows/新项目开发工作流/`
- continue into a same-version full audit when the user explicitly requests deeper confirmation
- compare a fresh Trellis baseline against a workflow-embedded project to judge missing/disabled/incompatible capabilities
- decide whether the workflow needs compatibility adaptation after Trellis version change or drift
- validate whether a suspected omitted Trellis capability should enter the compatibility matrix after the AI completes a discovery pass

Do not use it for:

- same-version workflow maintenance with no Trellis version change and no explicit same-version full audit request
- ordinary workflow embed/install correctness checks where capability compatibility is not the central question
- generic code review or implementation quality analysis

---

## Scope Boundary

First-version hard scope:

- target workflow root is fixed to `docs/workflows/新项目开发工作流/`
- no generic `docs/workflows/*` support in first version

If another workflow target is requested, stop and report that first-version support is limited to `docs/workflows/新项目开发工作流/`.

### Supported CLI Surface

Current first-version audit coverage is limited to the same three CLI surfaces
implied by `current_cli`:

- `Claude Code`
- `OpenCode`
- `Codex`

Other repo-local hidden directories such as `.kiro/` and `.qoder/` may exist as
Trellis carrier surfaces in this repository, but they are not part of this
skill's first-version matrix unless the workflow-side managed-surface contract
is explicitly expanded.

---

## Version Gate

### Step 0 Comes First

`workflow-capability-audit` starts with version gating **before**:

- task creation
- `prd.md`
- `capability-report.md`
- A/B fixture creation
- any audit execution beyond the gate itself

### Canonical Compatibility Anchor

The workflow-side compatibility anchor is:

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- constant name: `COMPATIBLE_TRELLIS_VERSION`

This constant is the **single concrete value source**.

Rules:

- other skill/spec/test/docs surfaces may reference the rule
- other surfaces must not duplicate the literal version value
- this single-source rule must remain documented in repo-local spec

### Missing Anchor Rule

If `COMPATIBLE_TRELLIS_VERSION` is missing:

1. stop and ask the user to provide the value
2. once the user provides it, `workflow-capability-audit` may perform one narrowly-scoped pre-audit source edit:
   - write the supplied value into `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
3. rerun version gating

This is the **sole allowed pre-audit source edit exception**.

### Runtime Version Source

For first-version design, treat:

- `trellis -v`
- fresh `trellis init` output `.trellis/.version`

as the same source lineage from the current Trellis version.

Version gating uses `trellis -v` as the operational check.

### Comparison Direction Rules

Version-direction judgment must use **semantic-version comparison**, not raw string ordering.

For the same numeric base version:

- `beta` < `rc` < stable (no prerelease marker)

If version parsing fails:

- terminate immediately
- classify as `Blocked / Version Parse Error`

Allowed outcomes:

1. `current == COMPATIBLE_TRELLIS_VERSION`
   - default: terminate execution
   - explain that no full compatibility audit is needed unless the user explicitly requests a same-version full audit
   - explicit override: allow the full audit path when the caller passes the dedicated continuation input

2. `current > COMPATIBLE_TRELLIS_VERSION`
   - proceed to full audit

3. `current < COMPATIBLE_TRELLIS_VERSION`
   - treat this as a workflow-contract violation
   - abort with a non-zero error instead of entering the normal audit path

### Environment Failure Rule

If `trellis -v` fails or returns empty output:

- terminate immediately
- classify as `Blocked / Environment Error`

### Codex Runtime Boundary

When the current executor is Codex and the audit reaches a runtime step that
depends on fresh `trellis init` execution for A/B baseline creation:

- do not treat a Codex-local `trellis init` failure as sufficient proof that the
  user's actual machine environment is broken
- distinguish `runtime command output under Codex` from `real shell or non-Codex
  executor behavior on the same machine`
- if the failure is observed only under Codex, classify it as a Codex runtime
  boundary / evidence-gap condition until the same step is rechecked outside Codex
- do not convert this condition directly into `Blocked / Environment Error` for
  the user's machine without a non-Codex recheck

Minimum recheck rule:

- if shell, Claude Code, or OpenCode can run the same `trellis init` step on the
  same machine, that result is the environment truth source
- if no non-Codex executor is available for recheck, stop with an evidence-gap
  explanation instead of asserting that the machine environment is broken

### Version-Gate Output Contract

Version-gate termination states must use a dedicated fixed template/reference.

First-version template strategy:

- one unified template
- distinguished by `Gate Result`

Expected `Gate Result` values:

- `equal-version-stop`
- `missing-compatible-anchor`
- `environment-error`
- `version-parse-error`

---

## Input Contract

Natural language is allowed, but the recommended contract is:

- `workflow_path`
  - default and only supported value in first version: `docs/workflows/新项目开发工作流/`
- `current_cli`
  - pass this value inferred from the current runtime whenever the run may continue past the version gate:
    - in Claude Code: `claude`
    - in OpenCode: `opencode`
    - in Codex CLI: `codex`
  - the script does not auto-detect the CLI; the caller is responsible for inference
  - version-gate-only calls may omit it because they stop before any CLI-specific full-audit setup begins
  - once execution may continue past the version gate into full-audit setup, values outside `claude|opencode|codex` must be rejected before any task or fixture setup begins
- `allow_equal_version_continue`
  - optional boolean
  - default: `false`
  - required when the user explicitly wants a same-version full audit
  - has effect only when `current == compatible`
- `continue_after_human_shell`
  - optional boolean
  - default: `false`
  - use only when resuming an existing `workflow-capability-audit` task after the human operator has manually executed the shell embed chain for `B`
- `manual_shell_evidence`
  - optional repeated evidence bullets
  - used together with `continue_after_human_shell`
  - records a short summary of what the returned human shell transcript proved

No initial `user_supplemented_capabilities` field exists in first version.

Reason:

- missed capability supplementation happens **after** one discovery pass
- it is a correction loop, not an initial input-mode switch
- manual shell continuation is also a later-round continuation path, not an initial input-mode switch

---

## Task Model

This skill is **task-based only** after `current > compatible` or an explicit same-version continuation is allowed.

### Task Creation Rules

- if no active task exists: create a top-level audit task
- if a non-audit active task exists: create a dedicated child audit task
- after child task creation, switch execution into it immediately
- if a `workflow-capability-audit` task is already active: stop and ask the user to resume or complete the existing audit before starting a new full audit
- if child-audit setup fails after task creation, rollback must remove the created task directory, restore the prior active-task pointer, and remove any stale parent `children` link

### Task Title

Default title:

`workflow-capability-audit: 新项目开发工作流`

### Main Files

Within the audit task:

- maintain `prd.md`
- maintain `capability-report.md`

`capability-report.md` is the single evolving evidence artifact across:

- initial audit
- manual shell embed continuation for `B`
- confirmed fix scope
- applied compatibility corrections
- post-fix revalidation

It must not freeze at the first audit conclusion if the workflow enters the confirmed compatibility-fix phase.

---

## A/B Fixture Rules

Full audit must create fresh temporary projects:

- `A`: fresh Trellis baseline
- `B`: fresh Trellis baseline prepared for workflow embed continuation

Rules:

- do not reuse user-supplied existing A/B roots
- do not recycle earlier unrelated fixtures

Lifecycle:

- create only after `current > compatible` or explicit same-version continuation is allowed
- preserve A/B through the whole audit/fix lifecycle
- preserve them after audit conclusion while the user reviews or confirms the next step
- preserve them through confirmed compatibility-fix and post-fix revalidation
- destroy only after compatibility correction is complete **and** the user gives explicit final confirmation

---

## Evidence Mainline

The audit follows a **script-driven + AI-review** hybrid model. The canonical execution engine generates the baseline matrix; the AI then reviews completeness, handles supplemental capabilities, and manages the fix lifecycle.

### A. Run the Canonical Execution Engine

The canonical execution engine (`docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`) must:

- pass the version gate
- create the audit task
- create fresh A/B fixtures
- generate initial `prd.md`
- if the run reaches workflow embed for `B`, stop and emit the manual human-shell command chain instead of executing embed commands itself
- generate `capability-report.md`; when the human-shell boundary is reached before `B` is embedded, the report must record that pending continuation state explicitly

### A.1 Continue After Human Shell

When the human operator has manually executed the shell embed chain for `B` and returned the transcript/evidence:

- reuse the same audit task
- reuse the same A/B fixture roots from `capability-report.md`
- update `capability-report.md` to mark the manual shell continuation as completed
- rebuild the workflow-managed and workflow-dependent matrices from the existing A/B roots
- continue the audit from the same task/report instead of creating a fresh audit task

The script discovers managed-surface rows from `workflow_assets.py` specs and dependent-surface rows from known Trellis-native carrier definitions.

First-version limitation:

- dependent-surface discovery starts from a maintained known-carrier seed list in the execution engine
- newly introduced Trellis-native carriers may still require the AI supplemental capability loop before they enter the formal matrix

### B. AI Reviews the Generated Report

After the script completes, review `capability-report.md` for:

- **completeness** — are there capabilities visible in the A/B fixtures that the script missed?
- **classification accuracy** — do the per-CLI classifications match the actual file evidence?
- **structural signals** — does the auto-generated structural-break judgment need refinement based on closer inspection?

This step is where human/AI domain knowledge supplements the script's automated discovery. The capability inventory is validated against current-version evidence rather than assumed from a fixed canonical list.

#### Native CLI Adaptation Evidence Contract

When the audit judges native adaptation for Claude Code, OpenCode, or Codex,
each CLI-specific conclusion must combine **both** evidence tracks:

- the CLI vendor/project's latest official documentation available at audit time
- workflow-source evidence plus current A/B fixture evidence

Do not rely on memory alone, and do not treat one evidence track as sufficient.

Use official documentation to confirm platform-supported mechanisms such as
configuration layers, hooks/plugins, rules/instructions loading, subagent/agent
discovery, and similar carrier semantics. Use workflow-source docs and A/B
fixture evidence to confirm how the audited workflow currently uses,
constrains, or intentionally avoids those mechanisms in installed target
projects.

Minimum workflow-source evidence pack for native CLI adaptation analysis:

- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- the relevant platform README under
  `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/README.md`
- the workflow source definitions that back the claim, such as
  `docs/workflows/新项目开发工作流/commands/workflow_assets.py`,
  `docs/workflows/新项目开发工作流/commands/install-workflow.py`, and
  `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- the temporary A/B fixture files that show the installed target-project result

When recording `## Native CLI Adaptation Evidence` in `capability-report.md`,
capture at least:

- per-CLI official documentation source checked
- per-CLI workflow-source / A/B evidence checked
- per-CLI agreement / discrepancy status
- discrepancy resolution and conservative-classification rationale when a
  disagreement exists

If official documentation and workflow-source / A/B evidence disagree:

- record the discrepancy explicitly in `capability-report.md`
- explain whether it is a workflow-source contract issue, stale product
  documentation, or an unresolved evidence gap
- prefer `unclear`, `present-but-gated-expected`, or another evidence-backed
  conservative classification over unsupported assumptions

#### Codex Inline Execution Constraint

When `current_cli = codex` in this repository and `.trellis/config.yaml` keeps
`codex.dispatch_mode: inline`, Step B AI review must stay inline in the main
Codex session.

Rules:

- do not manually spawn subagents for read-only audit analysis
- do not bypass inline mode just because the audit is "only analysis"
- treat this execution-model constraint as separate from the Codex runtime
  boundary around fresh `trellis init` execution for A/B fixtures
- if the repository later changes Codex away from the inline model, update this
  skill contract together with `.trellis/spec/platforms/codex-workflow-behavior.md`

### C. Capability / Compatibility Matrix

The report must use one unified capability matrix organized by capability rows.

Each row must include at least, in the emitted first-version column order:

- `Capability ID`
- `Capability`
- `Latest Trellis Mechanism / Benefit`
- `Discovery Source`
- `Claude Evidence`
- `Claude Classification`
- `OpenCode Evidence`
- `OpenCode Classification`
- `Codex Evidence`
- `Codex Classification`
- `Overall Summary`
- `Structural Signal`
- `Adaptation Decision`

Surface is conveyed by the matrix section heading (`Workflow-Managed Surface Matrix` vs `Workflow-Dependent Trellis-Native Surface Matrix`) rather than a dedicated column.

### D. Structural-Break Judgment

`capability-report.md` must include an explicit `Structural-Break Judgment` section.

Allowed results:

- `no`
- `possible`

Rules:

- `possible` must stop the skill and require explicit user confirmation
- `possible` must use a dedicated stop-and-confirm template/reference
- do not continue into normal adaptation recommendation flow after `possible` without explicit user confirmation

### E. Stop-and-Confirm Boundary

After producing the audit conclusion, stop and wait for user confirmation.

Do not auto-enter workflow source remediation.

---

## Capability Matrix Scope

The matrix must cover **both**:

### 1. Workflow-Managed Surface

Assets directly managed by the workflow install/upgrade contract.

### 2. Workflow-Dependent Trellis-Native Surface

Trellis-native capabilities that the workflow depends on, inherits, disables, or partially absorbs even when they are not installer-managed.

First-version dependent-surface coverage includes these known Trellis-native carriers:

- project-rules-and-routing-carrier (AGENTS.md)
- claude-hooks-and-settings-carrier (.claude/settings.json, .claude/hooks, .claude/hooks/inject-workflow-state.py, .claude/hooks/session-start.py, .claude/hooks/inject-subagent-context.py)
- opencode-plugin-and-instructions-carrier (.opencode/plugins, .opencode/package.json)
- codex-hooks-and-config-carrier (.codex/hooks.json, .codex/config.toml, .codex/hooks/inject-workflow-state.py; file presence and runtime activation are separate because Codex project hooks remain trust-gated and can still be altered by higher-precedence config)
- implementation-agent-carrier (per-CLI agent directories)
- trellis-runtime-workflow-guide (.trellis/workflow.md, .trellis/scripts/task.py)
- shared-skills-deployment-carrier (.agents/skills/ — shared deployment layer for shared skills consumed by OpenCode and Codex)
- claude-native-skills-carrier (.claude/skills/ — Claude-native skills carrier)
- opencode-native-skills-carrier (.opencode/skills/ — OpenCode-native skills carrier)
- opencode-lib-carrier (.opencode/lib/ — OpenCode helper libraries)
- trellis-hooks-script-carrier (.trellis/scripts/hooks/ — Trellis-side lifecycle hook script carrier)
- codex-secondary-skills-carrier (.codex/skills/ — Codex-local/secondary skills carrier; not a replacement for shared-skills-deployment-carrier)

shared-skills-deployment-carrier covers only the shared workflow skills primary carrier .agents/skills/; codex-secondary-skills-carrier covers the Codex-local/secondary skills surface .codex/skills/; the two must not replace or merge into one another.

These two surfaces must appear as distinct sections in `capability-report.md`.

---

## Classification Model

Per-CLI classification must support:

- `adopted-compatible`
- `patched-compatible`
- `intentionally-disabled`
- `present-but-incompatible`
- `missing-but-valuable`
- `unclear`
- `present-but-gated-unexpected`
- `present-but-gated-expected`
- `not-applicable`

### Overall Summary Derivation

`Overall Summary` must be derived by the most severe / most action-demanding per-CLI classification, not by averaging.

Severity / action priority:

1. `present-but-incompatible`
2. `missing-but-valuable`
3. `unclear`
4. `present-but-gated-unexpected`
5. `present-but-gated-expected`
6. `intentionally-disabled`
7. `patched-compatible`
8. `adopted-compatible`
9. `not-applicable`

`not-applicable` is the lowest-interference state and must not override any more action-demanding state.

---

## Capability Row Identity

Each capability row must include:

- stable `Capability ID`
- explicit `Discovery Source`

### Capability ID Rules

First-version formats:

- `WM-*` for workflow-managed surface
- `TN-*` for workflow-dependent Trellis-native surface

Once assigned, the ID must remain stable through the entire audit/fix lifecycle.

If a later supplemental capability is inserted into an earlier logical position:

- do not renumber existing IDs
- assign the new row the next available ID in that surface family

### Discovery Source Rules

Allowed first-version enum:

- `ai-discovered`
- `supplemental-confirmed`

No free-text source labels in first version.

---

## Supplemental Capability Loop

If the AI completes a discovery pass and the user points out an omitted capability:

1. treat the point as a hypothesis
2. validate it against current-version evidence using the **same** audit round
3. reuse the same A/B fixtures
4. reuse the same `capability-report.md`

If confirmed:

- insert the capability into the matrix at the correct logical location
- do not append all supplemental-confirmed items mechanically to the end
- set `Discovery Source = supplemental-confirmed`

If not confirmed:

- do not add it to the formal matrix
- record it in `Rejected / Unconfirmed Supplemental Points`

`capability-report.md` must include a dedicated `Rejected / Unconfirmed Supplemental Points` section.

### Known Limitation: Coarser Classification for Workflow-Managed Surfaces

The supplemental validation path classifies capabilities by file existence alone (`adopted-compatible` / `missing-but-valuable` / `not-applicable` / `unclear`). It cannot derive `patched-compatible` or `intentionally-disabled` because it lacks the `spec.category` metadata from `workflow_assets.py` that the main audit path uses. For supplemental workflow-managed capabilities, `adopted-compatible` is the default classification; finer categorization belongs to the AI post-review phase.

---

## Compatibility-Version Anchor Update Rules

### Initialization Exception

If `COMPATIBLE_TRELLIS_VERSION` is missing and the user provides the value:

- `workflow-capability-audit` itself may write that value into `workflow_assets.py`
- this is the sole allowed pre-audit source edit exception

### Final Promotion Rule

After a confirmed successful audit:

- `COMPATIBLE_TRELLIS_VERSION` **must** be set to the exact `trellis -v` output value in `workflow_assets.py`
- this is a mandatory post-audit step, not optional
- anchor write-back must occur only after `--task-dir` is validated as a real `workflow-capability-audit` task for the confirmed fix-lifecycle update
- the version value written must be the literal string from `trellis -v`, including any prerelease suffix (e.g., `-rc.3`, `-beta.1`)
- do **not** round up to a stable version (e.g., writing `"0.5.0"` when `trellis -v` returns `"0.5.0-rc.3"`) — this breaks downstream version gates in `workflow-audit` and causes false re-triggers in subsequent `workflow-capability-audit` runs

This rule applies even if the final conclusion is:

- the workflow is already compatible as-is
- no workflow source edits were needed beyond the initialization exception

No-fix-compatible path:

- `workflow-capability-audit` may still record the confirmed no-fix conclusion under `## Confirmed Fix Scope`
- in that path, `## Applied Corrections` may remain `- none yet`
- anchor promotion still requires recorded `## Post-Fix Revalidation` evidence plus explicit fixture-destruction finalization

---

## Validation

`workflow-capability-audit` must ship with persisted scenario test files in the same style as `workflow-audit`.

Each test file must use:

1. `Purpose`
2. `Input`
3. `Expected Mode`
4. `Expected Key Behaviors`
5. `Must Not`

First-version scenario set should cover at least:

- version equal stop
- version equal explicit continue
- missing compatibility anchor
- full newer-path audit
- older-version contract violation
- structural-break possible stop
- supplemental capability confirmation loop
- child audit task + A/B fixture lifecycle
- native CLI adaptation evidence contract
- Codex inline main-session analysis boundary

---

## Sync Rules

Behavioral source of truth:

- `.trellis/spec/skills/workflow-capability-audit.md`

Executable entry artifacts:

- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`

Canonical runtime artifacts:

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`

Behavior-affecting changes must update the spec, entry artifacts, and any affected runtime artifacts in the same change.

If behavior changes also affect references/tests, the same change must update:

- `.agents/skills/workflow-capability-audit/references/*`
- `.agents/skills/workflow-capability-audit/tests/*`
- `.claude/skills/workflow-capability-audit/references/*`
- `.claude/skills/workflow-capability-audit/tests/*`

If native CLI adaptation evidence rules change, also review whether these
repo-local maintainer docs need matching updates in the same change:

- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/commands/claude/README.md`
- `docs/workflows/新项目开发工作流/commands/opencode/README.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`

This rule currently has maintained counterparts in:

- `.trellis/spec/skills/workflow-capability-audit.md`
- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`
- `.agents/skills/workflow-capability-audit/references/execution-runbook.md`
- `.claude/skills/workflow-capability-audit/references/execution-runbook.md`
- `.agents/skills/workflow-capability-audit/references/capability-report-template.md`
- `.claude/skills/workflow-capability-audit/references/capability-report-template.md`
- `.agents/skills/workflow-capability-audit/tests/15-native-cli-adaptation-evidence-contract.md`
- `.claude/skills/workflow-capability-audit/tests/15-native-cli-adaptation-evidence-contract.md`
- `.agents/skills/workflow-capability-audit/tests/16-codex-inline-main-session-analysis.md`
- `.claude/skills/workflow-capability-audit/tests/16-codex-inline-main-session-analysis.md`
- `.trellis/spec/platforms/codex-workflow-behavior.md`
- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_capability_audit.py`

When its behavior changes, review and update those counterparts together rather
than editing only one copy.

---

## Related Files

- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`
- `.agents/skills/workflow-capability-audit/references/*`
- `.claude/skills/workflow-capability-audit/references/*`
- `.agents/skills/workflow-capability-audit/tests/*`
- `.claude/skills/workflow-capability-audit/tests/*`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`

# workflow-capability-audit Skill Specification

> Repo-local maintainer skill contract for auditing whether `docs/workflows/新项目开发工作流/` remains compatible with a newer Trellis version.

---

## Purpose

`workflow-capability-audit` exists to judge **Trellis version-upgrade compatibility** for the repo-local workflow source under `docs/workflows/新项目开发工作流/`.

This skill covers:

- pre-run Trellis version gating for workflow compatibility audits
- fresh `/tmp + trellis init` baseline discovery for the current Trellis version
- A/B comparison between:
  - `A`: fresh Trellis baseline
  - `B`: fresh Trellis baseline + current workflow install
- capability/compatibility judgment for:
  - workflow-managed surfaces
  - Trellis-native capabilities that the workflow depends on even when they are not installer-managed
- structural-break risk judgment before any workflow source adaptation work starts

It does not cover:

- ordinary business code review
- routine workflow-source drift analysis when the Trellis version has not changed
- automatic workflow source remediation before the user confirms the audit conclusion

---

## Trigger Conditions

Use `workflow-capability-audit` when the user wants to:

- determine whether a newer Trellis version changed capabilities or mechanics that affect `docs/workflows/新项目开发工作流/`
- compare a fresh Trellis baseline against a workflow-embedded project to judge missing/disabled/incompatible capabilities
- decide whether the workflow needs compatibility adaptation after Trellis version upgrade
- validate whether a suspected omitted Trellis capability should enter the compatibility matrix after the AI completes a discovery pass

Do not use it for:

- same-version workflow maintenance with no Trellis version change
- ordinary workflow embed/install correctness checks where capability compatibility is not the central question
- generic code review or implementation quality analysis

---

## Scope Boundary

First-version hard scope:

- target workflow root is fixed to `docs/workflows/新项目开发工作流/`
- no generic `docs/workflows/*` support in first version

If another workflow target is requested, stop and report that first-version support is limited to `docs/workflows/新项目开发工作流/`.

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

- `trellis --version`
- fresh `trellis init` output `.trellis/.version`

as the same source lineage from the current Trellis version.

Version gating uses `trellis --version` as the operational check.

### Comparison Direction Rules

Version-direction judgment must use **semantic-version comparison**, not raw string ordering.

For the same numeric base version:

- `beta` < `rc` < stable (no prerelease marker)

If version parsing fails:

- terminate immediately
- classify as `Blocked / Version Parse Error`

Allowed outcomes:

1. `current == COMPATIBLE_TRELLIS_VERSION`
   - terminate execution
   - explain that no Trellis version-upgrade compatibility audit is needed

2. `current > COMPATIBLE_TRELLIS_VERSION`
   - proceed to full audit

3. `current < COMPATIBLE_TRELLIS_VERSION`
   - terminate execution
   - classify as `Blocked / Unsupported Direction`

### Environment Failure Rule

If `trellis --version` fails or returns empty output:

- terminate immediately
- classify as `Blocked / Environment Error`

### Version-Gate Output Contract

Version-gate termination states must use a dedicated fixed template/reference.

First-version template strategy:

- one unified template
- distinguished by `Gate Result`

Expected `Gate Result` values:

- `equal-version-stop`
- `older-version-block`
- `missing-compatible-anchor`
- `environment-error`
- `version-parse-error`

---

## Input Contract

Natural language is allowed, but the recommended contract is:

- `workflow_path`
  - default and only supported value in first version: `docs/workflows/新项目开发工作流/`
- `current_cli`
  - optional
  - infer from runtime when possible

No initial `user_supplemented_capabilities` field exists in first version.

Reason:

- missed capability supplementation happens **after** one discovery pass
- it is a correction loop, not an initial input-mode switch

---

## Task Model

This skill is **task-based only** after the version gate passes.

### Task Creation Rules

- if no active task exists: create a top-level audit task
- if a non-audit active task exists: create a dedicated child audit task
- after child task creation, switch execution into it immediately

### Task Title

Default title:

`workflow-capability-audit: 新项目开发工作流`

### Main Files

Within the audit task:

- maintain `prd.md`
- maintain `capability-report.md`

`capability-report.md` is the single evolving evidence artifact across:

- initial audit
- confirmed fix scope
- applied compatibility corrections
- post-fix revalidation

It must not freeze at the first audit conclusion if the workflow enters the confirmed compatibility-fix phase.

---

## A/B Fixture Rules

Full audit must create fresh temporary projects:

- `A`: fresh Trellis baseline
- `B`: fresh Trellis baseline + installed current workflow

Rules:

- do not reuse user-supplied existing A/B roots
- do not recycle earlier unrelated fixtures

Lifecycle:

- create only after version gate passes
- preserve A/B through the whole audit/fix lifecycle
- preserve them after audit conclusion while the user reviews or confirms the next step
- preserve them through confirmed compatibility-fix and post-fix revalidation
- destroy only after compatibility correction is complete **and** the user gives explicit final confirmation

---

## Evidence Mainline

After version gating passes, the skill follows this fixed audit framework:

### A. Discover Current Trellis Baseline Capabilities

Using fresh `A`, determine what the current Trellis version actually provides and how it works.

This capability inventory is **dynamic** per Trellis version and must not be hardcoded as a fixed canonical capability list.

### B. Build Expected Workflow-Embedded State

Using fresh `B`, determine what the workflow actually:

- manages directly
- patches
- disables intentionally
- depends on without installer ownership

### C. Capability / Compatibility Matrix

The report must use one unified capability matrix organized by capability rows.

Each row must include at least:

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

### D. Structural-Break Judgment

`capability-report.md` must include an explicit `Structural-Break Judgment` section.

Allowed results:

- `no`
- `possible`
- `yes`

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
- `not-applicable`

### Overall Summary Derivation

`Overall Summary` must be derived by the most severe / most action-demanding per-CLI classification, not by averaging.

Severity / action priority:

1. `present-but-incompatible`
2. `missing-but-valuable`
3. `unclear`
4. `intentionally-disabled`
5. `patched-compatible`
6. `adopted-compatible`
7. `not-applicable`

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

---

## Compatibility-Version Anchor Update Rules

### Initialization Exception

If `COMPATIBLE_TRELLIS_VERSION` is missing and the user provides the value:

- `workflow-capability-audit` itself may write that value into `workflow_assets.py`
- this is the sole allowed pre-audit source edit exception

### Final Promotion Rule

After a confirmed successful audit:

- do **not** let the audit skill auto-write the final compatibility-version promotion
- the formal update belongs to the subsequent confirmed implementation/update step

This remains true even if the final conclusion is:

- the workflow is already compatible as-is
- no workflow source edits were needed beyond the initialization exception

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
- missing compatibility anchor
- full upgrade-path audit
- structural-break possible stop
- supplemental capability confirmation loop
- child audit task + A/B fixture lifecycle

---

## Sync Rules

Behavioral source of truth:

- `.trellis/spec/skills/workflow-capability-audit.md`

Executable entry artifacts:

- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`

Behavior-affecting changes must update these in the same change.

If behavior changes also affect references/tests, the same change must update:

- `.agents/skills/workflow-capability-audit/references/*`
- `.agents/skills/workflow-capability-audit/tests/*`
- `.claude/skills/workflow-capability-audit/references/*`
- `.claude/skills/workflow-capability-audit/tests/*`

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

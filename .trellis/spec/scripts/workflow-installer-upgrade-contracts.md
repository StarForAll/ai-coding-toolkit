# Workflow Installer / Upgrade Contracts

> Executable contracts for workflow installer, upgrade-analysis, and low-risk repair scripts under `docs/workflows/**/commands/`.

---

## Scenario: Trellis-based Workflow Embed / Upgrade Scripts

### 1. Scope / Trigger

- Trigger: modifying `docs/workflows/**/commands/install-workflow.py`
- Trigger: modifying `docs/workflows/**/commands/uninstall-workflow.py`
- Trigger: modifying `docs/workflows/**/commands/analyze-upgrade.py`
- Trigger: modifying `docs/workflows/**/commands/upgrade-compat.py`
- Trigger: modifying `docs/workflows/**/commands/workflow_assets.py`
- Trigger: modifying `docs/workflows/**/commands/detect-embed-state.py`
- Trigger: changing the distributed workflow command set, helper script set, install record schema, or target deployment layout
- Trigger: changing how workflow source assets are compared with deployed target-project copies
- Trigger: changing the target-project upgrade flow from analysis-first to another sequence
- Trigger: changing the embed-state model, initial-state gate, or failed-attempt recording contract

This concern is required when the change crosses these layers:

```text
workflow source assets -> expected deployed copies -> target-project live copies
-> install record / analysis report -> low-risk repair path / structural migration boundary
```

---

### 2. Signatures

#### install-workflow.py

```bash
python3 docs/workflows/<name>/commands/install-workflow.py \
  [--project-root /path/to/project] \
  [--cli claude,opencode,codex] \
  [--profile personal|outsourcing] \
  [--dry-run]
```

#### uninstall-workflow.py

```bash
python3 docs/workflows/<name>/commands/uninstall-workflow.py \
  [--project-root /path/to/project] \
  [--cli claude,opencode,codex]
```

#### analyze-upgrade.py

```bash
python3 docs/workflows/<name>/commands/analyze-upgrade.py \
  --baseline-root /path/to/A \
  --expected-root /path/to/B \
  --target-root /path/to/C \
  [--cli claude,opencode,codex] \
  [--report /tmp/report.md] \
  [--json]
```

#### upgrade-compat.py

```bash
python3 docs/workflows/<name>/commands/upgrade-compat.py --check \
  [--project-root /path/to/project] \
  [--cli claude,opencode,codex]

python3 docs/workflows/<name>/commands/upgrade-compat.py --merge \
  [--project-root /path/to/project] \
  [--cli claude,opencode,codex]

python3 docs/workflows/<name>/commands/upgrade-compat.py --force \
  [--project-root /path/to/project] \
  [--cli claude,opencode,codex]
```

#### Install Record

Target-project install record:

```text
.trellis/workflow-installed.json
```

Target-project embed-attempt record:

```text
.trellis/workflow-embed-attempt.json
```

Current embed-attempt lifecycle keys:

- `status`
- `workflow_version`
- `workflow_schema_version`
- `workflow_spec_path`
- `workflow_root`
- `target_project_root`
- `started_at`
- `updated_at`
- `cli_types`
- `last_step`

Failure-state keys that may appear when install does not complete:

- `error`
- `failed_at`

Current installer-written keys:

- `trellis_version`
- `cli_types`
- `profile`
- `commands`
- `overlay_commands`
- `added_commands`
- `disabled_commands`
- `patched_baseline_commands`
- `patched_shared_docs`
- `initial_pack`
- `bootstrap_task_removed`
- `scripts`
- `execution_cards`
- `workflow_version`
- `workflow_schema_version`

For legacy target projects, missing `workflow_version` / `workflow_schema_version`
must not block compatibility analysis by themselves once the target project is
already on the latest Trellis version.

Optional lifecycle keys may differ between install and upgrade paths, such as:

- `installed`
- `updated`
- `previous_version`
- `initial_pack`
- `bootstrap_task_removed`
- `bootstrap_cleanup_status`

Contract when these versioning keys are missing:

- do not block current upgrade analysis after the target project is already on the latest Trellis version
- treat the target project as `legacy/unknown`
- do not infer historical workflow structure from the absence alone
- continue with `A/B/C` analysis first only after the latest-Trellis prerequisite is satisfied
- after compatibility upgrade or structural migration completes, the confirmed values may be written back

Install-record write boundary:

- `workflow-installed.json` may be written only after all requested CLI deployments complete without deployment errors
- if any CLI deployment reports an error, the installer must exit non-zero before writing `workflow-installed.json`
- failed installs must not leave a misleading success-like install record behind
- installer must create `workflow-embed-attempt.json` before the first target-project write in a formal install
- installer must keep `workflow-embed-attempt.json` when install fails or when the final post-install validation does not pass
- installer may remove `workflow-embed-attempt.json` only after the post-install self-check confirms a full valid embed

Embed-attempt record contract:

- `status` must be one of:
  - `in_progress`
  - `failed`
- read-only diagnostics may synthesize `unknown` only when the attempt record is unreadable or not valid JSON; this is a diagnostic output state, not an installer-written lifecycle state
- `last_step` must identify the last completed or attempted installer phase
- `error` is optional and should be written only when the installer reaches a failed state
- read-only detection and diagnostics may surface `status`, `last_step`, and `error` to help users distinguish an interrupted install from a failed install
- absence of optional failure-state keys must not be treated as proof of a successful install

---

### 3. Contracts

#### 3.1 Source of Truth

Workflow source assets must be treated as the source of truth:

- command source: `docs/workflows/<name>/commands/*.md`
- helper scripts: `docs/workflows/<name>/commands/shell/*.py`
- managed asset registry: `docs/workflows/<name>/commands/workflow_assets.py`

Target-project deployed copies are derived state:

- Claude: `.claude/commands/trellis/*.md`
- OpenCode: `.opencode/commands/trellis/*.md`
- Claude platform-local workflow skills: `.claude/skills/*/SKILL.md`
- OpenCode platform-local workflow skills: `.opencode/skills/*/SKILL.md`
- Codex shared workflow skills: `.agents/skills/*/SKILL.md`
- Codex local / cleanup scope: `.codex/skills/*/SKILL.md` only for Codex-local project skills, optional disabled entries such as `parallel`, and duplicate shared-skill drift cleanup
- installer-managed routing block: `AGENTS.md` inside `<!-- workflow-nl-routing-start ... workflow-nl-routing-end -->`
- workflow-managed reference-doc patch carriers such as:
  - `.agents/skills/trellis-meta/references/**`
  - `.claude/skills/trellis-meta/references/**`
  - `.opencode/skills/trellis-meta/references/**`
- Trellis-native implementation agents:
  - Claude: `.claude/agents/trellis-{research,implement,check}.md`
  - OpenCode: `.opencode/agents/trellis-{research,implement,check}.md`
  - Codex: `.codex/agents/trellis-{research,implement,check}.toml`
  - workflow scripts may migrate legacy bare-name files to the Trellis-native names
  - current exception: `trellis-research` is a workflow-managed enhanced agent and may be synchronized from the authoring repo live deployment into target projects
  - `trellis-implement` / `trellis-check` remain Trellis-native and must not be overlaid
- shared helper scripts: `.trellis/scripts/workflow/*.py`
- shared project workflow guide patch: `.trellis/workflow.md`
- requirements-foundation example assets when the imported lock references them, such as:
  - `.trellis/library-assets/examples/universal-domains/product-and-requirements/**`
  - `.trellis/library-assets/examples/assembled-packs/requirements-discovery-foundation.md`
- target-project baseline guide patches under `.trellis/spec/guides/*.md` when the workflow explicitly repairs trellis-native stale operator guidance
- install-only collaboration reminder: root-level `todo.txt`

Entry-surface contract:

- user-facing routing or recommendation text must only advertise an entry surface that is actually deployed for that CLI
- if a Claude/OpenCode capability is carried only by `.claude/skills/*/SKILL.md` or `.opencode/skills/*/SKILL.md`, and no matching `.claude/commands/trellis/*.md` / `.opencode/commands/trellis/*.md` command carrier exists, the text must describe it as a skill or natural-language trigger, not as `/trellis:<name>`
- `.agents/skills/` may still participate as a shared distribution or drift-check surface, but it does not by itself justify advertising a Claude/OpenCode slash-command entry
- installer-managed `AGENTS.md` routing blocks, command-doc next-step tables, mapping docs, generated mindmaps, and installer regression fixtures must stay aligned on this entry-surface distinction

Special rule for `todo.txt`:

- `install-workflow.py` intentionally keeps `ensure_project_todo()` and may create a root-level `todo.txt`
- this file is an **install-only collaboration reminder**, not a stage gate, drift-repair surface, or uninstall restoration target
- its existence must not be treated as proof of workflow corruption, duplicate embed, or upgrade drift
- uninstall / upgrade / audit flows may mention it as contextual output, but should not classify it as a required managed capability whose absence or retention is a defect by itself
- if a future audit or compatibility analysis discusses `todo.txt`, the default interpretation must be “intentional low-stakes reminder artifact” unless another spec explicitly promotes it to a stronger contract
- `workflow-embed-attempt.json` may still record a chronological installer `last_step` related to this reminder creation (for example `ensure-todo`); this trace value is observational only and must not be interpreted as promoting `todo.txt` into a gate, required managed capability, or failure-critical contract

`workflow_assets.py` must remain the single shared definition of:

- supported CLI layouts
- patch-based baseline commands
- overlay baseline commands
- added commands
- optional disabled baseline commands
- Trellis-native implementation agents and legacy bare-name migration inputs
- helper scripts
- managed asset enumeration / detection helpers

#### 3.2 Asset Classes

Workflow embed / analysis / repair scripts must distinguish three asset classes:

1. **Patch-based baseline commands**
   - Claude / OpenCode: `continue`
   - `finish-work`
   - Codex shared skill carrier: `trellis-continue`
   - `trellis-finish-work`
   - Contract: keep Trellis baseline content, then inject workflow patch content

   Legacy `start` / baseline `record-session` are old-target compatibility inputs only. `record-session` has retired from the current fresh-baseline patch and distribution model. Native Trellis `finish-work` is the normal single-task terminal entry: it performs the current active task's `task.py archive` followed by `add_session.py`. `delivery` is a separate project-level / handoff-level workflow phase and must not be conflated with native `finish-work` semantics. Installed target projects with residual legacy `record-session` carriers or patch markers should be handled by `upgrade-compat`.

2. **Overlay baseline commands**
   - same-name commands whose deployed file is fully distributed by the workflow while semantically replacing the live baseline copy
   - current known set:
     - `brainstorm`
     - `check`
   - Contract: backup original baseline copy before install; uninstall must restore baseline copy

3. **Added commands**
   - workflow-only commands with no baseline copy to restore
   - current known set:
     - `feasibility`
     - `design`
     - `plan`
     - `project-audit`
     - `review-gate`
     - `delivery`

4. **Optional disabled baseline commands**
   - baseline commands or skills that may exist in target projects, but are intentionally overridden by this workflow into a disabled state
   - current known set:
     - `parallel`
   - Contract:
     - installer must back up the original baseline copy if present

5. **Managed enhanced agent**
   - current known set:
     - `trellis-research`
   - Contract:
     - installer must back up the target project's baseline `trellis-research` once before replacing it
     - installer must deploy the authoring-repo enhanced `trellis-research` content into the target project
     - `upgrade-compat.py --check` must detect drift in the managed enhanced research agent
     - `upgrade-compat.py --merge` / `--force` must restore the managed enhanced research agent from source
     - `uninstall-workflow.py` must restore the backed-up baseline `trellis-research`
     - this exception does not promote `trellis-implement` / `trellis-check` into workflow-managed overlays

#### Trellis 0.5+ carrier rename note

When adapting this workflow against a newer Trellis baseline, do not assume the
old Codex / command carrier names remain stable.

Current confirmed baseline drift (observed from fresh `trellis init` output):

- Claude / OpenCode command carrier:
  - `continue.md` replaces the old `start.md` baseline entrypoint
  - `record-session.md` may be absent because close-out is folded into native `finish-work.md`
- Codex shared skill carrier:
  - baseline patch targets are `trellis-continue` and `trellis-finish-work`
  - legacy `start` / `finish-work` skill names should be treated only as migration inputs, not as fresh-baseline assumptions
- Managed implementation agents:
  - deployed target filenames and in-file agent names follow `trellis-{research,implement,check}`
  - unprefixed `research` / `implement` / `check` names are legacy compatibility inputs only

Compatibility code should therefore:

- prefer current baseline names first
- fall back to legacy names only when upgrading an older installed target
- avoid treating missing legacy carriers as fresh-baseline incompatibility on current Trellis
     - installer may overwrite the target copy with a workflow-managed disabled notice
     - uninstall / force-restore paths must restore the original baseline copy when a backup exists
     - drift detection must compare the deployed disabled copy against the workflow source of truth

4.1 **Codex multi-directory skills boundary**
   - Codex may expose more than one project-local skills directory:
     - shared / generic layer and workflow distributed-skill target: `.agents/skills/`
     - Codex-local / project-custom layer and duplicate shared-skill drift cleanup surface: `.codex/skills/`
   - Contract:
     - workflow distributed skills (`feasibility`, `brainstorm`, `design`, `plan`, `project-audit`, `check`, `review-gate`, `delivery`) must be deployed to `.agents/skills/` only
     - `.codex/skills/` must not be treated as a required shared workflow skill deployment target; duplicate shared workflow skills found there are drift and should be detected / cleaned up
     - patch-based baseline skills for Codex (`trellis-continue`, `trellis-finish-work`) must be enhanced **only in the active skills directory** resolved by `resolve_codex_skills_dir`
     - legacy `start` / `finish-work` skill names are old-target compatibility inputs only, not current fresh-baseline patch targets
     - installer backup scope must match write scope:
       - distributed skills: `.agents/skills/` only
       - optional disabled skills such as `parallel`: each skills directory where the disabled entry exists
       - patched baseline skills: active skills directory only
       - duplicate shared workflow skill cleanup: `.codex/skills/` only when duplicate shared-skill files exist there
     - uninstall / `--force` restore scope must match the same boundary:
       - shared workflow distributed skills are restored / removed only in `.agents/skills/`
       - optional disabled entries are restored only in directories where they were backed up
       - active baseline patches are restored / reapplied only in the active skills directory
       - duplicate shared workflow skill copies in `.codex/skills/` are cleanup targets, not required restore targets
     - `upgrade-compat.py --check` must:
       - verify distributed skills in `.agents/skills/`
       - detect duplicate shared workflow skills under `.codex/skills/` as drift
       - verify optional disabled skills such as `parallel` in every directory where they exist
       - verify `trellis-continue` / `trellis-finish-work` patch health only in the active skills directory
     - docs must state that `.codex/skills/` is Codex-local / project-custom plus duplicate shared-skill drift cleanup scope, and that non-active directory copies of `trellis-continue` / `trellis-finish-work` are outside the workflow-managed patch drift surface unless a future installer explicitly starts writing there
     - docs must not describe `.codex/skills/parallel` as the current fresh-baseline default outcome of `trellis init`; if mentioned, it must be framed as a conditional / historical / sample-only secondary-carrier case rather than a required or expected default

4.2 **Codex install summary accounting**
   - installer summary fields for Codex must distinguish:
     - `patches`: workflow actually injected or removed assets within the workflow-managed write scope
     - `manual_checks`: baseline/manual-maintained prerequisite surfaces that were only checked for presence or readiness
   - Contract:
     - `patches` may include:
       - `trellis-continue` patch injection in the active skills directory
       - `trellis-finish-work` patch injection in the active skills directory
       - optional disabled entry removal such as `parallel`, but only when such an entry actually exists in one of the skills directories
     - `patches` must not include:
       - `.codex/hooks.json` presence checks
       - `.codex/hooks/inject-workflow-state.py` presence checks
       - other Trellis-baseline or project-manual assets that the workflow does not write, patch, or remove
     - presence checks for `.codex/hooks.json` / `.codex/hooks/inject-workflow-state.py` must be reported separately as `manual_checks` or an equivalent non-patch summary dimension
     - dry-run and formal-install summary output must not overstate workflow write scope by counting manual/baseline readiness checks as workflow patches
   - Tests Required:
     - Codex dry-run summary must show workflow patch count independently from manual baseline checks
     - a fixture that contains `.agents/skills/parallel` must still increment `patches` for the `parallel` removal path
     - the same fixture must not gain an extra patch count merely because `.codex/hooks.json` and `.codex/hooks/inject-workflow-state.py` exist

5. **Phase-gate helper scripts**
   - helper scripts referenced as mandatory validation gates inside workflow source commands
   - current examples may include:
     - `delivery-control-validate.py`
     - `ownership-proof-validate.py`
     - `source-watermark-guard.py`
     - `workflow-state.py`
   - Contract:
     - source command docs may reference `<WORKFLOW_DIR>/commands/shell/...` in source form
     - deployment must rewrite those references to `.trellis/scripts/workflow/...`
     - any newly added mandatory helper must be registered in `HELPER_SCRIPTS`
     - installer must copy it into the target project
     - install record `scripts` must include it
     - installer regression tests must assert both deployment presence and install-record inclusion
     - helper / patch scripts invoked directly by operators must expose standard `-h` / `--help` behavior instead of treating help flags as positional file paths
     - patch helpers that modify target-project Python function bodies must preserve the target function's leading docstring and baseline-compatible introspection/read surface unless the workflow contract explicitly retires that surface
     - retired helper names that are no longer workflow-managed must be tracked in shared asset definitions so `upgrade-compat.py --check` can flag stale deployed residue and `--merge` can remove it
     - if a helper becomes a required phase gate, the relevant walkthrough / mapping docs must mention the validation command

6. **Patch-based shared workflow document**
   - current known set:
     - `.trellis/workflow.md`
   - Contract:
     - keep the Trellis baseline workflow guide, then inject workflow projectization content into the documented section boundaries
     - if the projectized workflow removes the old Phase 1/2/3 narrative, it must still preserve a compatibility read surface for baseline step readers that call `get_context.py --mode phase --step <X.Y>`; strong-gate routing and baseline step lookup may coexist, but step lookup must not silently degrade to `Step not found`
     - when the strong-gate breadcrumb patch changes stage-entry or stage-exit requirements, the same change must propagate every still-applicable execution-card obligation and no-task bootstrap requirement into the matching stage blocks in the workflow patch source; do not leave requirement-change routing, `source_watermark_*`, `ownership_proof_required`, or delivery-time ownership-proof checks visible only in one entry surface
     - installer must back up the original baseline copy before first patching
     - uninstall / force-restore paths must restore the original baseline copy when a backup exists
     - drift detection must at minimum verify the workflow patch marker is still present
     - if the source patch changes, the workflow author must propagate the resulting rule changes to walkthrough / mapping docs that summarize the same behavior

7. **Trellis-native implementation agents**
   - Trellis 0.5+ native implementation-internal role assets
   - current Trellis-native target filenames:
     - Claude:
       - current: `.claude/agents/trellis-research.md`
       - current: `.claude/agents/trellis-implement.md`
       - current: `.claude/agents/trellis-check.md`
     - OpenCode:
       - current: `.opencode/agents/trellis-research.md`
       - current: `.opencode/agents/trellis-implement.md`
       - current: `.opencode/agents/trellis-check.md`
     - Codex:
       - current: `.codex/agents/trellis-research.toml`
       - current: `.codex/agents/trellis-implement.toml`
       - current: `.codex/agents/trellis-check.toml`
    - legacy compatibility inputs may still appear as unprefixed `research / implement / check` files on older installed target projects and must be handled during upgrade / uninstall flows
   - Contract:
     - workflow install / upgrade / uninstall scripts must not write, patch, or delete the Trellis-native `trellis-research` / `trellis-implement` / `trellis-check` content
     - installer dry-runs should report `Agents: 0` for the workflow-managed write set when only Trellis-native implementation agents are present
     - upgrade / uninstall paths may rename legacy bare-name files (`research`, `implement`, `check`) to the Trellis-native `trellis-*` naming convention when an older target project still has those files
     - `upgrade-compat.py --check` must not report native `trellis-*` agent content drift as workflow-managed drift
     - uninstall must not delete Trellis-native `trellis-*` agents created by `trellis init`
     - the formal workflow stage `/trellis:check` is distinct from the Trellis-native `trellis-check` agent role and docs must keep that boundary explicit

#### 3.2.1 Initial Branch Gate

For this workflow variant, installer-time repository gating must distinguish two target-project states:

1. **New repository / no local commit history**
   - the local primary branch and initial branch must be `main`
   - if the current branch is not `main`, installer must fail fast with a concrete remediation command

2. **Existing repository / has local commit history**
   - installer must not force-rename the current branch to `main`
   - installer may warn and record the boundary in docs, but must allow the install path to continue

This branch gate is a workflow-entry contract, not a generic Git rule:

- the effective first workflow entry may be `feasibility` or `brainstorm`
- target-project docs may describe the gate at the workflow-entry layer
- installer enforcement must still follow the same underlying rule when install is attempted

#### 3.2.2 Initial Embed State Gate

This workflow variant allows embed only from a clean initial baseline.

Required behavior:

- installer must detect whether the target project is still in the initial baseline state before any workflow-managed write
- if any workflow-managed trace already exists, installer must fail fast instead of trying to continue or overlay the previous state
- workflow-managed traces include at minimum:
  - `workflow-installed.json`
  - `workflow-embed-attempt.json`
  - installer-managed `AGENTS.md` routing block
  - installer-managed `.trellis/workflow.md` patch
  - distributed added commands / skills
  - workflow patch markers in baseline commands / skills
  - workflow-managed helper scripts
  - legacy bare-name implementation agents that require migration
- read-only detection may classify:
  - `INITIAL_BASELINE_READY`
  - `ALREADY_VALID_EMBEDDED`
  - `BLOCKED_NON_INITIAL_STATE`
- formal install path may proceed only from `INITIAL_BASELINE_READY`
- if install fails at any later step, target project becomes `BLOCKED_NON_INITIAL_STATE` until a human manually resets it

#### 3.3 Analysis-First Upgrade Contract

Target-project workflow upgrade must use an analysis-first sequence:

1. current repository finishes workflow source-asset compatibility maintenance
2. target project completes the Trellis official upgrade and resolves only official baseline conflicts
3. target project `.trellis/.version` must match the current latest Trellis version
4. `analyze-upgrade.py` compares:
   - `A`: clean Trellis baseline
   - `B`: expected state after installing the current workflow onto `A`
   - `C`: target-project live state after official Trellis upgrade
5. analysis classifies each managed asset into:
   - `keep`
   - `add`
   - `replace`
   - `merge`
   - `delete`
6. only low-risk drift may continue into `upgrade-compat.py`

This means:

- `upgrade-compat.py` is not the default upgrade strategy by itself
- neither read-only `A/B/C` analysis nor `upgrade-compat.py` may run before the target project is on the latest Trellis version
- a target project may still be upgraded without `workflow_version` / `workflow_schema_version` once it is already on the latest Trellis version
- structural migration is a branch conclusion from the analysis result, not the default entry point

#### 3.4 Drift Detection and Repair Contract

`upgrade-compat.py --check` must not treat distributed workflow commands as “present = healthy”.

Required behavior:

- patch-based baseline commands:
  - verify patch markers / injection anchors
- overlay baseline commands:
  - verify deployed content matches current workflow source content after preprocessing
- added commands:
  - verify deployed content matches current workflow source content after preprocessing
- shared helper scripts:
  - verify deployed content matches current workflow source content
- installer-managed `AGENTS.md` routing block:
  - verify the routing block markers still exist when `AGENTS.md` exists
  - verify the routing block content still matches the installer source of truth
- install-record state warnings:
  - do not fail only because lifecycle state and filesystem state disagree
  - but emit a human-readable warning when `bootstrap_task_removed` / `bootstrap_cleanup_status` disagree with the actual presence of `.trellis/tasks/00-bootstrap-guidelines`

For current workflow scripts, “after preprocessing” means at least applying the same path rewrite logic as deployment, such as:

```text
<WORKFLOW_DIR>/commands/shell/ -> .trellis/scripts/workflow/
```

Repair-path boundary:

- `--merge` may redeploy low-risk drifted assets and reapply patch injections
- `--force` may restore from stored baseline backup only when the target project is still within the same structural model
- neither `--merge` nor `--force` should be documented as the main path for structural breaks

#### 3.4.1 Critical Runtime Patch Capability Contract

The install-record field `workflow-installed.json["critical_runtime_patches"]`
tracks **runtime patch capabilities**, not a one-to-one list of helper-script
filenames that must appear on disk unchanged.

Contract:

- each capability name must map to at least one workflow-managed repair surface:
  - a distributed helper script under `docs/workflows/<name>/commands/shell/*.py`, or
  - an installer / upgrade patch entrypoint that is intentionally sourced from
    such a helper script, or
  - a validator-side marker check whose target-project patch carrier is already
    defined elsewhere in the same source contract
- when a capability is implemented via helper script distribution, the helper
  must also appear in:
  - `workflow_assets.py` helper enumeration
  - install-record `scripts`
  - installer deployment behavior
  - upgrade repair behavior
  - regression tests
- do not leave a capability name in `critical_runtime_patches` after renaming,
  merging, or splitting its helper-script carrier unless the new carrier mapping
  is updated in the same change
- scan / audit / repair flows must judge missing-patch defects from the
  **capability-to-carrier mapping**, not from a naive "capability name must
  equal helper filename stem" assumption

Validation & error behavior:

- if a capability's mapped helper / carrier is absent from source enumeration or
  deployment logic, treat that as contract drift
- if the target-project patched runtime carrier lacks the required patch marker,
  treat that as a real missing critical runtime patch
- if a JS hook carrier depends on Python helper execution, its runtime contract
  must accept a resolved interpreter override before falling back to the bare
  platform default; for the current workflow this means
  `process.env.TRELLIS_PYTHON || "python3"` rather than a hardcoded
  `"python3"`-only contract
- if runtime behavior is patched correctly but source helper enumeration no
  longer explains how the capability lands on disk, treat that as a source-side
  contract defect to fix before the next workflow release

Good / Base / Bad:

- Good: capability names, helper enumeration, deployment logic, and validator
  checks all describe the same patch surface
- Base: one capability maps to a wrapper helper that delegates to a legacy
  implementation helper, but both source/deploy/test surfaces stay aligned
- Bad: install record advertises a critical capability while no source helper or
  repair entrypoint explains how that capability is deployed or repaired

Tests Required:

- install regression asserts that every distributed helper required by the
  current `critical_runtime_patches` contract is deployed
- runtime validation regression fails when a capability's patched target carrier
  is missing its marker
- source-side regression covers renamed / wrapper helper carriers so capability
  names and helper filenames cannot silently drift apart

Wrong vs Correct:

#### Wrong

- assume every `critical_runtime_patches` item must have an identical helper
  filename stem on disk
- rename or wrap a patch helper without updating helper enumeration, installer,
  upgrade repair, and tests together

#### Correct

- treat `critical_runtime_patches` as runtime patch capability names with an
  explicit source-to-carrier mapping
- update helper enumeration, deployment, upgrade repair, validation, and tests
  in the same change whenever a capability's carrier changes

#### 3.4.2 Phase-Gate Helper Distribution Contract

When a workflow introduces or changes a helper script that is invoked as a mandatory phase gate:

- update `workflow_assets.py` first
- keep install / uninstall / upgrade detection behavior aligned through the shared helper list
- update source command docs and target-project path rewrite assumptions together
- update tests that prove:
  - the helper is deployed into `.trellis/scripts/workflow/`
  - `workflow-installed.json["scripts"]` contains the helper
  - target-project-facing guidance mentions the helper when the gate is user-visible

Examples of user-visible gate contracts:

- a delivery-phase command that blocks formal delivery until a helper returns success
- a close-out flow whose final session record behavior must stay aligned with the workflow terminal chain `finish-work -> delivery -> record-session`, with `task.py archive` followed by `add_session.py` inside `record-session`

Do not treat phase-gate helpers as "nice to have" copied scripts once their command docs make them required.

#### 3.4.1 Install Failure Boundary

Installer success-only side effects must be gated behind a clean deployment result:

- write `workflow-embed-attempt.json` before the first target-project write in a formal install
- deploy per-CLI assets first and collect deployment errors
- if any CLI deployment fails:
  - return a non-zero exit code
  - keep the failure visible in stdout/stderr
  - keep `workflow-embed-attempt.json`
  - do not write `workflow-installed.json`
  - do not continue into other success-only side effects such as post-install guidance that assumes successful embed
- only when all requested CLI deployments succeed may the installer continue to:
  - copy shared helper scripts
  - import the initial requirements foundation pack
  - remove the bootstrap task if it exists, otherwise skip cleanup
  - write `workflow-installed.json`
  - apply post-install routing / reminders
  - run a final read-only post-install validation
  - clear `workflow-embed-attempt.json` only after that validation passes

#### 3.4.1.1 Post-Install Self-Check Environment Gate

The installer may need to suppress attempt-record conflict detection only for its own in-flight post-install self-check.

Contract:

- `WORKFLOW_IGNORE_EMBED_ATTEMPT=1` is an internal environment contract between `install-workflow.py` and `upgrade-compat.py --check`
- it must be used only by the installer's immediate post-install self-check while `workflow-embed-attempt.json` is still expected to exist
- normal user-invoked `upgrade-compat.py --check` and `detect-embed-state.py` must not set this flag implicitly
- the flag must not weaken any other drift checks beyond suppressing the attempt-record conflict during the installer's own success-path validation

#### 3.5 Source-Maintenance vs Target-Project Boundary

When maintaining workflow source content in this repository after a Trellis upgrade:

- obtain the clean Trellis baseline from `/tmp` + `trellis init`
- do not use this repository's already customized `.trellis/`, `.claude/`, `.opencode/`, or `.codex/` directories as the initial baseline

When upgrading an already-installed target project:

- first resolve the Trellis official baseline upgrade
- confirm the target-project `.trellis/.version` already equals the current latest Trellis version
- then generate `A/B/C` and run `analyze-upgrade.py`
- then choose file-level actions
- then optionally use `upgrade-compat.py` for low-risk repair

If that latest-version prerequisite cannot be proven:

- `analyze-upgrade.py` must fail fast
- `upgrade-compat.py --check/--merge/--force` must fail fast
- failure messages must explicitly say that read-only analysis is also blocked

When analysis shows any of the following, stop treating the case as ordinary compatibility upgrade:

- patch anchors / headings no longer support the old injection model
- command naming, staging, or file layout changed
- managed assets are dominated by `merge`
- `.backup-original` is not a reliable restore base

That branch becomes structural migration and must not be collapsed into `upgrade-compat.py --force`.

---

### 4. Validation & Error Matrix

| Condition | `analyze-upgrade.py` | `--check` | `--merge` | `--force` |
|-----------|----------------------|-----------|-----------|-----------|
| `C == B` for a managed asset | classify `keep` | return `0` if all managed assets are healthy | no-op or return success | no-op or return success |
| target project is not on latest Trellis | fail fast before classification | fail fast | fail fast | fail fast |
| `A != B` and `C == A` for an existing managed asset | classify `replace` | return non-zero if deployed state is stale | redeploy current workflow copy | restore baseline backup, then reapply patch only if same structural model still holds |
| asset exists only in `B` | classify `add` | return non-zero if missing in `C` | deploy asset | deploy asset |
| `C != A` and `C != B` | classify `merge` and keep it visible | may return non-zero if drift is detected | do not claim semantic merge; only safe redeploy when drift is low-risk | not a structural-migration substitute |
| asset removed from latest workflow but still exists in `C` | classify `delete` | may stay non-zero or advisory depending on script scope | optional manual cleanup only | optional manual cleanup only |
| patch marker missing in Claude / OpenCode `continue` / `finish-work` or Codex active-skill `trellis-continue` / `trellis-finish-work`（legacy `start` / `record-session` 仅作为旧目标项目兼容残留处理） | may present as `replace` or `merge` depending on `A/B/C` | return non-zero | redeploy and reinject patch when injection model still holds | restore baseline backup, then reinject patch when backup is valid |
| helper script missing or drifted | classify `add` / `replace` / `merge` based on `A/B/C` | return non-zero | recopy helper script | recopy helper script |
| missing `workflow_version` / `workflow_schema_version` while target project is already on latest Trellis | annotate as `legacy/unknown` context only | do not fail on absence alone | do not synthesize historical version | do not synthesize historical version |
| missing baseline backup during force path | analysis may still proceed | n/a | n/a | fail clearly and keep error visible |
| structural break detected | flag structural migration recommendation | may still show drift, but is not sufficient by itself | do not treat as primary resolution | do not treat as primary resolution |

Failure messages must stay human-readable and identify the affected asset by file / command / skill name.

---

### 5. Good / Base / Bad Cases

#### Good

- target project completes Trellis official upgrade first
- `analyze-upgrade.py` reports most assets as `keep` / `replace`, with a small number of `merge`
- low-risk drift is repaired by `upgrade-compat.py --merge`
- follow-up `--check` passes

#### Base

- `A/B/C` are prepared correctly
- version fields may be absent, but the project is explicitly treated as `legacy/unknown`
- patch markers present where expected
- distributed command contents match source
- helper scripts match source
- `analyze-upgrade.py` produces a readable report
- `--check` returns success after low-risk repair

#### Bad

- skip `A/B/C` analysis and jump directly to `--force`
- treat distributed workflow files as healthy just because they exist
- let `--merge` stand in for a real semantic merge of target-project private edits
- treat missing `workflow_version` fields as proof of a specific old structure
- use the current repository's customized Trellis directories as the clean baseline for source-maintenance upgrade analysis

---

### 6. Tests Required

When modifying these contracts, update or add tests that prove:

1. install writes `overlay_commands` and `added_commands` into `workflow-installed.json`
2. installer enforces `main` branch for new repositories but allows existing-history repositories to keep a non-`main` branch
3. installer does not write `workflow-installed.json` when any CLI deployment fails
4. installer writes `workflow-embed-attempt.json` before formal install writes and clears it only after post-install validation passes
5. a failed install leaves `workflow-embed-attempt.json` behind with a failed lifecycle state
6. initial-state detection distinguishes:
   - `INITIAL_BASELINE_READY`
   - `ALREADY_VALID_EMBEDDED`
   - `BLOCKED_NON_INITIAL_STATE`
7. reinstall is blocked when the target project is no longer in the initial baseline state
8. uninstall restores overlay baseline commands from backup
9. `analyze-upgrade.py` classifies at least:
   - `keep`
   - `add`
   - `replace`
   - `merge`
   - `delete`
10. `--check` fails when:
   - patch markers drift
   - runtime patch markers still exist but startup guidance / session-context text still contains legacy READY auto-continue instructions
   - `.trellis/workflow.md` patch content drifts while the marker still exists
   - installer-managed `AGENTS.md` routing block is missing or drifts when `AGENTS.md` exists
   - `workflow-embed-attempt.json` exists
   - overlay command content drifts
   - added command content drifts
   - helper script content drifts
   - a required phase-gate helper is missing from deployed target scripts or missing from install-record `scripts`
11. `--check` emits a warning when install-record lifecycle state (`bootstrap_task_removed` / `bootstrap_cleanup_status`) conflicts with the actual presence of `.trellis/tasks/00-bootstrap-guidelines`
12. `--merge` restores drifted command and helper-script content for low-risk cases
13. `--force` can restore baseline-backed patch commands and reapply patches inside the same structural model
14. newly added required helper scripts are reflected in user-visible install guidance when the workflow gate is exposed to target-project users
15. Codex multi-directory behavior is covered by regression tests:
   - distributed shared workflow skills sync to `.agents/skills/` only
   - duplicate shared workflow skills under `.codex/skills/` are detected / cleaned as drift instead of required
   - `trellis-continue` / `trellis-finish-work` patch health is checked and repaired only in the active skills directory
   - legacy `start` / `finish-work` names are covered only as old-target compatibility inputs
   - uninstall / `--force` restore follow the same write-scope boundary for `.agents/skills/`, optional disabled entries, active baseline patches, and `.codex/skills/` duplicate cleanup
16. requirements-foundation import coverage is covered by regression tests:
   - installer must not leave `.trellis/library-lock.yaml` referencing example assets under `.trellis/library-assets/**` unless those example assets were actually copied into the target project
   - managed audit extra specs for `shared-pack:requirements-discovery-foundation-import` must stay aligned with the real imported output set
17. patched workflow guide compatibility is covered by regression tests:
   - the installed `.trellis/workflow.md` keeps the strong-gate stage contract
   - the same installed file still contains a baseline-compatible `#### X.Y` step-read surface for `get_context.py --mode phase --step`
18. patch helper CLI + introspection compatibility is covered by regression tests:
   - patch helpers expose standard `--help`
   - Python-target patch helpers do not destroy preserved function docstrings when they inject strong-gate logic
19. strong-gate workflow/doc runtime contracts are covered by regression tests:
   - the installed `.trellis/workflow.md` stage breadcrumbs surface the execution-card and watermark/ownership obligations required by the current workflow contract
   - injected JS workflow-state carriers require `process.env.TRELLIS_PYTHON || "python3"` instead of a hardcoded `python3` string
   - deployed execution cards that reference target-project formal docs do not imply those docs must preexist when the workflow is responsible for creating or backfilling them at runtime

Current regression anchors:

```text
docs/workflows/新项目开发工作流/commands/test_workflow_installers.py
docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py
```

Recommended assertion points:

- command-specific drift message is emitted
- helper-script drift message is emitted
- runtime patch health checks fail when marker-presence coexists with legacy READY auto-continue prompt residue
- analysis report includes action classification for each managed asset
- follow-up `--check` returns success after `--merge` / `--force` in supported scenarios

---

### 7. Wrong vs Correct

#### Wrong

- treat all workflow-distributed commands as “new commands”
- let `--check` validate only file existence
- skip helper-script content drift checks because the file is present
- skip `A/B/C` analysis and use `upgrade-compat.py` as the only upgrade decision layer
- document `--force` as the solution for structural breaks
- assume missing workflow version fields prove a specific migration path

#### Correct

- classify workflow assets as patch-based baseline, overlay baseline, and added commands
- keep workflow-facing docs and matrices aligned with `workflow_assets.py` when classifying assets such as `record-session`
- keep `workflow_assets.py` as the shared source for asset enumeration and deployment layout
- use `A/B/C` analysis to decide `keep / add / replace / merge / delete`
- use source-vs-deployed content checks for distributed commands and helper scripts
- keep backup / restore semantics explicit for overlay baseline commands
- use `/tmp` + `trellis init` as the clean baseline when maintaining workflow source compatibility after Trellis upgrades
- treat structural migration as a separate branch conclusion when ordinary compatibility upgrade no longer explains the target-project state

---

## Scenario: Profile-Based Conditional Content

### 1. Scope / Trigger

- Trigger: modifying `prepare_command_content()` in `workflow_assets.py`
- Trigger: adding/removing `<!-- if:outsourcing -->` markers in command source docs
- Trigger: changing which scripts or execution cards are included per profile
- Trigger: install-record `profile` field semantics change

### 2. Signatures

```python
def prepare_command_content(source_path: Path, *, profile: str = DEFAULT_PROFILE) -> str
```

Profile values: `"personal"` | `"outsourcing"` (default: `"outsourcing"`)

### 3. Contracts

#### 3.1 Conditional Marker Format

Source command files use HTML comments as conditional markers:

```markdown
<!-- if:outsourcing -->
(outsourcing-specific content)
<!-- endif:outsourcing -->
```

- Markers must be on their own line with no other content
- Markers must always appear in matched pairs
- Nesting is not supported

#### 3.2 Stripping Behavior

| Profile | Marker behavior |
|---------|----------------|
| `personal` | Remove markers AND wrapped content |
| `outsourcing` | Remove markers only, keep wrapped content |

#### 3.3 Script Filtering

| Constant | Contents |
|----------|---------|
| `HELPER_SCRIPTS` | All 8 helper scripts (full set) |
| `CORE_HELPER_SCRIPTS` | 7 scripts excluding outsourcing-only |
| `OUTSOURCING_ONLY_SCRIPTS` | `delivery-control-validate.py` |

Install deploys `HELPER_SCRIPTS` for outsourcing, `CORE_HELPER_SCRIPTS` for personal.

#### 3.4 Profile in Install Record

`workflow-installed.json` must include `"profile"` field. Missing profile defaults to `"outsourcing"` for backward compatibility.

### 4. Validation & Error Matrix

| Condition | Error |
|-----------|-------|
| Unmatched `<!-- if:outsourcing -->` without `<!-- endif:outsourcing -->` | Regex silently skips (no error); content leaks into personal build |
| Profile not in `VALID_PROFILES` | argparse rejects at CLI level |
| Missing `profile` in install record during `--check` | Default to `"outsourcing"` |

### 5. Good / Base / Bad Cases

- **Good**: personal profile trims outsourcing sections; `--check` uses same profile to verify
- **Base**: outsourcing profile keeps all content, markers stripped
- **Bad**: install with personal, check with outsourcing default → false drift on every outsourcing-marked command

### 6. Tests Required

- Profile stripping produces different output for marked files
- `--check` reads profile from install record and matches deployed content
- personal profile excludes `OUTSOURCING_ONLY_SCRIPTS`
- install record contains `profile` field

### 7. Wrong vs Correct

#### Wrong
- Check deployed content with default profile when install used `personal`
- Add outsourcing markers with content on the same line as the marker

#### Correct
- Always read `profile` from install record before content comparison
- Markers on their own lines, content between them on separate lines

---

## Scenario: Execution Card Distribution

### 1. Scope / Trigger

- Trigger: adding/removing execution cards
- Trigger: changing execution card link rewrite rules in `prepare_command_content`
- Trigger: changing `.trellis/workflow-docs/` deployment target

### 2. Signatures

```python
EXECUTION_CARDS = ["需求变更管理执行卡.md"]
OUTSOURCING_EXECUTION_CARDS = ["源码水印与归属证据链执行卡.md"]
WORKFLOW_DOCS_DIR = ".trellis/workflow-docs"
```

```python
def deploy_execution_cards(src: Path, root: Path, dry_run: bool, *, profile: str) -> int
```

### 3. Contracts

#### 3.1 Source Location

Execution cards live at the workflow root directory (parent of `commands/`):
```text
docs/workflows/<name>/需求变更管理执行卡.md
docs/workflows/<name>/源码水印与归属证据链执行卡.md
```

#### 3.2 Target Location

```text
.trellis/workflow-docs/需求变更管理执行卡.md
.trellis/workflow-docs/源码水印与归属证据链执行卡.md  (outsourcing only)
```

#### 3.3 Link Rewrite Contract

`prepare_command_content` rewrites execution card links to point to the target-project path:

| Source form | Deployed form |
|-------------|--------------|
| `[需求变更管理执行卡](../需求变更管理执行卡.md)` | `[需求变更管理执行卡](.trellis/workflow-docs/需求变更管理执行卡.md)` |
| `[需求变更管理执行卡](../../需求变更管理执行卡.md)` | Same as above |

Previous behavior stripped these to plain text. New behavior keeps them as working links.

#### 3.4 Drift Detection

`upgrade-compat.py --check` must verify:
- Execution card files exist in `.trellis/workflow-docs/`
- Content matches workflow source
- Profile determines which cards are expected

#### 3.5 Runtime-Created Target-Doc References

When an execution card or workflow-managed document references target-project
artifacts under paths such as `docs/requirements/**`, the source wording must
distinguish between:

- a path that must already exist before the workflow starts, and
- a formal target-project document path that the workflow may create or
  backfill during runtime

Do not describe a runtime-created formal-doc path as if its absence at project
start were itself a workflow defect.

### 4. Validation & Error Matrix

| Condition | Error |
|-----------|-------|
| Source card missing | `warn` during install, card not deployed |
| Deployed card content differs from source | `err` during `--check` |
| Card missing in target when expected by profile | `warn` during `--check` |

---

## Scenario: workflow-state.py route Subcommand

### 1. Scope / Trigger

- Trigger: modifying `cmd_route` in `workflow-state.py`
- Trigger: changing Phase Router decision tree in `start-patch-phase-router.md`
- Trigger: changing stage routing logic

### 2. Signatures

```bash
python3 .trellis/scripts/workflow/workflow-state.py route [task-dir] \
  [--project-root /path]
```

`task-dir` is optional. When absent, route resolves the active task from Trellis' session-scoped runtime and otherwise falls into `first_entry` / `recovery_needed`.

### 3. Contracts

#### Output Format (JSON to stdout)

```json
{
  "target": "design" | null,
  "action": "reenter" | "first_entry" | "awaiting_confirmation" | "blocked" | "recovery_needed" | "repair_needed" | "embed_invalid",
  "stage": "design",
  "stage_status": "in_progress",
  "reason": "...",
  "blockers": []
}
```

#### Action Semantics

| Action | Meaning | Phase Router behavior |
|--------|---------|----------------------|
| `first_entry` | No active task and no resumable task exists in the target project | Route to `/trellis:feasibility` |
| `reenter` | Normal re-entry to current stage | Route to `/trellis:<target>` |
| `awaiting_confirmation` | Stage done, pending user confirm | Show status, wait for user |
| `blocked` | Execution gate not met | Show blockers, do not proceed |
| `recovery_needed` | Cannot determine the current active task | Ask user to clarify |
| `repair_needed` | State file missing/broken | Run `repair` subcommand |
| `embed_invalid` | Workflow install incomplete | Stop, report install issue |

#### Exit Codes

- `0`: Routing computed successfully (even when target is null)
- `1`: Cannot compute route (path resolution error, etc.)

### 4. Validation & Error Matrix

| Condition | Output |
|-----------|--------|
| No active task and no task directories | `first_entry` → feasibility |
| No active task but task directories exist | `recovery_needed` |
| Active task → non-leaf task | `repair_needed` |
| Active task → missing workflow-state.json | `repair_needed` |
| Execution stage without `execution_authorized` | `blocked` |
| External outsourcing without `kickoff_payment_received=yes` | `blocked` |

---

## Scenario: workflow-state.py repair Subcommand

### 1. Scope / Trigger

- Trigger: modifying `cmd_repair` in `workflow-state.py`
- Trigger: changing state recovery logic in Phase Router

### 2. Signatures

```bash
python3 .trellis/scripts/workflow/workflow-state.py repair <task-dir> \
  [--project-root /path] [--apply]
```

### 3. Contracts

#### Inference Rules

| Artifact present | Inferred stage |
|-----------------|----------------|
| No assessment.md in task lineage | `feasibility` |
| assessment.md exists, no customer-facing-prd.md | `brainstorm` |
| customer-facing-prd.md exists, no design/ dir | `design` |
| design/ exists, no task_plan.md | `design` |
| task_plan.md exists | `plan` |

#### Output Format

```json
{
  "status": "ok" | "repair_needed",
  "inferred_stage": "design",
  "confidence": "high" | "medium" | "low",
  "evidence": ["..."],
  "message": "..."
}
```

#### Write Gate

- Without `--apply`: read-only, outputs inference
- With `--apply`: creates `workflow-state.json` using `build_default_state(inferred_stage)`

### 4. Wrong vs Correct

#### Wrong
- Auto-apply without user confirmation in AI layer
- Infer execution stages (implementation, test-first) — these require explicit user confirmation

#### Correct
- Output inference, let Phase Router prompt user to confirm
- Only infer pre-execution stages (feasibility through plan)

---

## Scenario: Tolerant Version Handling in validate_state_shape

### 1. Scope / Trigger

- Trigger: modifying version validation in `workflow-state.py`

### 3. Contracts

When `workflow-state.json` lacks the `"version"` field:
- Default to `SUPPORTED_STATE_VERSION` (currently `1`)
- Mutate the in-memory state dict to include the default
- Continue validation normally

Unknown fields in `workflow-state.json` are silently ignored; only required keys are validated.

### 7. Wrong vs Correct

#### Wrong
- Reject workflow-state.json outright when version is missing
- Error on unknown fields added by future versions

#### Correct
- Tolerate missing version, default to current supported version
- Validate only the required key set; ignore unknown keys

---

## Related Files

- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `docs/workflows/新项目开发工作流/需求变更管理执行卡.md`
- `docs/workflows/新项目开发工作流/源码水印与归属证据链执行卡.md`
- `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
- `docs/workflows/新项目开发工作流/结构性迁移设计.md`
- `docs/workflows/新项目开发工作流/命令映射.md`

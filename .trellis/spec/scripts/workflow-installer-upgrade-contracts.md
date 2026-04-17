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
- Trigger: changing the distributed workflow command set, helper script set, install record schema, or target deployment layout
- Trigger: changing how workflow source assets are compared with deployed target-project copies
- Trigger: changing the target-project upgrade flow from analysis-first to another sequence

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

Current required keys:

- `trellis_version`
- `cli_types`
- `commands`
- `overlay_commands`
- `added_commands`
- `disabled_commands`
- `patched_baseline_commands`
- `initial_pack`
- `bootstrap_task_removed`
- `scripts`

Optional lifecycle keys may differ between install and upgrade paths, such as:

- `installed`
- `updated`
- `previous_version`
- `initial_pack`
- `bootstrap_task_removed`

Optional versioning keys for future upgrade routing:

- `workflow_version`
- `workflow_schema_version`

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
- Codex: `.agents/skills/*/SKILL.md` or `.codex/skills/*/SKILL.md`
- shared helper scripts: `.trellis/scripts/workflow/*.py`

`workflow_assets.py` must remain the single shared definition of:

- supported CLI layouts
- patch-based baseline commands
- overlay baseline commands
- added commands
- optional disabled baseline commands
- helper scripts
- managed asset enumeration / detection helpers

#### 3.2 Asset Classes

Workflow embed / analysis / repair scripts must distinguish three asset classes:

1. **Patch-based baseline commands**
   - `start`
   - `finish-work`
   - `record-session`
   - Contract: keep Trellis baseline content, then inject workflow patch content

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
     - `test-first`
     - `project-audit`
     - `review-gate`
     - `delivery`

4. **Optional disabled baseline commands**
   - baseline commands or skills that may exist in target projects, but are intentionally overridden by this workflow into a disabled state
   - current known set:
     - `parallel`
   - Contract:
     - installer must back up the original baseline copy if present
     - installer may overwrite the target copy with a workflow-managed disabled notice
     - uninstall / force-restore paths must restore the original baseline copy when a backup exists
     - drift detection must compare the deployed disabled copy against the workflow source of truth

5. **Phase-gate helper scripts**
   - helper scripts referenced as mandatory validation gates inside workflow source commands
   - current examples may include:
     - `delivery-control-validate.py`
     - `ownership-proof-validate.py`
     - `record-session-helper.py`
   - Contract:
     - source command docs may reference `<WORKFLOW_DIR>/commands/shell/...` in source form
     - deployment must rewrite those references to `.trellis/scripts/workflow/...`
     - any newly added mandatory helper must be registered in `HELPER_SCRIPTS`
     - installer must copy it into the target project
     - install record `scripts` must include it
     - installer regression tests must assert both deployment presence and install-record inclusion
     - if a helper becomes a required phase gate, the relevant walkthrough / mapping docs must mention the validation command

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

For current workflow scripts, “after preprocessing” means at least applying the same path rewrite logic as deployment, such as:

```text
<WORKFLOW_DIR>/commands/shell/ -> .trellis/scripts/workflow/
```

Repair-path boundary:

- `--merge` may redeploy low-risk drifted assets and reapply patch injections
- `--force` may restore from stored baseline backup only when the target project is still within the same structural model
- neither `--merge` nor `--force` should be documented as the main path for structural breaks

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
- a record-session close-out flow that must run helper pre/post checks before archive

Do not treat phase-gate helpers as "nice to have" copied scripts once their command docs make them required.

#### 3.4.1 Install Failure Boundary

Installer success-only side effects must be gated behind a clean deployment result:

- deploy per-CLI assets first and collect deployment errors
- if any CLI deployment fails:
  - return a non-zero exit code
  - keep the failure visible in stdout/stderr
  - do not write `workflow-installed.json`
  - do not continue into other success-only side effects such as post-install guidance that assumes successful embed
- only when all requested CLI deployments succeed may the installer continue to:
  - copy shared helper scripts
  - import the initial requirements foundation pack
  - remove the bootstrap task
  - write `workflow-installed.json`
  - apply post-install routing / reminders

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
| patch marker missing in `start` / `finish-work` / `record-session` | may present as `replace` or `merge` depending on `A/B/C` | return non-zero | redeploy and reinject patch when injection model still holds | restore baseline backup, then reinject patch when backup is valid |
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
4. uninstall restores overlay baseline commands from backup
5. `analyze-upgrade.py` classifies at least:
   - `keep`
   - `add`
   - `replace`
   - `merge`
   - `delete`
6. `--check` fails when:
   - patch markers drift
   - overlay command content drifts
   - added command content drifts
   - helper script content drifts
   - a required phase-gate helper is missing from deployed target scripts or missing from install-record `scripts`
7. `--merge` restores drifted command and helper-script content for low-risk cases
8. `--force` can restore baseline-backed patch commands and reapply patches inside the same structural model
9. newly added required helper scripts are reflected in user-visible install guidance when the workflow gate is exposed to target-project users

Current regression anchors:

```text
docs/workflows/新项目开发工作流/commands/test_workflow_installers.py
docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py
```

Recommended assertion points:

- command-specific drift message is emitted
- helper-script drift message is emitted
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
- keep `workflow_assets.py` as the shared source for asset enumeration and deployment layout
- use `A/B/C` analysis to decide `keep / add / replace / merge / delete`
- use source-vs-deployed content checks for distributed commands and helper scripts
- keep backup / restore semantics explicit for overlay baseline commands
- use `/tmp` + `trellis init` as the clean baseline when maintaining workflow source compatibility after Trellis upgrades
- treat structural migration as a separate branch conclusion when ordinary compatibility upgrade no longer explains the target-project state

---

## Related Files

- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/analyze-upgrade.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/commands/test_upgrade_analysis.py`
- `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
- `docs/workflows/新项目开发工作流/结构性迁移设计.md`
- `docs/workflows/新项目开发工作流/命令映射.md`

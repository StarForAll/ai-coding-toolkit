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
- Codex: `.agents/skills/*/SKILL.md` or `.codex/skills/*/SKILL.md`
- installer-managed routing block: `AGENTS.md` inside `<!-- workflow-nl-routing-start ... workflow-nl-routing-end -->`
- managed implementation agents:
  - Claude: `.claude/agents/{research,implement,check}.md`
  - OpenCode: `.opencode/agents/{research,implement,check}.md`
  - Codex: `.codex/agents/{research,implement,check}.toml`
- shared helper scripts: `.trellis/scripts/workflow/*.py`
- shared project workflow guide patch: `.trellis/workflow.md`

`workflow_assets.py` must remain the single shared definition of:

- supported CLI layouts
- patch-based baseline commands
- overlay baseline commands
- added commands
- optional disabled baseline commands
- managed implementation agents
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

4.1 **Codex multi-directory skills boundary**
   - Codex may expose more than one project-local skills directory:
     - shared / generic layer: `.agents/skills/`
     - Codex-local layer: `.codex/skills/`
   - Contract:
     - workflow distributed skills (`feasibility`, `brainstorm`, `design`, `plan`, `test-first`, `project-audit`, `check`, `review-gate`, `delivery`) must be deployed to **every existing Codex skills directory**
     - patch-based baseline skills for Codex (`start`, `finish-work`) must be enhanced **only in the active skills directory** resolved by `resolve_codex_skills_dir`
     - installer backup scope must match write scope:
       - distributed skills / optional disabled skills: per existing skills directory
       - patched baseline skills: active skills directory only
     - uninstall / `--force` restore scope must match the same boundary and must not restore untouched baseline skills in non-active directories
     - `upgrade-compat.py --check` must:
       - verify distributed skills in every existing Codex skills directory
       - verify optional disabled skills such as `parallel` in every directory where they exist
       - verify `start` / `finish-work` patch health only in the active skills directory
     - docs must state that non-active directory copies of `start` / `finish-work` are outside the workflow-managed patch drift surface unless a future installer explicitly starts writing there

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

6. **Patch-based shared workflow document**
   - current known set:
     - `.trellis/workflow.md`
   - Contract:
     - keep the Trellis baseline workflow guide, then inject workflow projectization content into the documented section boundaries
     - installer must back up the original baseline copy before first patching
     - uninstall / force-restore paths must restore the original baseline copy when a backup exists
     - drift detection must at minimum verify the workflow patch marker is still present
     - if the source patch changes, the workflow author must propagate the resulting rule changes to walkthrough / mapping docs that summarize the same behavior

7. **Managed implementation agents**
   - workflow-managed implementation-internal role assets
   - current known set:
     - Claude:
       - `.claude/agents/research.md`
       - `.claude/agents/implement.md`
       - `.claude/agents/check.md`
     - OpenCode:
       - `.opencode/agents/research.md`
       - `.opencode/agents/implement.md`
       - `.opencode/agents/check.md`
     - Codex:
       - `.codex/agents/research.toml`
       - `.codex/agents/implement.toml`
       - `.codex/agents/check.toml`
   - Contract:
     - these assets are part of the workflow-managed implementation-stage internal chain
     - installer must back up any pre-existing target copy before first overwrite
     - if a target copy does not exist at install time, installer may create it from the workflow source of truth
     - `upgrade-compat.py --check` must detect drift against the workflow source of truth
     - `--merge` may redeploy the workflow-managed agent content
     - uninstall must restore the backed-up target copy when a backup exists
     - uninstall must delete an install-created managed agent when no baseline backup exists
     - the formal workflow stage `/trellis:check` is distinct from the internal `check-agent` role and docs must keep that boundary explicit
     - research-agent source contracts must keep:
       - `ace.search_context`-first project-internal code localization
       - Context7-first library/framework/SDK documentation lookup
       - `grok-search`-first live/latest fact lookup
       - `deepwiki`-first GitHub repository understanding
       - Exa for deep research, external code context, and fallback web evidence
       - explicit `[Evidence Gap]` fallback wording when Context7 is unavailable

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
  - workflow-managed implementation agents
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
   - distributed skills sync to every existing skills directory
   - `start` / `finish-work` patch only the active skills directory
   - uninstall / `--force` restore follow the same active-directory boundary

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
| `HELPER_SCRIPTS` | All 9 helper scripts (full set) |
| `CORE_HELPER_SCRIPTS` | 7 scripts excluding outsourcing-only |
| `OUTSOURCING_ONLY_SCRIPTS` | `delivery-control-validate.py`, `ownership-proof-validate.py` |

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
  [--project-root /path] [--current-task-file /path]
```

`task-dir` is optional. When absent, route infers from `.current-task` or project-level artifacts.

### 3. Contracts

#### Output Format (JSON to stdout)

```json
{
  "target": "design" | null,
  "action": "reenter" | "first_entry" | "resume_with_assessment" | "awaiting_confirmation" | "blocked" | "recovery_needed" | "repair_needed" | "embed_invalid",
  "stage": "design",
  "stage_status": "in_progress",
  "reason": "...",
  "blockers": []
}
```

#### Action Semantics

| Action | Meaning | Phase Router behavior |
|--------|---------|----------------------|
| `first_entry` | No assessment found | Route to `/trellis:feasibility` |
| `resume_with_assessment` | Valid assessment allows brainstorm | Route to `/trellis:brainstorm` |
| `reenter` | Normal re-entry to current stage | Route to `/trellis:<target>` |
| `awaiting_confirmation` | Stage done, pending user confirm | Show status, wait for user |
| `blocked` | Execution gate not met | Show blockers, do not proceed |
| `recovery_needed` | Cannot determine current task | Ask user to clarify |
| `repair_needed` | State file missing/broken | Run `repair` subcommand |
| `embed_invalid` | Workflow install incomplete | Stop, report install issue |

#### Exit Codes

- `0`: Routing computed successfully (even when target is null)
- `1`: Cannot compute route (path resolution error, etc.)

### 4. Validation & Error Matrix

| Condition | Output |
|-----------|--------|
| No `.current-task`, no assessment | `first_entry` → feasibility |
| No `.current-task`, valid assessment with brainstorm permission | `resume_with_assessment` → brainstorm |
| `.current-task` → non-leaf task | `repair_needed` |
| `.current-task` → missing workflow-state.json | `repair_needed` |
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

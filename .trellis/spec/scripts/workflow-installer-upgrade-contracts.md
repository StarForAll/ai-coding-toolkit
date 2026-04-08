# Workflow Installer / Upgrade Contracts

> Executable contracts for workflow installer and upgrade scripts under `docs/workflows/**/commands/`.

---

## Scenario: Trellis-based Workflow Embed / Upgrade Scripts

### 1. Scope / Trigger

- Trigger: modifying `docs/workflows/**/commands/install-workflow.py`
- Trigger: modifying `docs/workflows/**/commands/uninstall-workflow.py`
- Trigger: modifying `docs/workflows/**/commands/upgrade-compat.py`
- Trigger: changing the distributed workflow command set, helper script set, or target deployment layout
- Trigger: changing how source workflow assets are compared with deployed target-project copies

This concern is required when the change crosses these layers:

```text
workflow source assets -> target project deployed copies -> install record / drift detection -> recovery path
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

Expected keys:

- `trellis_version`
- `cli_types`
- `commands`
- `overlay_commands`
- `added_commands`
- `scripts`

Optional lifecycle keys may differ between install and upgrade paths, such as:

- `installed`
- `updated`
- `previous_version`
- `initial_pack`
- `bootstrap_task_removed`

---

### 3. Contracts

#### 3.1 Source of Truth

Workflow source assets must be treated as the source of truth:

- command source: `docs/workflows/<name>/commands/*.md`
- helper scripts: `docs/workflows/<name>/commands/shell/*.py`

Target-project deployed copies are derived state:

- Claude: `.claude/commands/trellis/*.md`
- OpenCode: `.opencode/commands/trellis/*.md`
- Codex: `.agents/skills/*/SKILL.md` or `.codex/skills/*/SKILL.md`
- shared helper scripts: `.trellis/scripts/workflow/*.py`

#### 3.2 Asset Classes

Workflow embed / upgrade scripts must distinguish three asset classes:

1. **Patch-based baseline commands**
   - `start`
   - `finish-work`
   - `record-session`
   - Contract: keep Trellis baseline content, then inject workflow patch content

2. **Overlay baseline commands**
   - same-name commands whose deployed file is fully distributed by the workflow while semantically merging with Trellis baseline
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
     - `review-gate`
     - `delivery`

#### 3.3 Drift Detection Contract

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

#### 3.4 Source-Maintenance vs Target-Project Boundary

When maintaining workflow source content in this repository after a Trellis upgrade:

- obtain the clean Trellis baseline from `/tmp` + `trellis init`
- do not use this repository's already customized `.trellis/`, `.claude/`, `.opencode/`, or `.codex/` directories as the initial baseline

When upgrading an already-installed target project:

- `upgrade-compat.py` is the local automation layer
- it uses the target project's deployed state and install record
- it is not a substitute for the source-maintenance clean-baseline comparison

---

### 4. Validation & Error Matrix

| Condition | `--check` | `--merge` | `--force` |
|-----------|-----------|-----------|-----------|
| version unchanged + deployed state matches source/patch contract | return `0` | no-op or return success | no-op or return success |
| patch marker missing in `start` / `finish-work` / `record-session` | return non-zero | redeploy and reinject patch | restore baseline backup, then reinject patch |
| overlay/add command file missing | return non-zero | redeploy command | redeploy command |
| overlay/add command content drift | return non-zero | redeploy command from source | redeploy command from source |
| helper script missing | return non-zero | recopy helper script | recopy helper script |
| helper script content drift | return non-zero | recopy helper script | recopy helper script |
| missing baseline backup during force path | return non-zero | n/a | fail clearly and keep error visible |

Failure messages must stay human-readable and identify the affected asset by file / command / skill name.

---

### 5. Good / Base / Bad Cases

#### Good

- `brainstorm` deployed copy was manually edited
- `upgrade-compat.py --check` reports content drift
- `upgrade-compat.py --merge` redeploys the workflow copy
- follow-up `--check` passes

#### Base

- version unchanged
- patch markers present
- distributed command contents match source
- helper scripts match source
- `--check` returns success

#### Bad

- a distributed file still exists, but only existence is checked
- source workflow content has changed while target-project copy is stale
- `--check` reports success even though deployed behavior is outdated

---

### 6. Tests Required

When modifying these contracts, update or add tests that prove:

1. install writes `overlay_commands` and `added_commands` into `workflow-installed.json`
2. uninstall restores overlay baseline commands from backup
3. `--check` fails when:
   - patch markers drift
   - overlay command content drifts
   - added command content drifts
   - helper script content drifts
4. `--merge` restores drifted command and helper-script content
5. `--force` can restore baseline-backed patch commands and reapply patches

Current regression anchor:

```text
docs/workflows/新项目开发工作流/commands/test_workflow_installers.py
```

Recommended assertion points:

- command-specific drift message is emitted
- helper-script drift message is emitted
- follow-up `--check` returns success after `--merge` / `--force`

---

### 7. Wrong vs Correct

#### Wrong

- treat all workflow-distributed commands as “new commands”
- let `--check` validate only file existence
- skip helper-script content drift checks because the file is present
- use the current repository's customized Trellis directories as the clean baseline for source-maintenance upgrade analysis

#### Correct

- classify workflow assets as patch-based baseline, overlay baseline, and added commands
- use source-vs-deployed content checks for distributed commands and helper scripts
- keep backup / restore semantics explicit for overlay baseline commands
- use `/tmp` + `trellis init` as the clean baseline when maintaining workflow source compatibility after Trellis upgrades

---

## Related Files

- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/uninstall-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- `docs/workflows/新项目开发工作流/命令映射.md`

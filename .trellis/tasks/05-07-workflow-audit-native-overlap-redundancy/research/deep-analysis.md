# Deep Analysis: Native Trellis overlap and redundancy

## Scope

- workflow root: `docs/workflows/新项目开发工作流/`
- audit task: `.trellis/tasks/05-07-workflow-audit-native-overlap-redundancy/`
- current CLI: Codex
- compatible Trellis version: `0.5.0-rc.5`
- actual `trellis -v`: `0.5.0-rc.5` with exit code `0`

This analysis began as an audit refinement. Later remediation passes updated the two target `docs/workflows/新项目开发工作流/` maintainer docs, aligned the `.trellis/spec` installer / upgrade contract with the current Codex skills boundary, and cleaned residual stale carrier wording in platform README files, embedded NL routing text, installer / upgrade comments, and the brainstorm process table.

## Evidence Boundary

### Source Repo

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py:21-29` defines supported CLI types, Trellis version compatibility, current baseline patch names, and legacy carrier names.
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py:244-275` defines `.agents/skills/` as the canonical shared skills directory and `.codex/skills/` as the Codex-local secondary skills directory.
- `docs/workflows/新项目开发工作流/commands/install-workflow.py:1190-1314` deploys shared Codex workflow skills only to `.agents/skills/`, removes duplicate shared skills from `.codex/skills/`, and patches `trellis-continue` / `trellis-finish-work` in the active skills directory.
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py:639-665` checks shared skills only in `.agents/skills/` and treats matching files under `.codex/skills/` as duplicate drift.
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` was remediated after this audit to keep current fresh-baseline carriers as `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work`, keep `start` / `record-session` only as legacy compatibility inputs, and classify native implementation agents as Trellis-native with workflow dry-run `Agents: 0`.
- `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md` was remediated after this audit to make fresh-baseline checks target current carriers and classify `.codex/skills/` as Codex-local / duplicate-drift scope.
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md:247-263` correctly states current Trellis 0.5 carrier drift: `continue.md`, absent `record-session.md`, and Codex `trellis-continue` / `trellis-finish-work`.
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md:268-289` now aligns with the current installer and upgrade checker by requiring shared workflow skills in `.agents/skills/` only, treating `.codex/skills/` duplicate shared skills as drift, and limiting Codex baseline patches to `trellis-continue` / `trellis-finish-work` in the active skills directory.
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` now also aligns the implementation-agent contract with current behavior: `trellis-research`, `trellis-implement`, and `trellis-check` are Trellis-native, while workflow scripts only migrate legacy bare-name files and must not overlay native agent content.
- Residual stale wording under `commands/` has been cleaned so current fresh-baseline documentation and generated NL routing text prefer `continue` / `finish-work` and Codex `trellis-continue` / `trellis-finish-work`; `start` / `record-session` remain only in legacy compatibility paths, historical command examples, or old-target fallback code.

### Generated Target Project

Generated target root:

```text
/tmp/trellis-audit-native-overlap.HvTWIb
```

Observed generated baseline:

- `.trellis/.version` contains `0.5.0-rc.5`.
- Claude/OpenCode command baseline contains `continue.md` and `finish-work.md`.
- Claude/OpenCode command baseline does not contain `start.md` or `record-session.md`.
- `.agents/skills/` contains Trellis-native skills such as `trellis-continue` and `trellis-finish-work`.
- `.codex/skills/` exists but contains no shared skill files in this fixture.
- Claude/OpenCode/Codex native agent files for `trellis-research`, `trellis-implement`, and `trellis-check` are present before workflow install.

### Runtime Commands

Commands replayed from the source repo:

```bash
trellis -v
```

- exit code: `0`
- key output: `0.5.0-rc.5`

```bash
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/detect-embed-state.py --project-root /tmp/trellis-audit-native-overlap.HvTWIb --json
```

- exit code: `0`
- key output: `status: INITIAL_BASELINE_READY`, `cli_types: ["claude", "opencode", "codex"]`, `traces: []`, `blockers: []`, `upgrade_check_passed: false`

```bash
/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-audit-native-overlap.HvTWIb --dry-run
```

- exit code: `0`
- key output:
  - Claude/OpenCode deploy phase commands and patch `continue.md` / `finish-work.md`
  - Claude/OpenCode warn that `record-session.md` is absent and skip metadata closure injection
  - Codex deploys shared phase skills to `.agents/skills`
  - Codex patches `trellis-finish-work` and `trellis-continue`
  - summary reports `Agents: 0` for Claude, OpenCode, and Codex

## Corrected Judgment

### Confirmed Issues

1. Codex skills scope conflict was real, but it was a source-contract conflict, not an implementation defect. Current implementation, boundary docs, and `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` now agree that shared workflow skills belong in `.agents/skills/`, while `.codex/skills/` is checked for duplicate cleanup.
2. Retired carrier wording was real before remediation. Current runtime and source constants use `continue`, `finish-work`, `trellis-continue`, and `trellis-finish-work`; the two target maintainer docs now keep `start` and `record-session` only as legacy compatibility wording.
3. The boundary matrix quick table previously misclassified native `research / implement / check` agents as workflow-deployed. Runtime evidence shows fresh Trellis provides the `trellis-*` agent files and workflow dry-run reports `Agents: 0`; the table now says that explicitly.

### False Alarms

1. There is no current evidence that the installer still overlays native implementation agents.
2. Workflow phase commands and skills are not direct duplicates of native Trellis research/implement/check agents.
3. Patching `continue` and `finish-work` is not redundant by itself; it is the current workflow extension mechanism.

### Remaining Gaps

Formal install, `workflow-installed.json`, post-install hidden-directory artifact state, and `upgrade-compat.py --check` remain unverified in this task because `workflow-audit` requires Codex to stop before formal embed execution. A non-Codex handoff or explicitly approved direct-shell formal run is required to close that gap.

## Remediation Status

- Done in this pass: `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` now uses current carrier names, classifies implementation agents as Trellis-native, and treats `.codex/skills/` as Codex-local / duplicate-drift scope.
- Done in this pass: `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md` now updates fresh-baseline expectations from `start` / `record-session` to current `continue` / `finish-work` and Codex `trellis-continue` / `trellis-finish-work`.
- Done in follow-up spec-sync: `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` now aligns the Codex multi-directory contract with `.agents/skills/` shared deployment, `.codex/skills/` duplicate cleanup, optional disabled-entry cleanup where present, active-directory `trellis-continue` / `trellis-finish-work` patches, and Trellis-native agent ownership.
- Done in follow-up wording cleanup: `commands/claude/README.md`, `commands/opencode/README.md`, `commands/codex/README.md`, `commands/install-workflow.py`, `commands/upgrade-compat.py`, and `commands/brainstorm.md` no longer present `start` / `record-session` as current fresh-baseline carriers; remaining uses are legacy compatibility, historical examples, or fallback implementation identifiers.

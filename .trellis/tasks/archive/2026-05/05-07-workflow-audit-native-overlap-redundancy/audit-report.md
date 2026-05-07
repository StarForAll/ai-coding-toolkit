# workflow-audit: native Trellis overlap and redundancy

## Target

- workflow root: `docs/workflows/新项目开发工作流/`
- mode: task-based runtime audit
- current CLI: Codex
- compatible Trellis version: `0.5.0-rc.5`
- actual `trellis -v`: `0.5.0-rc.5`
- status: `docs/workflows/` maintainer-doc remediation, commands wording cleanup, and `.trellis/spec` contract remediation applied; formal install remains blocked by Codex handoff boundary

## Source Repo Evidence

- `[source repo]` `docs/workflows/新项目开发工作流/commands/workflow_assets.py:21-29` defines `ALL_CLI_TYPES = ["claude", "opencode", "codex"]`, `COMPATIBLE_TRELLIS_VERSION = "0.5.0-rc.5"`, current command patch targets `["continue", "finish-work"]`, Codex patch skill targets `["trellis-continue", "trellis-finish-work"]`, and legacy compatibility names `start`, `finish-work`, `record-session`.
- `[source repo]` `docs/workflows/新项目开发工作流/commands/workflow_assets.py:244-275` defines `.agents/skills/` as the canonical shared Codex/OpenCode skills directory and `.codex/skills/` as the Codex-local secondary skills directory.
- `[source repo]` `docs/workflows/新项目开发工作流/commands/install-workflow.py:1190-1314` says shared workflow skills only write to `.agents/skills/`, `.codex/skills/` keeps Codex-local skills and has duplicate shared skills removed, and active Codex baseline patches target `trellis-finish-work` and `trellis-continue`.
- `[source repo]` `docs/workflows/新项目开发工作流/commands/upgrade-compat.py:639-665` checks shared skills in `.agents/skills/` and treats matching shared skills under `.codex/skills/` as duplicate drift.
- `[source repo]` `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:11-18` states Trellis 0.5+ natively provides `trellis-research`, `trellis-implement`, and `trellis-check` agents, and workflow no longer overlays agent definitions.
- `[source repo]` `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` has been remediated to use current `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work` carriers, keep `start` / `record-session` only as legacy compatibility inputs, classify `.codex/skills/` as Codex-local / duplicate-drift scope, and classify `trellis-research` / `trellis-implement` / `trellis-check` as Trellis-native with workflow dry-run `Agents: 0`.
- `[source repo]` `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md` has been remediated to make current fresh-baseline checks target `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work`, with legacy `start` / `record-session` wording limited to old-target compatibility.
- `[source repo]` `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md:247-263` correctly records the current Trellis 0.5 carrier rename: `continue.md`, absent `record-session.md`, and Codex `trellis-continue` / `trellis-finish-work`.
- `[source repo]` `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md:268-289` now matches the implementation by requiring shared Codex workflow skills to deploy to `.agents/skills/` only, treating duplicate shared skills under `.codex/skills/` as drift, and limiting `trellis-continue` / `trellis-finish-work` baseline patches to the active skills directory.
- `[source repo]` `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` now classifies `trellis-research` / `trellis-implement` / `trellis-check` as Trellis-native assets and limits workflow responsibility to legacy bare-name migration, with no native agent content overlay.
- `[source repo]` `docs/workflows/新项目开发工作流/commands/claude/README.md`, `commands/opencode/README.md`, `commands/codex/README.md`, `commands/install-workflow.py`, `commands/upgrade-compat.py`, and `commands/brainstorm.md` have been cleaned so current fresh-baseline wording uses `continue` / `finish-work` and Codex `trellis-continue` / `trellis-finish-work`; residual `start` / `record-session` references are scoped to legacy compatibility, historical examples, or fallback implementation identifiers.

## Runtime Evidence

### Commands

- `[runtime command output]` `trellis -v`
  - exit code: `0`
  - key output: `0.5.0-rc.5`
- `[runtime command output]` `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/detect-embed-state.py --project-root /tmp/trellis-audit-native-overlap.HvTWIb --json`
  - exit code: `0`
  - key output: `status: INITIAL_BASELINE_READY`, `cli_types: ["claude", "opencode", "codex"]`, `traces: []`, `blockers: []`, `upgrade_check_passed: false`
- `[runtime command output]` `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-audit-native-overlap.HvTWIb --dry-run`
  - exit code: `0`
  - key output: deployed or planned phase commands/skills, patched `continue.md` / `finish-work.md` / `trellis-continue` / `trellis-finish-work`, warned that `record-session.md` is absent for Claude/OpenCode, and reported `Agents: 0` for Claude, OpenCode, and Codex.

### Generated Target Project

- `[generated target project]` `/tmp/trellis-audit-native-overlap.HvTWIb/.trellis/.version` contains `0.5.0-rc.5`.
- `[generated target project]` Fresh Trellis baseline contains `.claude/agents/trellis-research.md`, `.claude/agents/trellis-implement.md`, `.claude/agents/trellis-check.md`, `.opencode/agents/trellis-research.md`, `.opencode/agents/trellis-implement.md`, `.opencode/agents/trellis-check.md`, `.codex/agents/trellis-research.toml`, `.codex/agents/trellis-implement.toml`, and `.codex/agents/trellis-check.toml`.
- `[generated target project]` Fresh Trellis baseline contains `.claude/commands/trellis/continue.md`, `.claude/commands/trellis/finish-work.md`, `.opencode/commands/trellis/continue.md`, and `.opencode/commands/trellis/finish-work.md`.
- `[generated target project]` Fresh Trellis baseline does not contain `.claude/commands/trellis/start.md`, `.claude/commands/trellis/record-session.md`, `.opencode/commands/trellis/start.md`, `.opencode/commands/trellis/record-session.md`, `.agents/skills/start/SKILL.md`, `.agents/skills/finish-work/SKILL.md`, or `.agents/skills/record-session/SKILL.md`.
- `[generated target project]` Fresh Trellis baseline contains `.agents/skills/trellis-continue/SKILL.md` and `.agents/skills/trellis-finish-work/SKILL.md`.
- `[generated target project]` `.codex/skills/` exists in the fixture but contains no shared skill files. The corrected conclusion is not "the directory is absent"; it is "shared workflow skills are not written there, and duplicates there are treated as drift."

## Per-CLI Adaptation Conclusions

- Claude Code: `present-compatible-after-doc-remediation`. Fresh Trellis owns `.claude/agents/trellis-research.md`, `.claude/agents/trellis-implement.md`, and `.claude/agents/trellis-check.md`; workflow dry-run reports `Agents: 0`; the boundary docs now describe current `continue.md` / `finish-work.md` carriers and keep `start` / `record-session` only as legacy compatibility inputs.
- OpenCode: `present-compatible-after-doc-remediation`. Fresh Trellis owns `.opencode/agents/trellis-research.md`, `.opencode/agents/trellis-implement.md`, and `.opencode/agents/trellis-check.md`; workflow dry-run reports `Agents: 0`; the boundary docs now describe current `continue.md` / `finish-work.md` carriers and keep `start` / `record-session` only as legacy compatibility inputs.
- Codex: `present-compatible-after-doc-and-spec-remediation`. Fresh Trellis owns `.codex/agents/trellis-research.toml`, `.codex/agents/trellis-implement.toml`, and `.codex/agents/trellis-check.toml`; workflow dry-run reports `Agents: 0`, deploys shared phase skills to `.agents/skills`, and patches `trellis-continue` / `trellis-finish-work`. The remediated `docs/workflows/` maintainer docs and `.trellis/spec` contract now match that behavior.

## Codex Handoff Boundary

Formal install was not executed because the current executor is Codex and `workflow-audit` requires stopping at the formal embed boundary.

Default handoff order is Claude Code first, then OpenCode. Required handoff sequence for a non-Codex executor:

```bash
/ops/softwares/python/bin/python3 \
  /ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/detect-embed-state.py \
  --project-root /tmp/trellis-audit-native-overlap.HvTWIb --json

/ops/softwares/python/bin/python3 \
  /ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py \
  --project-root /tmp/trellis-audit-native-overlap.HvTWIb --dry-run

WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1 /ops/softwares/python/bin/python3 \
  /ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py \
  --project-root /tmp/trellis-audit-native-overlap.HvTWIb

/ops/softwares/python/bin/python3 \
  /ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
  --project-root /tmp/trellis-audit-native-overlap.HvTWIb --check
```

## Findings

### Confirmed Issues After Current Remediation

None remain in the audited docs/spec contract surface. The only remaining gap is formal install / post-install evidence.

### Fixed In This Remediation

#### P1: `.trellis/spec` conflicted on Codex distributed skill deployment scope

- priority: P1
- conclusion: The `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` drift has been remediated. It now requires distributed Codex workflow skills in `.agents/skills/` only, treats duplicates under `.codex/skills/` as drift, limits baseline patches to `trellis-continue` / `trellis-finish-work` in the active skills directory, and scopes backup / uninstall / force restore to the same write surfaces.
- evidence source: `[source repo]` `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md:268-283`
- evidence source: `[source repo]` `docs/workflows/新项目开发工作流/commands/install-workflow.py:1190-1260`
- evidence source: `[source repo]` `docs/workflows/新项目开发工作流/commands/upgrade-compat.py:639-665`
- evidence source: `[source repo]` `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:157-184`
- evidence source: `[runtime command output]` dry-run exit code `0`; output planned all Codex shared phase skills to `.agents/skills`
- evidence source: `[generated target project]` `.codex/skills/` exists but contains no shared skill files in the fixture
- validation action: Compared spec contract, installer implementation, upgrade checker behavior, boundary matrix, dry-run output, and generated target-project skills directories, then re-searched stale phrases after editing.
- impact scope: Maintainers following the spec should no longer misclassify the current installer as incomplete or reintroduce duplicate shared workflow skills under `.codex/skills/`.

- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`: retired fresh-baseline carriers were replaced with current `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work` wording; `start` / `record-session` now appear only as legacy compatibility inputs; native agents are classified as Trellis-native with workflow dry-run `Agents: 0`.
- `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`: fresh-baseline checks now target `continue` / `finish-work` and `trellis-continue` / `trellis-finish-work`; `.codex/skills/` is treated as Codex-local / duplicate-drift scope; legacy `start` / `record-session` are not fresh-baseline requirements.
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`: Codex multi-directory contract and regression checklist now match `.agents/skills/` shared deployment, `.codex/skills/` duplicate cleanup, optional disabled entry cleanup where present, and active-directory `trellis-continue` / `trellis-finish-work` patches; native agent contracts now prohibit workflow overlay of Trellis-native `trellis-*` agents.
- `commands/claude/README.md`, `commands/opencode/README.md`, `commands/codex/README.md`, `commands/install-workflow.py`, `commands/upgrade-compat.py`, and `commands/brainstorm.md`: residual fresh-baseline wording now points to `continue` / `finish-work` and Codex `trellis-continue` / `trellis-finish-work`; `start` / `record-session` are no longer described as current fresh-baseline requirements.

### False Alarms

- No current runtime evidence shows that the workflow installer overlays or duplicates native `trellis-research`, `trellis-implement`, or `trellis-check` agent definitions. The confirmed problem is a stale quick-table row, not current installer behavior.
- Workflow phase entries `feasibility`, `design`, `plan`, `test-first`, `project-audit`, `review-gate`, and `delivery` are not direct duplicates of native Trellis research/implement/check agents. They are higher-level workflow stage carriers.
- Patching `continue` and `finish-work` is not inherently redundant. The dry-run shows the workflow augments current native baseline carriers rather than rebuilding the full Trellis baseline.

### Evidence Gaps

- Formal install was not run because the current executor is Codex and the skill requires stopping before formal embed execution.
- Actual installed `workflow-installed.json`, backup directories, `.trellis/workflow.md` patch, AGENTS NL routing block, post-install artifact set, and `upgrade-compat.py --check` remain unverified until the handoff sequence runs in Claude Code, OpenCode, or an explicitly approved direct shell execution with `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1`.
- The earlier sandbox failure for `trellis init` remains recorded as a runtime-boundary observation, but it is not used as evidence for workflow correctness because the escaped rerun had already created the fixture successfully.

## Recommendation

The `docs/workflows/新项目开发工作流/` maintainer-doc remediation, commands wording cleanup, and `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` contract remediation are complete, including Codex skills scope and Trellis-native agent ownership. The only remaining audit evidence gap is formal install plus post-install `upgrade-compat.py --check` through a non-Codex handoff or explicitly approved direct-shell execution.

## Current Remediation Boundary

- Workflow source assets under `docs/workflows/新项目开发工作流/` have been modified only for the confirmed maintainer-doc and residual commands wording drift described above.
- Task-local files have been updated with refined evidence, corrected descriptions, and completed `.trellis/spec` contract remediation.
- Formal install and post-install verification remain a controlled handoff gap.

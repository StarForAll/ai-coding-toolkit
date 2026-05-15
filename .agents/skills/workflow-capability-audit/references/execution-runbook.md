# workflow-capability-audit Execution Runbook

Canonical execution engine:

- `docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py`

This script is the shared execution engine for the repo-local maintainer skill.
Do not duplicate runtime logic across `.agents/skills/` and `.claude/skills/`.

## 1. Version Gate Only

Use this when you only need the pre-run gate result:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py \
--json
```

## 2. Missing Compatible Anchor

If `COMPATIBLE_TRELLIS_VERSION` is missing, rerun with the user-supplied value:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py \
--compatible-trellis-version 0.4.0 \
--json
```

This is the sole allowed pre-audit source edit exception:

- the script may write the supplied value into `workflow_assets.py`
- then rerun the version gate

## 3. Full Upgrade Audit

When `current > compatible`, the script creates or switches into the audit task,
creates fresh `A/B`, installs the workflow into `B`, and initializes:

- `prd.md`
- `capability-report.md`

If a `workflow-capability-audit` task is already active, stop instead of creating another full-audit task. Ask the user to resume or complete the existing audit first.

Always pass `--current-cli` inferred from the current runtime (the script does not auto-detect the CLI):

- accepted values are exactly `claude`, `opencode`, or `codex`
- reject any other value before task creation or fixture setup

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py \
--current-cli claude \
--json
```

Returned JSON includes at least:

- `task_dir`
- `a_root`
- `b_root`
- `capability_report`

Codex execution note:

- when this skill runs from Codex in this repository and `.trellis/config.yaml`
  keeps `codex.dispatch_mode: inline`, keep the audit analysis in the main
  Codex session
- do not manually spawn subagents for Step B review or official-doc comparison
- this execution-model rule is separate from the Codex runtime boundary below

Native CLI adaptation evidence rule:

- when the audit draws Claude Code / OpenCode / Codex compatibility conclusions,
  verify them against both the latest official CLI documentation available at
  execution time and repo-local evidence from the current workflow authoring
  repository
- the minimum repo-local pack is `CLI原生适配边界矩阵.md`, the matching
  platform README, and the carrier files that implement the claim
- if the generated `capability-report.md` does not already contain
  `## Native CLI Adaptation Evidence`, fill that section during the AI review
  step before finalizing the audit conclusion
- record per CLI the official-doc source checked, the repo-local evidence
  checked, the agreement/discrepancy status, and any conservative-classification
  rationale used to resolve disagreements
- if those evidence tracks disagree, keep the discrepancy visible in
  `capability-report.md`, explain whether it is an intentional local
  adaptation, stale repo guidance, or an unresolved evidence gap, and prefer
  `unclear`, `present-but-gated-expected`, or another evidence-backed
  conservative classification instead of flattening it into a memory-based
  answer

Task-state boundary:

- the script now reads and restores the active task through Trellis' session-scoped runtime state (`.trellis/.runtime/sessions/`) rather than a legacy global `.trellis/.current-task` file
- rollback after task creation must restore the previous session-scoped active task when one existed in the current executor context
- if no session identity is available during rollback, task restoration degrades to a warning rather than failing the cleanup path itself

Codex boundary:

- if fresh A/B baseline creation fails only under Codex because `trellis init`
  cannot be trusted inside the current Codex runtime/sandbox, do not conclude
  that the user's actual machine environment is broken yet
- rerun the same `trellis init` check in a real shell or another non-Codex executor
  on the same machine before classifying the machine as environment-broken
- if no such recheck is available, report the result as Codex runtime evidence gap
  rather than a confirmed machine-environment defect

## 4. Supplemental Capability Validation

Use this only after one audit round already exists.

Required:

- `--task-dir`
- `--supplemental-capability`

Optional evidence hints:

- `--surface workflow-managed|workflow-dependent-native`
- `--mechanism ...`
- `--claude-path ...`
- `--opencode-path ...`
- `--codex-path ...`

Example:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py \
--task-dir .trellis/tasks/05-02-workflow-capability-audit \
--supplemental-capability custom-supplemental-capability \
--surface workflow-dependent-native \
--mechanism "Supplemental capability confirmed from current A/B evidence." \
--claude-path AGENTS.md \
--json
```

## 5. Confirmed Fix Lifecycle Updates

Use these flags after the user confirms the audit conclusion and the workflow
enters the compatibility-fix lifecycle.

Supported update groups:

- `--confirm-fix-scope`
- `--record-correction`
- `--record-revalidation`
- `--finalize-fixture-destruction`

Example:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py \
--task-dir .trellis/tasks/05-02-workflow-capability-audit \
--confirm-fix-scope "Confirm patch markers and capability matrix updates." \
--record-correction "Updated workflow source for Trellis version-upgrade compatibility." \
--record-revalidation "Revalidated capability report after confirmed correction." \
--finalize-fixture-destruction \
--json
```

## 6. Post-Audit Anchor Write-Back

After a confirmed successful audit, the script writes the current `trellis -v`
value back into `COMPATIBLE_TRELLIS_VERSION` in `workflow_assets.py`. This
write-back is a mandatory post-audit step, not optional.

Anchor promotion is gated by two conditions that must both be satisfied:

1. `--finalize-fixture-destruction` is passed (outer gate)
2. `capability-report.md` has recorded items under `## Post-Fix Revalidation`
   (inner gate — revalidation may have been recorded in a prior call)

The write-back does NOT happen:

- during the initial full audit
- when only `--confirm-fix-scope` or `--record-correction` or
  `--record-revalidation` is passed without `--finalize-fixture-destruction`
- when `--finalize-fixture-destruction` is passed but the report has no
  recorded post-fix revalidation items

No-fix-compatible path:

- if the audit concludes the workflow is already compatible as-is, `--confirm-fix-scope` may still record that conclusion
- in that path, `## Applied Corrections` may remain `- none yet`
- anchor promotion is still allowed once post-fix / post-audit revalidation is recorded and fixture destruction is explicitly finalized

Before that write-back, `--task-dir` must first validate as a real
`workflow-capability-audit` task. Failed or mistyped fix-lifecycle requests
must not mutate `workflow_assets.py`.

The write-back:

- uses the exact literal string from `trellis -v`, preserving any prerelease suffix
- does NOT round up to a stable version
- applies even when the workflow was already compatible as-is or no workflow
  source edits were needed beyond the initialization exception

## 7. Boundaries

- version gate happens before task creation or audit artifact creation
- full audit is allowed only when `current > compatible`
- full audit must not create a second active `workflow-capability-audit` task when one is already active
- if a child audit task is created under a parent task and setup later fails, rollback must also remove the stale parent `children` link
- equal version stops
- older version blocks
- supplemental validation reuses the same A/B and the same `capability-report.md`
- `COMPATIBLE_TRELLIS_VERSION` is promoted to the exact `trellis -v` value when `--finalize-fixture-destruction` is passed and the report has recorded post-fix revalidation items
- Codex-local `trellis init` failures must be rechecked outside Codex before they
  are treated as confirmed machine-environment failures

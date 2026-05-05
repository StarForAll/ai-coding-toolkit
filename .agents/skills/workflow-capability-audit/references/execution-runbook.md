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

After the user confirms the audit by running `--confirm-fix-scope`, the script
automatically writes the current `trellis -v` value back into
`COMPATIBLE_TRELLIS_VERSION` in `workflow_assets.py`. The write-back does NOT
happen during the initial full audit — it happens only when the user explicitly
confirms the audit by entering the fix lifecycle.

The write-back:

- uses the exact literal string from `trellis -v`, preserving any prerelease suffix
- does NOT round up to a stable version
- applies even when the workflow was already compatible as-is

No separate flag is required; the anchor promotion is a side effect of the first
`--confirm-fix-scope` invocation after a successful full audit.

## 7. Boundaries

- version gate happens before task creation or audit artifact creation
- full audit is allowed only when `current > compatible`
- full audit must not create a second active `workflow-capability-audit` task when one is already active
- equal version stops
- older version blocks
- supplemental validation reuses the same A/B and the same `capability-report.md`
- `COMPATIBLE_TRELLIS_VERSION` is promoted to the exact `trellis -v` value when the user confirms the audit via `--confirm-fix-scope`
- Codex-local `trellis init` failures must be rechecked outside Codex before they
  are treated as confirmed machine-environment failures

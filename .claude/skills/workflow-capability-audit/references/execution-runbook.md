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

## 6. Boundaries

- version gate happens before task creation or audit artifact creation
- full audit is allowed only when `current > compatible`
- equal version stops
- older version blocks
- supplemental validation reuses the same A/B and the same `capability-report.md`
- final compatibility-anchor promotion is **not** auto-written by this audit script

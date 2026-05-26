# workflow-validate-matrix Skill Specification

> Behavioral and packaging contract for the installable skill `skills/workflow-validate-matrix/`.

---

## Scenario: Runtime-Bundled Installable Matrix Validator

### 1. Scope / Trigger

- Trigger: modifying `skills/workflow-validate-matrix/**`
- Trigger: modifying `scripts/sync-workflow-validate-matrix-runtime.py`
- Trigger: modifying workflow command/runtime files that are synced into the matrix runtime bundle
- Trigger: changing how the skill locates or validates workflow installer/runtime logic
- Trigger: changing how the skill is expected to be reinstalled globally through Skills CLI

This concern is required when the change crosses these layers:

```text
workflow source assets -> synced runtime bundle under skills/workflow-validate-matrix/
-> global Skills CLI install payload -> runtime drift guard -> matrix execution
```

### 2. Signatures

Skill-side runtime sync command:

```bash
/ops/softwares/python/bin/python3 scripts/sync-workflow-validate-matrix-runtime.py
/ops/softwares/python/bin/python3 scripts/sync-workflow-validate-matrix-runtime.py --check
```

Global reinstall path:

```bash
npx skills add . -g -y
```

Matrix runner:

```bash
/ops/softwares/python/bin/python3 skills/workflow-validate-matrix/validate-matrix.py \
  [--keep-temp] \
  [--output PATH]
```

### 3. Contracts

- The skill must keep `trellis` as an explicit runtime prerequisite.
- The skill must not depend on live source-repo `docs/workflows/新项目开发工作流/commands/*.py` paths at execution time.
- The skill must execute against a synced runtime bundle under:
  `skills/workflow-validate-matrix/runtime_bundle/workflow/`
- The runtime bundle must be generated from a single source of truth in the workflow product source, not maintained manually as an independent implementation.
- If the authoring repo is available and the runtime bundle drifts from the source of truth, the skill must fail closed.
- Drift failure output must provide concrete remediation:
  1. run the sync script
  2. reinstall the global skill with Skills CLI
- Runtime drift must never degrade to a warning-only path that still runs the matrix.
- Bundle-sync logic must exclude test caches / compiled artifacts and must detect:
  - missing bundle files
  - content drift
  - extra stale bundle files
- Shared workflow scripts that rely on source-repo discovery must support bundle execution by resolving the host source repo through explicit env override and/or upward search, not only by fixed `parents[N]` assumptions.

### 4. Validation & Error Matrix

| Condition | Required Behavior |
|-----------|-------------------|
| Bundle root missing | hard fail with sync + reinstall instructions |
| Bundle content drift | hard fail with sync + reinstall instructions |
| Authoring repo unavailable | allow execution to continue against bundled runtime |
| `trellis` missing | stop before scenario execution |
| Runtime bundle in sync | continue normally |
| Sync script `--check` finds drift | exit non-zero |
| Sync script writes bundle | emit follow-up reminder to reinstall global skill |

### 5. Good / Base / Bad Cases

- Good:
  - workflow runtime source changes
  - maintainer runs sync script
  - `--check` passes
  - global skill is reinstalled
  - matrix runs successfully from bundled runtime

- Base:
  - authoring repo is present
  - bundle is already in sync
  - matrix runs without touching live `docs/workflows/.../commands/` paths

- Bad:
  - workflow runtime source changes but bundle is not synced
  - matrix still runs against stale copied code
  - sync guidance is vague or missing
  - bundled runtime depends on fixed repo-relative `parents[4]` paths and breaks outside the source tree

### 6. Tests Required

- Unit tests for bundle helper behavior:
  - version/schema extraction from bundle
  - drift failure includes sync + reinstall instructions
  - authoring repo detection works in the source repo
- Sync validation:
  - `scripts/sync-workflow-validate-matrix-runtime.py --check` must fail on drift
  - `./scripts/validate-skills.sh` must invoke the bundle drift check
- Runtime regression:
  - real matrix run succeeds using the bundled runtime path
- Workflow command regression:
  - at least one installer-side test must still pass after replacing fixed `parents[4]` assumptions with source-root resolution

### 7. Wrong vs Correct

#### Wrong

- Put the only shared implementation inside the skill directory and make workflow source commands import from the skill.
- Allow matrix execution to continue with a stale bundle after printing only a warning.
- Rely on `Path(__file__).resolve().parents[4]` as the only way to find the host repo.

#### Correct

- Keep workflow-owned runtime code as the source of truth and sync a generated bundle into the skill payload.
- Stop immediately when bundle drift is detected and print exact sync + reinstall commands.
- Resolve the host source repo through explicit env override and/or upward search so the same code can run from both the source tree and the bundled payload.

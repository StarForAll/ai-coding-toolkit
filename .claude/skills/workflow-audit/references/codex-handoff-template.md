# Codex Handoff Template

When `workflow-audit` reaches the point where a formal embed into a temporary target project would need to be executed and the current main executor is Codex, it must stop the formal embed action and output the following handoff block.

The outer fence uses 4 backticks so the inner triple-backtick `bash` blocks render correctly when the takeover CLI reads this output.

````markdown
## Codex Handoff

### Why execution stops here
- The audit has reached the formal temporary-project embed step
- By workflow contract, Codex must not lead the first formal embed execution

### Default takeover order
1. Claude Code
2. OpenCode

### Takeover boundary
- Continue this handoff in a main interactive Claude Code or OpenCode session
- Do not run the continuation through an agent or sub-agent

### Execution context for the takeover CLI
- Run all commands below from the workflow source repo's working directory (the repo that contains `<WORKFLOW_ROOT_DIR>`), NOT from inside `<TARGET_PROJECT_ROOT>`
- `<WORKFLOW_ROOT_DIR>` points to the workflow source root (e.g. `docs/workflows/新项目开发工作流/`)
- `<TARGET_PROJECT_ROOT>` points to the `/tmp` temporary target project that received `trellis init`
- The `--project-root` argument always targets `<TARGET_PROJECT_ROOT>`; the script itself is invoked from `<WORKFLOW_ROOT_DIR>/commands/`

### Where the next CLI should execute
- Workflow Root Dir: `<WORKFLOW_ROOT_DIR>`
- Temporary Target Project Root: `<TARGET_PROJECT_ROOT>`

### Next command skeleton
```bash
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/detect-embed-state.py \
  --project-root <TARGET_PROJECT_ROOT>
```

```bash
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/install-workflow.py \
  --project-root <TARGET_PROJECT_ROOT> \
  --dry-run
```

```bash
WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1 \
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/install-workflow.py \
  --project-root <TARGET_PROJECT_ROOT>
```

The `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` env var is mandatory: `install-workflow.py` rejects formal install when it is unset, to enforce the "Codex must not lead formal embed" boundary.

```bash
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/upgrade-compat.py \
  --project-root <TARGET_PROJECT_ROOT> \
  --check
```

### Evidence that must be brought back
- `detect-embed-state.py` result
- `install-workflow.py --dry-run` result
- key `install-workflow.py` output
- `upgrade-compat.py --check` result
- post-install verification result
- any anomalies / failures encountered

### Takeover CLI behavior limits
- main interactive CLI session only; do not use agents/sub-agents for this takeover
- runtime validation only
- no workflow source-file edits during the audit stage
- returned evidence must be merged back into the current `audit-report.md`
````

## Override Rule

If the user has already stated in natural language that:

- Claude Code is unavailable
- or OpenCode is the only usable non-Codex CLI

then the default order may be overridden, but the handoff must still explain why.

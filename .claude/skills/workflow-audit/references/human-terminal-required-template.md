# Human Terminal Required Template

When `workflow-audit` reaches the point where the formal embed command chain would need to be executed, it must stop AI-driven execution and output the following human-terminal-required block.

The outer fence uses 4 backticks so the inner triple-backtick `bash` blocks render correctly when the operator reads this output.

````markdown
## Human Terminal Required

### Why execution stops here
- The audit has reached the formal temporary-project embed step
- By workflow contract, no AI CLI or agent may lead the first formal embed execution

### Execution boundary
- Continue only in a human-operated interactive system terminal
- Do not run the continuation through Claude Code, OpenCode, Codex, or any agent/sub-agent shell/tool path

### Execution context for the human terminal
- Run all commands below from the workflow source repo's working directory (the repo that contains `<WORKFLOW_ROOT_DIR>`), NOT from inside `<TARGET_PROJECT_ROOT>`
- `<WORKFLOW_ROOT_DIR>` points to the workflow source root (e.g. `docs/workflows/新项目开发工作流/`)
- `<TARGET_PROJECT_ROOT>` points to the `/tmp` temporary target project that received `trellis init`
- The `--project-root` argument always targets `<TARGET_PROJECT_ROOT>`; the script itself is invoked from `<WORKFLOW_ROOT_DIR>/commands/`

### Where the operator should execute
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
  --project-id <PROJECT_ID> \
  --profile <PROFILE> \
  --dry-run
```

```bash
WORKFLOW_EMBED_HUMAN_CONFIRMED=1 \
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/install-workflow.py \
  --project-root <TARGET_PROJECT_ROOT> \
  --project-id <PROJECT_ID> \
  --profile <PROFILE>
```

Replace `<PROFILE>` with `personal` or `outsourcing`. The `WORKFLOW_EMBED_HUMAN_CONFIRMED=1` env var is mandatory, and the operator must also complete the terminal-side explicit confirmation prompt for `EMBED <PROJECT_ID>`.

```bash
/ops/softwares/python/bin/python3 <WORKFLOW_ROOT_DIR>/commands/upgrade-compat.py \
  --project-root <TARGET_PROJECT_ROOT> \
  --check
```

### Evidence that must be brought back
- `detect-embed-state.py` result
- `install-workflow.py --dry-run` result
- the formal install terminal transcript, including the explicit confirmation prompt/response
- `upgrade-compat.py --check` result
- post-install verification result
- any anomalies / failures encountered

### Human operator limits
- runtime validation only
- no workflow source-file edits during the audit stage
- returned evidence must be merged back into the current `audit-report.md`
````

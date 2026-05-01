# Codex Handoff Template

When `workflow-audit` reaches the point where a formal embed into a temporary target project would need to be executed and the current main executor is Codex, it must stop the formal embed action and output the following handoff block.

```markdown
## Codex Handoff

### Why execution stops here
- The audit has reached the formal temporary-project embed step
- By workflow contract, Codex must not lead the first formal embed execution

### Default takeover order
1. Claude Code
2. OpenCode

### Where the next CLI should execute
- Workflow Root: `<workflow_path>`
- Temporary Target Project: `<tmp-project-root>`

### Next command skeleton
```bash
/ops/softwares/python/bin/python3 <workflow_root>/commands/detect-embed-state.py \
  --project-root <tmp-project-root>
```

```bash
/ops/softwares/python/bin/python3 <workflow_root>/commands/install-workflow.py \
  --project-root <tmp-project-root> \
  --dry-run
```

```bash
WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1 \
/ops/softwares/python/bin/python3 <workflow_root>/commands/install-workflow.py \
  --project-root <tmp-project-root>
```

```bash
/ops/softwares/python/bin/python3 <workflow_root>/commands/upgrade-compat.py \
  --project-root <tmp-project-root> \
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
- runtime validation only
- no workflow source-file edits during the audit stage
- returned evidence must be merged back into the current `audit-report.md`
```

## Override Rule

If the user has already stated in natural language that:

- Claude Code is unavailable
- or OpenCode is the only usable non-Codex CLI

then the default order may be overridden, but the handoff must still explain why.

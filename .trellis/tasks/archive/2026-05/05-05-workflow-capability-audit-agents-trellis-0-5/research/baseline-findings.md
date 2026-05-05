# Trellis 0.5 baseline findings

## Purpose

Record the concrete baseline evidence used to adapt `docs/workflows/新项目开发工作流/` for Trellis `0.5.0-rc.3`.

## Version gate evidence

- `trellis -v` returned `0.5.0-rc.3`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` currently declares `COMPATIBLE_TRELLIS_VERSION = "0.4.0"`
- Therefore `current > compatible`, so capability audit is in-scope

## Canonical audit failure chain

1. Running:

   ```bash
   /ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/workflow-capability-audit.py --current-cli codex --json
   ```

2. In sandboxed execution, A/B fixture creation fails because `trellis init` cannot complete Python probing.
3. Re-running outside sandbox gets past fixture creation, then fails during `install-workflow.py`.
4. Concrete failure:

   - `[codex] 活动 skills 目录缺少 finish-work 基线，无法注入 workflow 项目化补丁：.agents/skills`
   - `[codex] 活动 skills 目录缺少 start 基线，无法注入 workflow Phase Router 补丁：.agents/skills`

## Fresh Trellis 0.5 baseline fixture

Fixture root:

- `/tmp/trellis-0-5-baseline-p2fO5L`

Creation command:

```bash
trellis init --claude --opencode --codex -u xzc -y
```

## Observed carrier layout

### `.agents/skills/`

Present baseline skills:

- `trellis-before-dev`
- `trellis-brainstorm`
- `trellis-break-loop`
- `trellis-check`
- `trellis-continue`
- `trellis-finish-work`
- `trellis-meta`
- `trellis-update-spec`

Not present:

- plain `start`
- plain `finish-work`
- plain `brainstorm`
- plain `check`

### `.codex/agents/`

Present managed agents:

- `trellis-research.toml`
- `trellis-implement.toml`
- `trellis-check.toml`

### `.codex/`

Other Codex-native carriers:

- `config.toml`
- `hooks.json`
- `hooks/session-start.py`
- `hooks/inject-workflow-state.py`

### `AGENTS.md`

The Trellis-managed block still documents:

- `.agents/skills/` as reusable Trellis skills
- `.codex/agents/` as optional custom subagents

## Immediate compatibility implication

The workflow product still assumes a Codex/OpenCode shared-skill baseline that exposes plain `start` and `finish-work`. Trellis `0.5.0-rc.3` replaced that assumption with:

- `trellis-*` skill entrypoints
- `trellis-*` Codex agents
- Codex hook/config carriers

Any install, uninstall, upgrade, or capability-audit logic that hard-requires `.agents/skills/start/SKILL.md` or `.agents/skills/finish-work/SKILL.md` is now stale.

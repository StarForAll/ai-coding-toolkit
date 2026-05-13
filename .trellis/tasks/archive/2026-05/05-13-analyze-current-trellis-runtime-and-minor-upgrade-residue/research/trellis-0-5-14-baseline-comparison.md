# Research: trellis 0.5.14 baseline comparison

- Query: Compare the current live runtime in this repository against a fresh Trellis 0.5.14 init baseline to separate upstream baseline adoption from repo-local overlays or residual drift.
- Scope: internal
- Date: 2026-05-13

## Findings

### Baseline Setup

- `trellis --version` returned `0.5.14`.
- Fresh baseline path: `/tmp/trellis-live-runtime-sxc8p7`
- Baseline command: `trellis init --codex --claude --opencode --qoder -u xzc -y`

### Files Found

| File Path | Comparison Result |
| --- | --- |
| `.codex/hooks.json` | Matches fresh 0.5.14 baseline exactly. |
| `.codex/config.toml` | Matches fresh 0.5.14 baseline exactly. |
| `.codex/agents/trellis-research.toml` | Matches fresh 0.5.14 baseline exactly. |
| `.claude/agents/trellis-research.md` | Matches fresh 0.5.14 baseline exactly. |
| `.qoder/agents/trellis-research.md` | Matches fresh 0.5.14 baseline exactly. |
| `.opencode/agents/trellis-research.md` | Matches fresh 0.5.14 baseline exactly. |
| `.qoder/settings.json` | Matches fresh 0.5.14 baseline exactly. |
| `.opencode/lib/trellis-context.js` | Matches fresh 0.5.14 baseline exactly. |
| `.opencode/plugins/inject-subagent-context.js` | Matches fresh 0.5.14 baseline exactly. |
| `.opencode/plugins/inject-workflow-state.js` | Matches fresh 0.5.14 baseline exactly. |
| `.opencode/plugins/session-start.js` | Matches fresh 0.5.14 baseline exactly. |
| `.trellis/scripts/common/safe_commit.py` | Matches fresh 0.5.14 baseline exactly. |
| `.trellis/scripts/common/task_store.py` | Matches fresh 0.5.14 baseline exactly. |
| `.trellis/scripts/common/session_context.py` | Matches fresh 0.5.14 baseline exactly. |
| `.claude/settings.json` | Differs only by repo-local `statusLine` stanza; hook timeouts already match baseline. |

### What This Means

1. Most runtime residue in `git diff` is not random local experimentation. It is the repo catching up to the current Trellis 0.5.14 baseline.
2. Matching the baseline is not the same as matching this repository's desired live contract. The best example is `trellis-research`: the fresh 0.5.14 baseline already contains the simplified carriers, but this repo's own live spec still expects richer research capabilities and stronger task-resolution fallback.
3. The only obvious baseline-vs-live overlay among the core runtime files I compared is Claude's `statusLine` addition, which looks intentional and self-consistent.

### Related Specs

- `.trellis/spec/agents/index.md`
- `.trellis/spec/platforms/codex-workflow-behavior.md`
- `.trellis/workflow.md`

## Caveats / Not Found

- I only compared the runtime surfaces relevant to the current working-tree residue. I did not exhaustively diff every generated file under the baseline tree.
- Baseline parity is evidence about upstream adoption, not proof that the repo-local contract is correct.

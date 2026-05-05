# Research: platform agent drift classification

- Query: 判断当前仓库不同平台下的 Trellis agents 差异，哪些是平台能力差异造成的合理差异，哪些更像维护漂移
- Scope: internal
- Date: 2026-05-05

## Findings

### Files Found

| File Path | Description |
| --- | --- |
| `.claude/settings.json` | Claude hooks wiring，包含 SessionStart / UserPromptSubmit / inject-subagent-context |
| `.codex/hooks.json` | Codex hooks wiring，仅 SessionStart / UserPromptSubmit |
| `.qoder/settings.json` | Qoder hooks wiring，仅 SessionStart / UserPromptSubmit |
| `.kiro/agents/trellis-implement.json` | Kiro implement agent，agentSpawn hook 注入 |
| `.codex/agents/trellis-implement.toml` | Codex implement agent，self-load task/spec/jsonl |
| `.claude/agents/trellis-implement.md` | Claude implement agent，薄 agent body，依赖 hook push |
| `.qoder/agents/trellis-implement.md` | Qoder implement agent，带 self-load 段 |
| `.opencode/plugins/inject-subagent-context.js` | OpenCode subagent context plugin |

### Platform-capability differences (reasonable)

#### Claude

- Claude has explicit sub-agent context injection wiring via `PreToolUse` for `Task` and `Agent`. See `.claude/settings.json:38`.
- Because context is hook-pushed, `.claude/agents/trellis-implement.md` and `.claude/agents/trellis-check.md` do not need a self-loading prelude.

Classification: **reasonable platform difference**

#### Codex

- Codex only wires `SessionStart` and `UserPromptSubmit`. See `.codex/hooks.json:2`.
- There is no parallel subagent-context hook in the current Codex integration, so `.codex/agents/trellis-implement.toml` and `.codex/agents/trellis-check.toml` must instruct the agent to self-load current task, `prd.md`, and JSONL files. See `.codex/agents/trellis-implement.toml:5`, `.codex/agents/trellis-check.toml:5`.

Classification: **reasonable platform difference**

#### Kiro

- Kiro agent definitions include an `agentSpawn` hook invoking `.kiro/hooks/inject-subagent-context.py`. See `.kiro/agents/trellis-implement.json:6`, `.kiro/agents/trellis-check.json:6`.
- Therefore Kiro can reasonably use thinner `instructions` bodies without a duplicated self-load section.

Classification: **reasonable platform difference**

#### Qoder

- Qoder currently wires only `SessionStart` and `UserPromptSubmit`, not a dedicated subagent injection hook. See `.qoder/settings.json:2`.
- Because of that, `.qoder/agents/trellis-implement.md` and `.qoder/agents/trellis-check.md` carrying self-load instructions is also a reasonable adaptation.

Classification: **reasonable platform difference**

#### OpenCode

- OpenCode has plugin-based subagent context injection in `.opencode/plugins/inject-subagent-context.js`.
- The deployed agent files still include a self-load fallback section. This is more redundant than Claude/Kiro, but still explainable as compatibility / belt-and-suspenders design, not necessarily a bug by itself.

Classification: **mostly reasonable platform difference**

### Potential maintenance drift

#### Drift 1: spec classification needed correction

Earlier wording in `.trellis/spec/agents/index.md` grouped context-loading
differences into `format-only`. This audit corrected the spec to separate:

- `context-adapter`: same core role, different context-loading contract
- `format-only`: only serialization/frontmatter wrapper difference

That is not fully precise:

- Claude implement/check agents do not include self-load instructions.
- Qoder and Codex implement/check agents do include explicit self-load instructions.
- OpenCode research agent includes a slightly different forbidden-path example set (`.opencode/` mentioned explicitly).

These are still mostly **platform-driven**, but they are not purely frontmatter-only differences.

#### Drift 2: duplicated core bodies raise future divergence risk

Even where differences are currently reasonable, the repo still keeps independent full copies of agent prompts per platform instead of a single source layer.

Evidence:
- `.trellis/spec/agents/index.md` explicitly states `agents/` source layer is empty and live files are edited directly.
- Archived task `05-04-drift-convergence` already recorded this as a structural source/deploy drift issue.

This means:
- current differences are not necessarily bugs now
- but they are structurally drift-prone and should be normalized once `agents/` source assets are implemented

Classification: **maintenance drift risk**, not current runtime bug

### Final classification table

| Surface | Classification | Why |
| --- | --- | --- |
| Claude thin agents vs Codex/Qoder self-load agents | Reasonable platform difference | Hook-push vs agent-pull context model |
| Kiro hook-based JSON agents vs Markdown/TOML formats | Reasonable platform difference | Platform file format and spawn-hook model differ |
| OpenCode plugin injection + self-load fallback | Reasonable but redundant | Likely compatibility bias rather than contract break |
| Agent spec classification | Corrected in this audit | `.trellis/spec/agents/index.md` now separates `context-adapter` from `format-only`, matching the live hook/self-load split. |
| Direct per-platform maintenance without source layer | Maintenance drift risk | Any future contract update must be manually propagated |

## Caveats / Not Found

- No evidence was found that current agent differences are causing an immediate runtime failure in this repo.
- The main issue is accuracy of classification and future drift risk, not proof of a current broken platform.

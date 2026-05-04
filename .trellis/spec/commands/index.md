# Command Asset Specification

> **⚠️ IMPORTANT**: This spec describes the TARGET architecture, not current practice.
> Current workflow: Edit directly in `.claude/commands/`、`.opencode/commands/`
> To implement this architecture: populate `commands/<tool>/<id>/` source layer, then enable sync to tool directories

> How to author command source assets for multiple AI CLI tools.

---

## Current State

**Source asset directories** (`commands/claude/<id>/`、`commands/codex/<id>/`、`commands/shell/<id>/`) are empty — only top-level README files exist, no actual scripts.

**Tool command directories** (`.claude/commands/`、`.opencode/commands/`) contain live commands,
but are **not synchronized** from `commands/<tool>/` source.
Current practice is **direct editing** in tool directories.

**To close the gap:** populate `commands/<tool>/<id>/` with real scripts, then apply the deployment mapping.

---

## Scope

This spec covers the **source asset layer**: `commands/claude/`, `commands/codex/`, `commands/shell/`.

**Out of scope:**
- `.claude/commands/`, `.opencode/commands/` — these are each tool's internal command discovery directories, managed independently by each tool
- Trellis workflow commands (start, brainstorm, finish-work, etc.) — these live directly in tool deployment directories and are not part of this spec

---

## Source Asset Structure

```
commands/
  claude/             # Claude Code 特有的自定义命令/脚本
    <command-id>/
      README.md       # 用途、依赖、运行方式、副作用（必需）
      script.sh       # 主脚本（或 .py, .js 等）
      config.json     # 配置（可选）
  codex/              # Codex CLI 特有的辅助资产（非项目级 slash command 目录）
    <command-id>/
      README.md
      script.sh
  shell/              # 平台无关的通用脚本
    <command-id>.sh
    README.md
```

---

## Naming Conventions

- Command IDs: kebab-case: `deploy-helper`, `test-runner`, `validate-skills`
- Script files: Match command ID: `deploy-helper.sh`
- Subdirectories: One per command (or group of strongly related commands)

---

## README.md per Command (Required)

Must include:
- **Problem**: What problem this command solves
- **Dependencies**: Required tools, environment, languages
- **Usage**: How to run with common parameters
- **Side Effects**: What files it modifies, git state changes
- **Target Tool(s)**: Which AI CLI this command is designed for

---

## Subdirectory Conventions

### `commands/claude/`

Claude Code specific commands. These may include:
- MCP tool definitions
- Hook scripts for Claude Code lifecycle events
- Claude-specific workflow scripts

### `commands/codex/`

OpenAI Codex CLI specific helper assets. These may include:
- Codex-specific config snippets or bootstrap helpers
- Codex workflow packaging helpers that emit skills / hooks / agent assets
- Codex-specific prompt templates used by scripts or installation flows

Do **not** treat this directory as a project-level slash command source equivalent to
`.claude/commands/` or `.opencode/commands/`. In this repository's current multi-CLI
workflow model, Codex project integration is primarily carried by `AGENTS.md`,
hooks, skills, and subagents.

### `commands/shell/`

Platform-agnostic shell scripts usable by any tool. Follow [shell-conventions.md](../scripts/shell-conventions.md).

---

## Deployment

Source assets in `commands/<tool>/` are deployed to the corresponding tool's command discovery directory:

| Source | Deploy Target | Method |
|--------|--------------|--------|
| `commands/claude/<id>/` | `.claude/commands/<namespace>/<name>.md` | Manual copy/adapt |
| `commands/codex/<id>/` | Codex CLI config / skills / helper assets | Manual |
| `commands/shell/<id>.sh` | Referenced directly | Symlink or copy |

The deployment format (slash command markdown, frontmatter, etc.) is tool-specific and documented by each tool, not by this spec.

---

## Quality Checklist

Before finalizing a new command source asset:

- [ ] Directory exists in `commands/<tool>/<command-id>/`
- [ ] README.md documents purpose, dependencies, usage, side effects
- [ ] Script has shebang, error handling, `--help` support
- [ ] Follows [shell-conventions.md](../scripts/shell-conventions.md) for shell scripts
- [ ] Has been deployed to target tool and verified working
- [ ] If the command orchestrates external reviewer CLIs (for example `multi-cli-review` / `multi-cli-review-action`), the source docs explicitly include:
  - reviewer task-dir root
  - review round number
  - at least two reviewer commands whose review description and `--review-focus` stay identical while only `--reviewer-id` differs
  - the matching aggregator command for the current CLI
  - the boundary that the coordinator creates the review directory and reviewers only write reports

---

## Anti-Patterns

- **No README**: Commands without documentation
- **Hardcoded paths**: Use environment variables or config, not absolute paths
- **Silent failures**: Always report status to stdout/stderr
- **Mixed tool concerns**: Don't put Claude-specific logic in `commands/shell/`
- **Unpaired reviewer handoff**: Commands that ask other CLIs to run reviewer work but fail to emit the matching `multi-cli-review-action` command for the current CLI
- **Divergent reviewer prompts**: Default reviewer command pairs that differ in review description or `--review-focus` when the only intended difference is `--reviewer-id`

## Platform Drift Status (as of 2026-05-04)

Source layer `commands/` is empty (only README.md files). Tool command directories contain live content. Drift inventory below classifies differences for the source-layer convergence task (`03-19-implement-commands-source`).

### Drift Classification

| Type | Meaning | Action |
|------|---------|--------|
| **none** | Content is identical across platforms | No action needed |
| **platform-param** | Only differs in platform-specific runtime parameter (e.g. `--platform claude` vs `--platform opencode`) | Reasonable; no action |
| **content-drift** | Instructional content differs (one platform has more/different guidance) | Source layer must converge to canonical version |
| **platform-only** | Command exists on one platform only, and is inherently platform-specific | Evaluate: keep as platform-only or generalize |
| **residual** | Empty or obsolete file left over from a previous change | Clean up |

### Commands

| Command | Claude | OpenCode | Drift Type | Details |
|---------|--------|----------|------------|---------|
| finish-work | ✓ | ✓ | none | Identical content |
| continue | ✓ | ✓ | platform-param | `--platform claude` vs `--platform opencode` |
| record-session | ✓ | ✓ | **retired** | Replaced by `finish-work` (which includes session recording via `record-session-helper.py`). Deployed files have been removed. |
| create-command | — | ✓ | **retired** | Low-usage, unshipped. Deployed file removed. |
| migrate-specs | — | ✓ | **residual** | 0-byte empty file. Should be deleted. |

### Skills (deployment asymmetry)

| Skill | Claude | OpenCode | Drift Type | Details |
|-------|--------|----------|------------|---------|
| trellis-check | ✓ | ✓ | none | Identical |
| trellis-before-dev | ✓ | ✓ | none | Identical |
| trellis-brainstorm | ✓ | ✓ | none | Identical |
| trellis-update-spec | ✓ | ✓ | none | Identical |
| trellis-break-loop | ✓ | ✓ | none | Identical |
| trellis-meta | ✓ | ✓ | none | Identical |
| workflow-audit | ✓ | — | **platform-only** | Claude-only. Has test fixtures. Evaluate cross-platform deployment. |
| workflow-capability-audit | ✓ | — | **platform-only** | Claude-only. Has test fixtures. Evaluate cross-platform deployment. |

### Notes for Source Layer Task

When `03-19-implement-commands-source` populates the source layer:
- `record-session` has been retired — its functionality is absorbed by `finish-work` (which calls `record-session-helper.py` internally). Deployed command files removed.
- `create-command` has been retired — low-usage, unshipped. Deployed file removed.
- `workflow-audit` and `workflow-capability-audit` should be evaluated for OpenCode/Codex deployment

---

**Language**: English

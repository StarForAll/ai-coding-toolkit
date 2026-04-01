# Command Asset Specification

> **⚠️ IMPORTANT**: This spec describes the TARGET architecture, not current practice.
> Current workflow: Edit directly in `.claude/commands/`、`.opencode/commands/`、`.iflow/commands/`
> To implement this architecture: populate `commands/<tool>/<id>/` source layer, then enable sync to tool directories

> How to author command source assets for multiple AI CLI tools.

---

## Current State

**Source asset directories** (`commands/claude/<id>/`、`commands/codex/<id>/`、`commands/shell/<id>/`) are empty — only top-level README files exist, no actual scripts.

**Tool command directories** (`.claude/commands/`、`.opencode/commands/`、`.iflow/commands/`) contain live commands,
but are **not synchronized** from `commands/<tool>/` source.
Current practice is **direct editing** in tool directories.

**To close the gap:** populate `commands/<tool>/<id>/` with real scripts, then apply the deployment mapping.

---

## Scope

This spec covers the **source asset layer**: `commands/claude/`, `commands/codex/`, `commands/shell/`.

**Out of scope:**
- `.claude/commands/`, `.opencode/commands/`, `.iflow/commands/` — these are each tool's internal command discovery directories, managed independently by each tool
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

---

## Anti-Patterns

- **No README**: Commands without documentation
- **Hardcoded paths**: Use environment variables or config, not absolute paths
- **Silent failures**: Always report status to stdout/stderr
- **Mixed tool concerns**: Don't put Claude-specific logic in `commands/shell/`

---

**Language**: English

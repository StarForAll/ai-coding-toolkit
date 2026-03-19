# Agent Asset Specification

> **⚠️ IMPORTANT**: This spec describes the TARGET architecture, not current practice.
> Current workflow: Edit directly in `.claude/agents/`、`.opencode/agents/`、`.iflow/agents/`
> To implement this architecture: populate `agents/<id>/` source layer, then enable sync to tool directories

> How to author agent source assets and deploy them across multiple AI CLI tools.

---

## Current State

**Source asset layer** (`agents/<agent-id>/`) is empty — no `SYSTEM.md`, `TOOLS.md`, or `EXAMPLES/` exist.

**Tool deployment directories** (`.claude/agents/`、`.opencode/agents/`、`.iflow/agents/`) exist
and contain live agent definitions, but are **not synchronized** from `agents/<id>/` source.
Current practice is **direct editing** in tool directories.

**To close the gap:** populate `agents/<id>/` with real source assets, then apply the Sync Strategy.

---

## Architecture: Source → Deploy

This project maintains agents at two layers:

```
源资产层 (Source of Truth)              工具部署层 (Tool-Specific Instances)
──────────────────────────              ────────────────────────────────────
agents/                                 .claude/agents/
  <agent-id>/                             <role>.md  (name, description, tools, model)
    README.md   ← 用途、场景、示例
    SYSTEM.md   ← 系统提示词（核心）      .opencode/agents/
    TOOLS.md    ← 权限边界（可选）          <role>.md  (description, mode, permission)
    EXAMPLES/   ← 示例（可选）
                                        .iflow/agents/
                                          <role>.md  (name, description, tools, color)
```

**Source of truth**: `agents/<agent-id>/` directory.
**Tool deployments**: `.claude/agents/`, `.opencode/agents/`, `.iflow/agents/` are derived instances.

---

## Source Asset Structure

```
agents/
  <agent-id>/
    README.md        # 用途、适用场景、调用方式、示例（必需）
    SYSTEM.md        # 系统提示词：角色、职责、边界、工作流、输出格式（必需）
    TOOLS.md         # 抽象权限需求：read/write/edit/bash/glob/grep（可选）
    EXAMPLES/        # 输入输出示例（可选）
      input-1.md
      output-1.md
```

### README.md (Required)

Must include:
- **Purpose**: What problem this agent solves
- **When to Use**: Trigger conditions / invocation scenarios
- **Input**: What the agent expects
- **Output**: What the agent produces
- **Tool Compatibility**: Which tools this agent is deployed to

### SYSTEM.md (Required)

The core content, must be **tool-agnostic**. Contains:
- Agent role and expertise
- Core responsibilities (numbered list)
- Strict boundaries (what NOT to do)
- Workflow steps (numbered)
- Report format (markdown template)
- Context self-loading instructions

**Rules:**
- Do NOT embed tool-specific syntax (no `Task(subagent_type:...)`, no frontmatter)
- Do NOT reference specific tool paths (use generic paths like `.trellis/`)
- Keep it self-contained — a tool adapter should only need to wrap it in frontmatter

### TOOLS.md (Optional)

Describe abstract permission needs:
```markdown
## Required Permissions
- read: YES — must read source files and specs
- write: YES — must create/modify files
- edit: YES — must edit existing files
- bash: YES — must run lint/test commands
- glob: YES — must search files by pattern
- grep: YES — must search file contents

## Forbidden Operations
- git commit, git push, git merge
- rm -rf (bulk deletion)
```

---

## Writing Principles

1. **Tool-agnostic first**: SYSTEM.md is the single source of truth for agent behavior
2. **Role-based naming**: `feature-planner`, `bug-fixer`, `code-reviewer` (kebab-case)
3. **Single responsibility**: One agent = one role. Split complex workflows into sub-agents
4. **Explicit boundaries**: Always define what the agent must NOT do
5. **Structured output**: Define a report format so the caller knows what to expect

---

## Multi-Tool Deployment Mapping

Each tool requires a single `.md` file in its agents directory, wrapping the source content in tool-specific frontmatter.

### Field Mapping

| Source Field | Claude Code | OpenCode | iFlow |
|-------------|-------------|----------|-------|
| **Directory** | `.claude/agents/` | `.opencode/agents/` | `.iflow/agents/` |
| **Filename** | `<role>.md` | `<role>.md` | `<role>.md` |
| **Agent name** | `name:` in frontmatter | Inferred from filename | `name:` in frontmatter |
| **Description** | `description:` | `description:` (use `\|` block) | `description:` |
| **Permissions** | `tools:` list (e.g. `Read, Write, Bash`) | `permission:` block (`read: allow`) | `tools:` list + `color:` |
| **Model** | `model:` (optional) | Not supported | Not supported |
| **Mode** | Implicit (subagent) | `mode: subagent` (required) | Implicit (subagent) |
| **Body** | SYSTEM.md content | SYSTEM.md content | SYSTEM.md content |

### Example: Deploying `research` Agent

**Source**: `agents/research/SYSTEM.md`

**Claude Code** (`.claude/agents/research.md`):
```markdown
---
name: research
description: |
  Code and tech search expert. Pure research, no code modifications.
tools: [Read, Grep, Glob, Task]
model: opus
---
<SYSTEM.md content>
```

**OpenCode** (`.opencode/agents/research.md`):
```markdown
---
description: |
  Code and tech search expert. Pure research, no code modifications.
mode: subagent
permission:
  read: allow
  grep: allow
  glob: allow
---
<SYSTEM.md content>
```

**iFlow** (`.iflow/agents/research.md`):
```markdown
---
name: research
description: |
  Code and tech search expert. Pure research, no code modifications.
tools: [Read, Grep, Glob]
color: blue
---
<SYSTEM.md content>
```

---

## Sync Strategy

| Change Type | Action |
|------------|--------|
| Modify SYSTEM.md body | Update ALL tool deployment files |
| Modify TOOLS.md | Update permission fields in ALL tool deployment files |
| Modify README.md description | Update `description:` in ALL tool deployment files |
| Add new agent | Create `agents/<id>/` + create deployment file in each tool |
| Deprecate agent | Mark in README.md + remove from all tool deployments |
| Tool-specific frontmatter change | Only update that tool's deployment file |

### Recommended Sync Workflow

```bash
# After modifying agents/<id>/SYSTEM.md:
# 1. Update .claude/agents/<role>.md (keep frontmatter, replace body)
# 2. Update .opencode/agents/<role>.md (keep frontmatter, replace body)
# 3. Update .iflow/agents/<role>.md (keep frontmatter, replace body)
```

---

## Root `agents/` Directory

The `agents/` directory at the project root IS the source asset layer. It is NOT a scaffold or documentation-only directory. All agent definitions should be authored here first, then deployed to tool-specific directories.

---

## Quality Checklist

Before finalizing a new agent:

- [ ] `agents/<agent-id>/README.md` exists with purpose, triggers, I/O
- [ ] `agents/<agent-id>/SYSTEM.md` exists and is tool-agnostic
- [ ] SYSTEM.md has: responsibilities, boundaries, workflow, report format
- [ ] Deployed to `.claude/agents/` with correct frontmatter
- [ ] Deployed to `.opencode/agents/` with correct frontmatter
- [ ] Deployed to `.iflow/agents/` with correct frontmatter
- [ ] Permissions are minimal for each tool

---

## Anti-Patterns

- **Tool-specific content in SYSTEM.md**: Embedding `Task(subagent_type:...)` or frontmatter in the source
- **Skipping source layer**: Writing directly in `.opencode/agents/` without `agents/<id>/` source
- **Asymmetric deployments**: Different behavior across tools because sync was missed
- **Overly generic prompts**: "You are a helpful assistant"
- **Missing boundaries**: No constraints on dangerous operations

---

**Language**: English

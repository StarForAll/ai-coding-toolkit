# Agent Asset Specification

> **⚠️ IMPORTANT**: This spec describes the TARGET architecture, not current practice.
> Current workflow: Edit directly in live deployment directories such as `.claude/agents/`、`.opencode/agents/`、`.codex/agents/`，and currently also `.kiro/agents/` / `.qoder/agents/`
> To implement this architecture: populate `agents/<id>/` source layer, then enable sync to tool directories

> How to author agent source assets and deploy them across multiple AI CLI tools.

---

## Current State

**Source asset layer** (`agents/<agent-id>/`) is empty — no `SYSTEM.md`, `TOOLS.md`, or `EXAMPLES/` exist.

**Tool deployment directories** (`.claude/agents/`、`.opencode/agents/`、`.codex/agents/`) exist
and contain live agent definitions, but are **not synchronized** from `agents/<id>/` source.
Current practice is **direct editing** in tool directories.

Additional live deployment surfaces also exist in this repository today, notably
`.kiro/agents/` and `.qoder/agents/`. They are part of the current maintenance
surface even though the initial source-layer design in this spec still centers
on Claude / OpenCode / Codex.

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
                                        .codex/agents/
                                          <role>.toml  (name, description, sandbox)
```

**Source of truth**: `agents/<agent-id>/` directory.
**Tool deployments**: `.claude/agents/`, `.opencode/agents/`, `.codex/agents/` are derived instances.

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

**Rules:**
- Do NOT embed tool-specific syntax (no `Task(subagent_type:...)`, no frontmatter)
- Do NOT reference specific tool paths (use generic paths like `.trellis/`)
- Keep it self-contained for shared role semantics; deployment adapters may still
  add platform-specific metadata or context-loading glue

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

Each deployment target requires one tool-specific agent file that wraps the
shared source content in that platform's metadata format.

The mapping table below focuses on the current primary convergence targets
Claude / OpenCode / Codex. This repository also carries live Kiro / Qoder agent
deployments, but they remain outside the not-yet-implemented `agents/<id>/`
source sync path.

### Field Mapping

| Source Field | Claude Code | OpenCode | Codex |
|-------------|-------------|----------|-------|
| **Directory** | `.claude/agents/` | `.opencode/agents/` | `.codex/agents/` |
| **Filename** | `<role>.md` | `<role>.md` | `<role>.toml` |
| **Agent name** | `name:` in frontmatter | Inferred from filename | `name =` |
| **Description** | `description:` | `description:` (use `\|` block) | `description =` |
| **Permissions** | `tools:` list (e.g. `Read, Write, Bash`) | `permission:` block (`read: allow`) | `sandbox_mode =` + developer instructions |
| **Model** | `model:` (optional) | Not supported | Not supported |
| **Mode** | Implicit (subagent) | `mode: subagent` (required) | Implicit |
| **Body** | SYSTEM.md content | SYSTEM.md content | `developer_instructions` string |

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

**Codex** (`.codex/agents/research.toml`):
```toml
name = "research"
description = "Code and tech search expert. Pure research, no code modifications."
sandbox_mode = "read-only"

developer_instructions = """
<SYSTEM.md content>
"""
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
# 3. Update .codex/agents/<role>.toml (keep metadata, replace instructions)
```

---

## Root `agents/` Directory

The `agents/` directory at the project root is the **intended** source asset
layer for this target architecture. In the current repo state it is still a
scaffold / documentation-only directory containing only `agents/README.md`;
live agent definitions remain under tool-specific deployment directories until
`03-19-implement-agents-source` is completed.

---

## Quality Checklist

Before finalizing a new agent:

- [ ] `agents/<agent-id>/README.md` exists with purpose, triggers, I/O
- [ ] `agents/<agent-id>/SYSTEM.md` exists and is tool-agnostic
- [ ] SYSTEM.md has: responsibilities, boundaries, workflow, report format
- [ ] Deployed to `.claude/agents/` with correct frontmatter
- [ ] Deployed to `.opencode/agents/` with correct frontmatter
- [ ] Deployed to `.codex/agents/` with correct metadata
- [ ] Permissions are minimal for each tool

---

## Anti-Patterns

- **Tool-specific content in SYSTEM.md**: Embedding `Task(subagent_type:...)` or frontmatter in the source
- **Skipping source layer**: Writing directly in `.opencode/agents/` without `agents/<id>/` source
- **Asymmetric deployments**: Different behavior across tools because sync was missed
- **Overly generic prompts**: "You are a helpful assistant"
- **Missing boundaries**: No constraints on dangerous operations

## Platform Drift Status (as of 2026-05-04)

Source layer `agents/` is empty. All three tool deployments are independently maintained. Drift inventory below classifies differences for the source-layer convergence task (`03-19-implement-agents-source`).

### Drift Classification

| Type | Meaning | Action |
|------|---------|--------|
| **format-only** | Different serialization wrapper / frontmatter; core instructions identical or equivalent | Source layer will unify core body; platform adapters keep format |
| **context-adapter** | Same core role, but one platform needs hook-push context while another must self-load task / JSONL context | Keep shared role semantics; isolate loading instructions in deployment adapters |
| **content-drift** | Core instruction body differs across platforms (responsibilities, boundaries, workflow steps) | Source layer must converge to single canonical version |
| **platform-only** | Feature exists on one platform only and is inherently platform-specific | No cross-platform action needed |

### Agents

| Agent | Claude | OpenCode | Codex | Drift Type | Details |
|-------|--------|----------|-------|------------|---------|
| trellis-implement | ✓ | ✓ | ✓ | context-adapter | Claude relies on hook-injected context. OpenCode and Codex include self-loading context instructions because their current integration model is not identical to Claude's hook push. |
| trellis-check | ✓ | ✓ | ✓ | context-adapter | Same pattern as trellis-implement. Hook model differs, but the review role itself is aligned. |
| trellis-research | ✓ | ✓ | ✓ | format-only | Main difference is wrapper/permission syntax plus small platform path examples; no evidence of a different research role. |

### Additional Live Platforms

The current repository also carries live `trellis-*` agents in:

- `.kiro/agents/`
- `.qoder/agents/`

These follow the same broad split:

- hook-push / spawn-hook capable platforms can keep thinner agent bodies
- platforms without equivalent sub-agent injection must self-load task context

Treat those surfaces as part of the same convergence problem even though the
current source-layer mapping table above still focuses on Claude / OpenCode /
Codex.

### Current Assessment

No **critical role-drift** is currently confirmed across deployed agents.
However, the live differences are not purely frontmatter-only:

- some are **context-adapter** differences caused by platform hook capability
- direct per-platform maintenance still creates a **future content-drift risk**

So the right conclusion is:

- current differences are mostly reasonable platform adaptations
- current spec should not overstate them as pure `format-only`
- source-layer convergence is still needed to prevent future drift

### Notes for Source Layer Task

When `03-19-implement-agents-source` populates `agents/<id>/SYSTEM.md`:
- The SYSTEM.md body should capture the **shared core** (responsibilities, boundaries, workflow, report format)
- Platform-specific context-loading instructions should go in each platform's deployment adapter, not in SYSTEM.md
- The self-loading context section (currently seen in OpenCode / Codex / Qoder-style deployments) should be extracted to a platform adapter pattern where possible

---

**Language**: English

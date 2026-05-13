# Agent Asset Specification

> **⚠️ IMPORTANT**: This spec describes the TARGET architecture, not current practice.
> Current workflow: Edit directly in live deployment directories such as `.claude/agents/`、`.opencode/agents/`、`.codex/agents/`，and currently also `.kiro/agents/` / `.qoder/agents/`
> To implement this architecture: populate `agents/<id>/` source layer, then enable sync to tool directories

> How to author agent source assets and deploy them across multiple AI CLI tools.

---

## Current State

**Source asset layer** (`agents/<agent-id>/`) is now partially populated. The repository currently has at least one real source asset (`agents/self-media-content-expert/`), but the source layer is still incomplete and not yet the live synchronization source for all deployed agents.

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
    DEPLOYMENT.md    # 目标平台 wrapper 生成与验证说明（推荐）
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
- **Deployment Pointer**: If deployment guidance lives in `DEPLOYMENT.md`, README should point to it clearly

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
| **Permissions** | `tools:` list or richer frontmatter capability controls | `permission:` block (`read: allow`) | `sandbox_mode =` + developer instructions |
| **Model** | `model:` (optional) | Not supported | Not supported |
| **Mode** | Implicit (subagent) | `mode: subagent` (required) | Implicit |
| **Body** | SYSTEM.md content | SYSTEM.md content | `developer_instructions` string |

### Official-doc drift notes (verified 2026-05-13)

- **Claude Code**: project-scoped subagents still live under `.claude/agents/` as Markdown files, but the official docs now expose a broader frontmatter surface than this source-layer spec currently models, including optional fields such as `color`, `permissionMode`, `mcpServers`, `hooks`, `skills`, `memory`, `effort`, `background`, and `isolation`. For source-layer work in this repo, keep `SYSTEM.md` tool-agnostic and treat those as deployment-wrapper concerns unless a task explicitly needs them.
- **OpenCode**: official docs now prefer the `permission` field over the legacy `tools` boolean/object config. When authoring or updating OpenCode deployment wrappers, use `permission` as the default unless maintaining backward compatibility with an older deployment.
- **Codex**: official docs confirm the required custom-agent fields are `name`, `description`, and `developer_instructions`; `sandbox_mode`, `model`, `model_reasoning_effort`, `mcp_servers`, and `skills.config` remain optional wrapper-level additions.

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
layer for this target architecture. In the current repo state it is no longer
documentation-only: it now contains source assets such as
`agents/self-media-content-expert/`. However, live agent definitions still
primarily remain under tool-specific deployment directories until
`03-19-implement-agents-source` is completed.

---

## Quality Checklist

Before finalizing a new agent source asset:

- [ ] `agents/<agent-id>/README.md` exists with purpose, triggers, I/O
- [ ] `agents/<agent-id>/SYSTEM.md` exists and is tool-agnostic
- [ ] SYSTEM.md has: responsibilities, boundaries, workflow, report format
- [ ] If cross-platform deployment is part of the design, `DEPLOYMENT.md` exists or equivalent deployment guidance is clearly documented
- [ ] Deployment wrappers are either created or explicitly documented as out of scope for this task
- [ ] Permissions are minimal for each tool

---

## Anti-Patterns

- **Tool-specific content in SYSTEM.md**: Embedding `Task(subagent_type:...)` or frontmatter in the source
- **Skipping source layer**: Writing directly in `.opencode/agents/` without `agents/<id>/` source
- **Asymmetric deployments**: Different behavior across tools because sync was missed
- **Overly generic prompts**: "You are a helpful assistant"
- **Missing boundaries**: No constraints on dangerous operations

## Platform Drift Status (as of 2026-05-04)

Source layer `agents/` is partially populated, but all three primary tool deployments are still independently maintained. Drift inventory below classifies differences for the source-layer convergence task (`03-19-implement-agents-source`).

### Drift Classification

| Type | Meaning | Action |
|------|---------|--------|
| **format-only** | Different serialization wrapper / frontmatter; core instructions identical or equivalent | Source layer will unify core body; platform adapters keep format |
| **context-adapter** | Same core role, but one platform needs hook-push context while another must self-load task / JSONL context | Keep shared role semantics; isolate loading instructions in deployment adapters |
| **content-drift** | Core instruction body differs across platforms (responsibilities, boundaries, workflow steps) | Source layer must converge to single canonical version |
| **capability-enhancement** | Tool set expanded on some platforms (new MCP tools added) without changing core role/boundaries/workflow | Document in Tool Capability Matrix; platforms without MCP support keep existing tool set |
| **platform-only** | Feature exists on one platform only and is inherently platform-specific | No cross-platform action needed |

### Agents

| Agent | Claude | OpenCode | Codex | Drift Type | Details |
|-------|--------|----------|-------|------------|---------|
| trellis-implement | ✓ | ✓ | ✓ | context-adapter | Claude relies on hook-injected context. OpenCode and Codex include self-loading context instructions because their current integration model is not identical to Claude's hook push. |
| trellis-check | ✓ | ✓ | ✓ | context-adapter | Same pattern as trellis-implement. Hook model differs, but the review role itself is aligned. |
| trellis-research | ✓ | ✓ | ✓ | context-adapter + capability-enhancement | Hook-push platforms can keep a thinner research body, while class-2 pull-loaded deployments such as Codex and Qoder self-load the active task path from the dispatch prompt or `task.py current --source` before writing `{TASK_DIR}/research/`. **Tool capability enhanced 2026-05-06**: Claude/Qoder/OpenCode gained ace.search_context, exa.web_fetch, Context7, deepwiki, grok-search, exa.web_search_advanced; Codex/Kiro unchanged (platform model不支持 named MCP tool declarations). |

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

### Context-Adapter Audit (2026-05-06)

Verified by comparing deployed agents against Trellis 0.5.0-rc.5 native templates
(`@mindfoldhq/trellis/dist/templates/{platform}/agents/`). Supporting evidence:
- CLI boundary matrix: `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` §"当前真实边界"
- Capability audit: `.trellis/tasks/archive/2026-05/05-06-workflow-capability-audit/capability-report.md`
- Per-file diff results available on request via `diff` against the template paths above

| Platform | Match Native? | Context-Loading Mechanism |
|----------|--------------|--------------------------|
| Claude Code (`.claude/agents/`) | **Identical** | PreToolUse hook (`inject-subagent-context.py`) auto-injects full task context before spawn for implement/check; research agent still self-loads task path (`task.py current --source`) because its scope (pure search + persist) does not need the full JSONL/spec injection the hook provides |
| OpenCode (`.opencode/agents/`) | **Identical** | Trellis native template already includes Context Self-Loading section (OpenCode has no PreToolUse hook) |
| Codex (`.codex/agents/`) | **Differs** | Repo agents have extra context self-loading instructions not present in native template; Codex only has SessionStart + UserPromptSubmit hooks, no PreToolUse — self-loading is the primary mechanism for sub-agents to receive reliable task context |

**Conclusion**: All three platforms are using native Trellis agents or equivalent
functionality. The Codex context self-loading additions are valid and necessary
(`context-adapter` drift type), not overlay residuals.

**Removing** the self-loading from Codex agents would lose the reliable
context-loading path (JSONL/spec resolution, `implement.jsonl`/`check.jsonl`
iteration). Codex agents can still discover the task path from the dispatch
prompt or `task.py current --source`, but without self-loading they would miss
the structured spec context that the hook provides on Claude and the
self-loading section provides on Codex/OpenCode today.

**Convergence path**: When Trellis upstream adds context self-loading to the
Codex native templates (aligning with the OpenCode template pattern), re-run
`trellis init --claude --codex --opencode` or manually sync `.codex/agents/`
to the updated native templates. Until then, the current Codex agent files
should be preserved as-is and not overwritten by the simpler native templates.

### Tool Capability Enhancement (2026-05-06)

trellis-research originally deployed with basic internal search (Glob/Grep/Read) + 2 exa tools.
Enhanced on 2026-05-06 to cover the project MCP routing matrix's primary search scenarios.

**Enhancement type**: `capability-enhancement` — extends available search channels
without changing the core role, boundaries, or workflow structure.

#### Enhanced Tool Matrix

| Priority | Tool | Purpose | Claude | Qoder | OpenCode | Codex | Kiro |
|----------|------|---------|--------|-------|----------|-------|------|
| P0 | mcp__ace__search_context | Internal semantic search | ✓ | ✓ | ✓ | ✗ | ✗ |
| P0 | mcp__exa__web_fetch_exa | Full-page read after search | ✓ | ✓ | ✓ | ✗ | ✗¹ |
| P1 | mcp__Context7__resolve-library-id | Library docs (resolve) | ✓ | ✓ | ✓ | ✗ | ✗ |
| P1 | mcp__Context7__query-docs | Library docs (query) | ✓ | ✓ | ✓ | ✗ | ✗ |
| P2 | mcp__deepwiki__* (3 tools) | GitHub repo research | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__exa__web_search_advanced_exa | Advanced search | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__grok-search__web_search | Real-time / latest info (primary); general web (fallback) | ✓ | ✓ | ✓ | ✗ | ✗ |
| P3 | mcp__grok-search__web_fetch | Real-time / latest info (primary); general web (fallback) | ✓ | ✓ | ✓ | ✗ | ✗ |

¹ Kiro uses generic `web_fetch` which is functionally equivalent to `mcp__exa__web_fetch_exa`
but is not an MCP-specific tool declaration.

**Cross-platform notes:**
- Claude / Qoder / OpenCode: full enhancement with all MCP tools
- Codex: sandbox model doesn't support named MCP tool declarations; main agent coordinates external searches
- Kiro: generic tool names (`web_search`/`web_fetch`) cover basic web capability; no MCP-specific tools

**Search routing rule (agent body ↔ project MCP routing matrix alignment):**

The agent's Step 3 routing table must follow the same priority order as the project's
global MCP routing matrix (`rules/03-mcp-routing-matrix.md`):

| Search Type | Primary | Fallback | Rationale |
|-------------|---------|----------|-----------|
| Internal code | ace.search_context | Glob + Grep + Read | Semantic > keyword for code intent |
| Library docs | Context7 | exa | First-party docs > general web |
| GitHub repos | deepwiki | exa | Structured repo knowledge > raw search |
| **Real-time / latest info** | **grok-search** | **exa** | **grok-search has lower latency for current events, version updates, and time-sensitive facts** |
| General web (non-time-sensitive) | exa | grok-search | exa has better content quality for static/evergreen topics |
| Advanced / deep research | exa.web_search_advanced | grok-search | exa supports date/domain/text filters and deep-reasoning mode |

Key alignment rule: **Real-time / latest info queries MUST use grok-search as primary,
not exa.** This mirrors the project routing matrix's "Real-time information retrieval:
grok-search → exa" rule and prevents the sub-agent from defaulting to exa for
time-sensitive queries where grok-search is the designated first choice.

**Body changes on enhanced platforms:**
- Core Responsibilities lines 1-2 updated to reference new primary tools with fallback chains
- Workflow Step 3 expanded from single-line to a tool routing table with 6 search types:
  - Internal code: ace.search_context → Glob/Grep/Read
  - Library docs: Context7 → exa fallback
  - GitHub repos: deepwiki → exa fallback
  - **Real-time / latest info: grok-search → exa fallback** (aligns with project MCP routing matrix rule that latest-information queries prefer grok-search)
  - General web (non-time-sensitive): exa → grok-search fallback
  - Advanced / deep research: exa.web_search_advanced → grok-search fallback

### Notes for Source Layer Task

When `03-19-implement-agents-source` populates `agents/<id>/SYSTEM.md`:
- The SYSTEM.md body should capture the **shared core** (responsibilities, boundaries, workflow, report format)
- Platform-specific context-loading instructions should go in each platform's deployment adapter, not in SYSTEM.md
- The self-loading context section (currently seen in OpenCode / Codex / Qoder-style deployments) should be extracted to a platform adapter pattern where possible
- For Codex specifically: the deployment adapter MUST include context self-loading unless Trellis upstream adds it to native templates first

---

**Language**: English

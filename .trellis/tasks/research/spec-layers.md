# Research: Trellis Spec Layers

- **Query**: Spec directory structure, layer organization, universal domains, spec index, how specs reach agents
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.trellis/spec/index.md` | Master spec index (180 lines) |
| `.claude/skills/trellis-before-dev/SKILL.md` | Skill that discovers and injects specs (35 lines) |
| `.claude/skills/trellis-update-spec/SKILL.md` | Skill that captures contracts into specs (357 lines) |
| `.trellis/scripts/common/task_context.py` | JSONL context management for adding spec paths |

### Spec Directory Structure

From `spec/index.md`:
- **Meta-project definition**: AI coding toolkit maintaining reusable source assets and workflow assets
- **3 groups**: Repo Maintenance Specs, Workflow Method Specs, Supporting Workflow Assets
- **7 spec layers**:
  1. `library-assets` — Reusable framework/library documentation
  2. `scripts` — Automation scripts and their contracts
  3. `agents` — Agent definitions and behavior contracts
  4. `commands` — CLI command specifications
  5. `skills` — Skill definitions and routing rules
  6. `docs` — Documentation standards
  7. `platforms` — Platform-specific configurations

- **6 universal domains**:
  1. `ai-execution` — AI agent execution patterns
  2. `context-engineering` — Context loading and injection
  3. `agent-collaboration` — Multi-agent coordination
  4. `verification` — Testing and quality assurance
  5. `project-governance` — Project management and workflow
  6. `product-and-requirements` — Requirements and PRD

### How Specs Reach Agents

**Path 1 — JSONL Injection (sub-agent mode)**:
1. During Phase 1.3 (Research), the AI agent adds relevant spec paths to `implement.jsonl` / `check.jsonl`
2. The hook reads JSONL entries and injects file content into sub-agent prompts
3. Sub-agents receive curated spec content automatically

**Path 2 — Skill Loading (inline mode)**:
1. `trellis-before-dev` skill is loaded during Phase 2.1
2. Skill steps: discover packages -> identify applicable specs -> read spec index -> read guideline files -> read shared guides -> understand standards
3. Specs are loaded directly into the main session's context

**Path 3 — Breadcrumb Injection (all modes)**:
1. The per-turn breadcrumb may include spec references
2. `inject-workflow-state.py` can include spec-related instructions in the breadcrumb body

### Spec Update Mechanism

From `trellis-update-spec/SKILL.md`:
- **Code-spec vs Guide distinction**:
  - Specs = "how to implement" (executable contracts, must be followed)
  - Guides = "what to consider" (reference material, informational)
- **Mandatory 7-section template** for infrastructure/cross-layer work
- **Update types**: Design Decision, Project Convention, New Pattern, Forbidden Pattern, Common Mistake, Gotcha
- Specs are captured during Phase 3.1 (Update Specs)

### Code Patterns

- `task_context.py:cmd_add_context()` is the programmatic way to add spec paths to JSONL
- Spec files follow a naming convention under `.trellis/spec/<package>/<layer>/`
- The `trellis-before-dev` skill discovers specs by first reading the spec index, then reading individual spec files

### Connections

- Specs are the knowledge base that flows through JSONL to sub-agents
- Spec updates are triggered during Phase 3 (Finish) via the `trellis-update-spec` skill
- The spec index is read during Phase 1.1 (Auto-Context) to identify applicable specs
- Spec paths stored in JSONL connect the spec layer to the hook injection system
- Universal domains provide cross-cutting categorization that helps agents find relevant specs

## Caveats / Not Found

- Individual spec files under `.trellis/spec/` were not enumerated in detail
- The exact spec file format (sections, frontmatter) was not inspected beyond what update-spec skill describes
- The interaction between spec layers and universal domains (how they cross-reference) was not fully traced

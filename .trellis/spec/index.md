# Project Specifications

> Live development and workflow-authoring guidance for the ai-coding-toolkit project.

---

## Project Nature

This is a **meta-project** — an AI coding toolkit that maintains both reusable source assets and workflow assets. It does not contain a runnable application. Its deliverables are:

- **Markdown** specs, templates, checklists, examples
- **YAML** configuration (`manifest.yaml`, schemas)
- **Python** automation scripts (`cli.py`, validation, assembly, sync)
- **Shell** validation scripts
- **SKILL.md** skill definitions (YAML frontmatter + markdown)
- **Agent** source assets (`agents/<id>/`) deployed to `.claude/agents/`, `.opencode/agents/`, `.iflow/agents/`
- **Command** source assets (`commands/<tool>/`) deployed to tool-specific command directories
- **Workflow assets** under `docs/workflows/**`, including command source files, installers, and workflow conventions

`.trellis/spec/` is the live spec workspace for this repository. It is narrower
than `trellis-library/` as a source library, but wider than a pure
"repo-maintenance only" directory:

1. It keeps **repo-local maintenance specs** for this repository's live assets
2. It keeps **workflow-method specs** that this repository actively uses when authoring `docs/workflows/**`
3. It keeps **supporting imported assets** (templates, checklists, examples, platform-oriented references) when they directly support the repository's workflow outputs

---

## Specification Index

### Group 1: Repo Maintenance Specs

| Spec Layer | Path | Status | Purpose |
|-----------|------|--------|---------|
| [library-assets](./library-assets/index.md) | `.trellis/spec/library-assets/` | ✅ Implemented | How to author specs, templates, checklists for `trellis-library` |
| [scripts](./scripts/index.md) | `.trellis/spec/scripts/` | ✅ Implemented | Python and Shell script conventions |
| [agents](./agents/index.md) | `.trellis/spec/agents/` | ⚠️ Design | Agent source-layer guidance while live edits still happen in tool directories |
| [commands](./commands/index.md) | `.trellis/spec/commands/` | ⚠️ Design | Command source-layer guidance while live edits still happen in tool directories |
| [skills](./skills/index.md) | `.trellis/spec/skills/` | ✅ Implemented | How to define installable skills in `skills/` |
| [docs](./docs/index.md) | `.trellis/spec/docs/` | ✅ Implemented | Repository documentation conventions |

> **Status Legend**:
> - ✅ **Implemented**: source asset layer is populated, spec reflects live practice
> - ⚠️ **Design**: source asset layer is incomplete, current practice still relies on direct editing in tool directories

### Group 2: Workflow Method Specs

These concerns are appropriate here because this repository authors and validates
AI workflow assets under `docs/workflows/**`.

| Workflow Spec Area | Path | Why It Belongs Here |
|-------------------|------|---------------------|
| AI execution rules | `.trellis/spec/universal-domains/ai-execution/` | Governs tool use, prompt boundaries, output structure, and model fallback in workflow design |
| Context engineering | `.trellis/spec/universal-domains/context-engineering/` | Governs context injection, summary strategy, contamination control, and long-session workflow behavior |
| Agent collaboration | `.trellis/spec/universal-domains/agent-collaboration/` | Governs delegation, handoff, and multi-agent workflow boundaries |
| Verification | `.trellis/spec/universal-domains/verification/` | Governs evidence, validation gates, definition of done, and release/readiness expectations |
| Project governance | `.trellis/spec/universal-domains/project-governance/` | Governs change records, risk handling, and library sync rules used by this repo |
| Product and requirements | `.trellis/spec/universal-domains/product-and-requirements/` | Governs requirement discovery and PRD shaping used by workflow assets in `docs/workflows/**` |
| CLI command interface | `.trellis/spec/platforms/cli/command-interface/` | Governs CLI-oriented command contracts used by workflow command assets |

Current fit review:

- Most workflow-method concerns are still strongly aligned with this repository's role even if explicit citations are uneven
- The latest pruning sweep removed the previously weak-fit concerns from the live workspace
- The generic PRD wrapper concern has also been removed from the live workspace
- See [Workflow Spec Fit Assessment](./workflow-spec-fit-assessment.md) before pruning reusable concerns from the live project spec workspace

### Group 3: Supporting Workflow Assets

These are not the primary repo-maintenance rules, but they remain appropriate in
`.trellis/spec/` when they directly support the repository's workflow outputs.

| Asset Type | Path | Typical Use |
|-----------|------|-------------|
| Templates | `.trellis/spec/templates/` | Workflow-authored PRDs, handoff artifacts, acceptance criteria, readiness docs |
| Checklists | `.trellis/spec/checklists/` | Workflow gates, readiness checks, handoff quality, context health |
| Examples | `.trellis/spec/examples/` | Example PRDs and workflow-support artifacts |

Current support-layer status:

- Direct workflow dependencies are concentrated in the `product-and-requirements` template/checklist set
- Product-and-requirements examples currently serve as indirect support material
- Other templates/checklists remain present as domain-fitting assets, but are not yet explicitly routed by current workflow docs
- See [Workflow Support Inventory](./workflow-support-inventory.md) before deciding whether to keep, clarify, or remove a support asset

### Repo-Specific Thinking Guides

| Guide | Path |
|-------|------|
| [Thinking Guides](./guides/index.md) | `.trellis/spec/guides/` |
| [Code Reuse Thinking](./guides/code-reuse-thinking-guide.md) | Pattern identification |
| [Cross-Layer Thinking](./guides/cross-layer-thinking-guide.md) | Repo boundary and drift prevention |

### Scope Boundary

`.trellis/spec/` is the live spec workspace for this project.

Keep only guidance that directly helps author, validate, or maintain the live
assets this repository owns:

- `trellis-library/` source assets and `manifest.yaml`
- `.trellis/scripts/` and repository automation
- `agents/`, `commands/`, `skills/`, `docs/`
- `docs/workflows/**` workflow assets and their command/install flows
- repo-specific thinking guides for sync, reuse, and drift prevention
- supporting templates, checklists, and examples that those workflow assets actively depend on

Do not treat this directory as a full mirror of `trellis-library/`.
Only keep the subset of reusable concerns that this repository actually uses as
live workflow-authoring inputs.

---

## Quick Start by Task Type

| Task | Must-Read Specs |
|------|----------------|
| Author a new spec in `trellis-library` | `library-assets/spec-authoring.md` |
| Author a new template | `library-assets/template-authoring.md` |
| Author a new checklist | `library-assets/checklist-authoring.md` |
| Update `manifest.yaml` | `library-assets/manifest-maintenance.md` |
| Write/modify Python scripts | `scripts/python-conventions.md` |
| Modify workflow installer / upgrade scripts in `docs/workflows/**/commands/` | `scripts/index.md` + `scripts/workflow-installer-upgrade-contracts.md` |
| Write/modify Shell scripts | `scripts/shell-conventions.md` |
| Define an agent (source + deploy) | `agents/index.md` |
| Define a command (source + deploy) | `commands/index.md` |
| Define a skill | `skills/index.md` |
| Design or update workflow docs in `docs/workflows/**` | `docs/index.md` + relevant `universal-domains/**` concerns |
| Any repo-maintenance task | `guides/index.md` |

---

## Pre-Development Checklist

Before writing ANY code or content:

1. [ ] Identify which spec layers apply to your task
2. [ ] Decide whether your task is primarily repo maintenance, workflow authoring, or both
3. [ ] Read the relevant index files
4. [ ] Read the specific guideline files listed in each index
5. [ ] If writing workflow assets, read the relevant `universal-domains/**` concern files and any needed template/checklist assets
6. [ ] Read `guides/index.md` for repo-specific thinking supplements
7. [ ] If modifying `trellis-library` assets, also read `library-assets/manifest-maintenance.md`

---

## Validation Commands

```bash
# Validate trellis-library manifest and asset sync
python3 trellis-library/cli.py validate --strict-warnings

# Validate skills structure
./scripts/validate-skills.sh
```

---

## Meta-Project Note

This project has no traditional frontend/backend app layers. Do not create
`frontend/` or `backend/` spec directories here. All development falls into:

1. **Asset authoring** (specs, templates, checklists, examples) → see `library-assets/`
2. **Script development** (Python, Shell) → see `scripts/`
3. **Agent assets** (source definitions in `agents/` → deployed to tool directories) → see `agents/`
4. **Command assets** (source in `commands/` → deployed to tool directories) → see `commands/`
5. **Skill definitions** → see `skills/`
6. **Workflow assets** (`docs/workflows/**`, workflow commands, installers, upgrade flows) → see `docs/` + relevant `universal-domains/**`
7. **Documentation** → see `docs/`

---

**Language**: English

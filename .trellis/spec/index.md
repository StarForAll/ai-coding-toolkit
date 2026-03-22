# Project Specifications

> Development guidelines for the ai-coding-toolkit project.

---

## Project Nature

This is a **meta-project** — a "specs-as-code" asset library. It does not contain a runnable application. Its deliverables are:

- **Markdown** specs, templates, checklists, examples
- **YAML** configuration (`manifest.yaml`, schemas)
- **Python** automation scripts (`cli.py`, validation, assembly, sync)
- **Shell** validation scripts
- **SKILL.md** skill definitions (YAML frontmatter + markdown)
- **Agent** source assets (`agents/<id>/`) deployed to `.claude/agents/`, `.opencode/agents/`, `.iflow/agents/`
- **Command** source assets (`commands/<tool>/`) deployed to tool-specific command directories

---

## Specification Index

### Project-Specific Specs

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

### Repo-Specific Thinking Guides

| Guide | Path |
|-------|------|
| [Thinking Guides](./guides/index.md) | `.trellis/spec/guides/` |
| [Code Reuse Thinking](./guides/code-reuse-thinking-guide.md) | Pattern identification |
| [Cross-Layer Thinking](./guides/cross-layer-thinking-guide.md) | Repo boundary and drift prevention |

### Scope Boundary

`.trellis/spec/` is the repository-local maintenance layer for this project.

Keep only guidance that directly helps maintain these live assets and workflows:

- `trellis-library/` source assets and `manifest.yaml`
- `.trellis/scripts/` and repository automation
- `agents/`, `commands/`, `skills/`, `docs/`
- repo-specific thinking guides for sync, reuse, and drift prevention

Do not mirror generic product-planning or cross-project governance content here.
Those belong in `trellis-library/specs/` as reusable library assets, not in this
repo's local maintenance spec.

---

## Quick Start by Task Type

| Task | Must-Read Specs |
|------|----------------|
| Author a new spec in `trellis-library` | `library-assets/spec-authoring.md` |
| Author a new template | `library-assets/template-authoring.md` |
| Author a new checklist | `library-assets/checklist-authoring.md` |
| Update `manifest.yaml` | `library-assets/manifest-maintenance.md` |
| Write/modify Python scripts | `scripts/python-conventions.md` |
| Write/modify Shell scripts | `scripts/shell-conventions.md` |
| Define an agent (source + deploy) | `agents/index.md` |
| Define a command (source + deploy) | `commands/index.md` |
| Define a skill | `skills/index.md` |
| Any repo-maintenance task | `guides/index.md` |

---

## Pre-Development Checklist

Before writing ANY code or content:

1. [ ] Identify which spec layers apply to your task
2. [ ] Read the relevant index files
3. [ ] Read the specific guideline files listed in each index
4. [ ] Read `guides/index.md` for repo-specific thinking supplements
5. [ ] If modifying `trellis-library` assets, also read `library-assets/manifest-maintenance.md`

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
6. **Documentation** → see `docs/`

---

**Language**: English

# Project Documentation Guidelines

> Project-local rules for writing and organizing documentation in this repository.

---

## Overview

This directory is the **repo-local documentation layer** for `ai-coding-toolkit`.

Use this document for:
- README and directory-level structure in this repo
- workflow docs and maintenance notes that describe real repository behavior
- workflow-asset documentation under `docs/workflows/**`
- formatting, linking, and update habits for asset-library documentation

---

## Project Identity

This project is a **workflow authoring toolkit** — it creates, maintains, and distributes AI-assisted development workflows. It is not a target project that uses those workflows.

Key distinction:

| | This project (ai-coding-toolkit) | Target projects (other repos) |
|--|----------------------------------|-------------------------------|
| Role | **Author and distribute** workflow assets | **Install and use** workflow assets |
| `docs/workflows/*/` | Product source assets to maintain | Does not exist (installed as tool commands) |
| `docs/workflows/**/commands/*.md` | Source files to edit with authoring specs | Deployed copies managed by installer |
| `docs/workflows/**/commands/*.py` | Installer/upgrade scripts to develop | Scripts run once during embed |
| Workflow at runtime | Trellis native workflow (source repo is not a target) | Installed `wf` module: `.trellis/workflows/wf.md` variant + `.trellis/scripts/wf/` CLI |
| Dev process | `/trellis:start` → Trellis native brainstorm/check/finish-work | `wf route` → mechanism entries (`task new` / `start` / `close` / `repair`) |

**Critical rule**: When modifying files under `docs/workflows/`, you are editing **product assets** — the module source, the variant text, and the installer/CLI contracts described in `docs/workflows/workflow-implementation.md` are features of the product, not rules for how to develop in this project. The specs that govern your editing behavior are in `.trellis/spec/docs/` and `.trellis/spec/scripts/`.

---


| Type | Location | Purpose |
|------|----------|---------|
| Repository README | `README.md`, `README.en.md` | Explain what this repo contains and how the asset layers relate; maintain the Chinese default plus aligned English companion |
| Asset README | `agents/README.md`, `commands/*/README.md`, `docs/README.md` | Clarify scope and structure of one asset area |
| Workflow docs | `docs/workflows/**` | Human-facing workflow notes and command references |
| Trellis spec docs | `.trellis/spec/**` | Repo-local maintenance guidance plus workflow-authoring rules used by this repo |
| Workflow implementation constraints | `.trellis/spec/docs/workflow-implementation-constraints.md` | Guardrails to follow when implementing `docs/workflows/workflow-implementation.md` |
| Library docs | `trellis-library/README.md`, `trellis-library/taxonomy.md` | Source-library architecture and taxonomy |

---

## Boundary

Do not add generic application README templates, frontend/backend doc advice, or
API-reference scaffolds here. This repository is an asset library and workflow
tooling repo, not a runnable app.

Do not treat `docs/workflows/*/` content as development rules for this project.
Those are product assets — see [Project Identity](#project-identity) above.

This directory should stay focused on repository-specific documentation
conventions and examples.

---

## Directory Structure

```text
docs/
  README.md
  workflows/
    workflow-design.md              ← judgments and transitions (authority)
    依赖机制设计说明.md               ← dependency-mechanism detail
    workflow-implementation.md      ← implementation plan (module source, contracts)
    新项目开发工作流/                 ← module source; being rebuilt (legacy content retired 2026-10-28)
    旧项目重构工作流/
```

---

## Mindmap Generation

When a workflow document needs a visual companion mindmap, follow
[workflow-mindmap-spec.md](./workflow-mindmap-spec.md).

Key contracts:
- Output: self-contained `.html` file, no external deps
- Layout: right-expanding tree, parent centered on children block
- Data: inline JS `const tree = [...]` array with typed node classes

---

## README Standards

### Project Root README

Must include:
- **Project title**: Clear, searchable name
- **One-line description**: What reusable assets this repo contains
- **Repository map**: Core directories and what each one owns
- **Source-of-truth explanation**: Which directories are source assets versus derived tool deployments
- **Validation commands**: How to run repo checks that matter
- **Links**: To workflow docs, `trellis-library`, and relevant spec indexes

Additional contract for this repository:
- The project root README is a **paired bilingual asset**: `README.md` is the default Simplified Chinese entry, and `README.en.md` is the aligned English companion
- **Any modification** to the project root README content, structure, commands, paths, links, or status descriptions must update **both** `README.md` and `README.en.md` in the same change
- The two files must keep visible cross-links near the top so readers can switch languages directly

### Directory README

For subdirectories:
- **Purpose**: What this directory contains
- **Structure**: Overview of files or subdirectories
- **Source/deploy boundary**: If this directory feeds other tool-specific copies
- **Usage**: How to modify or validate these files

---

## Writing Guidelines

### Language

- **Default**: Match the directory's established language
- **Consistency**: Keep one document internally consistent
- **Commands / identifiers**: Preserve exact paths, filenames, and command names

### Formatting

- **Markdown**: Use standard MD syntax
- **Code blocks**: Language-specific syntax highlighting where useful
- **Links**: Relative paths for internal links
- **Headings**: Use ATX-style (`#`, `##`, `###`)

### Content

- **Concise**: Get to the point
- **Actionable**: Tell reader what to do
- **Complete**: Include prerequisites, steps, and verification when behavior is procedural
- **Current**: Keep up to date with code

### Workflow Boundary

- **Separate ownership layers**: Distinguish source-repo authoring files, task-local runtime artifacts, and target-project outputs
- **Name the target explicitly**: If a workflow creates or updates files in the consuming project, say "target project" and give the target path
- **Do not conflate artifacts**: Explain different roles when both task-local working files and project-level formal docs exist
- **Preserve deploy semantics**: When source docs are installed into other tool/runtime locations, state whether the rule applies to the source copy, deployed copy, or target project filesystem
- **Do not describe target architecture as current repo state**: For repo-level docs such as the root `AGENTS.md` and README files, distinguish placeholder/scaffold directories from the workflow-local source or live deployed copies that actually drive behavior today
- **Keep source-repo AGENTS separate from install-time target-project AGENTS blocks**: Installer-managed target-project sections such as `workflow-nl-routing` should be described as target-project outputs, not mirrored into this source repository's own `AGENTS.md`, unless the authoring contract explicitly requires the source repo to carry the same block
- **Use a clean Trellis baseline for source-workflow compatibility maintenance**: When documenting how this repository updates Trellis-based workflow source content after a Trellis upgrade, reference the `/tmp` fixture created by `trellis init`, not this repository's already customized `.trellis/` or CLI directories; do not present that rule as the target project's own upgrade-compat standard
- **Keep pre-release workflow versions below 1.0**: For workflow source assets under `docs/workflows/**` that are not yet officially declared production-ready, the active version must use `0.x.y`; reserve `1.0.0+` for workflows explicitly declared formally available

---

## Template: Directory README.md

```markdown
# Directory Name

Brief description of what this directory owns.

## Purpose

What belongs here and what does not.

## Structure

- `path-a/` - explanation
- `path-b/` - explanation

## Update Notes

- How to modify safely
- How to validate changes
- Related source-of-truth or deployment paths
```

---

## Quality Standards

### Must Have

- [ ] Clear title and purpose
- [ ] Logical structure with headings
- [ ] Exact repo paths and commands where applicable
- [ ] Links to related docs

### Should Have

- [ ] Small examples for non-obvious workflows
- [ ] Validation note for change-heavy docs
- [ ] Table of contents for long docs

### Anti-Patterns

- **Outdated docs**: Docs that contradict code
- **Incomplete steps**: "Do X" without explaining how
- **No context**: "Run this command" without explaining why
- **Broken links**: Internal links that don't work
- **App-centric boilerplate**: Installation or runtime sections for software this repo does not ship
- **Inconsistent formatting**: Mixed styles in same doc
- **Split bilingual README maintenance**: Updating `README.md` or `README.en.md` alone when the root README contract requires both files to stay aligned
- **Target-project ambiguity**: Referencing paths like `docs/...` without saying whether they live in this repo, a task directory, or the installed target project
- **Artifact conflation**: Treating task-local files such as `$TASK_DIR/prd.md` as equivalent to long-lived project requirement documents
- **Version drift across workflow source files**: Updating `WORKFLOW_VERSION` or a workflow title without synchronizing the other active references, installer assertions, or generated companion docs

---

## Code Examples

### Good

```bash
# Validate skill structure
./scripts/validate-skills.sh
```

### Bad

```text
Run the validator
```

---

## Links

### Internal Links

```markdown
[Workflow design](../../../docs/workflows/workflow-design.md)
[Implementation plan](../../../docs/workflows/workflow-implementation.md)
[Spec Index](../index.md)
```

### External Links

```markdown
[Skills CLI](https://www.npmjs.com/package/skills)
```

---

## Maintenance

- Review docs when code changes
- Remove obsolete information
- Check sample commands still work
- Re-test links when moving files

---

## Tools

- Markdown linters: `markdownlint`
- Link checkers: `lychee`
- Spell checkers: `cspell`

---

**Language**: Match the document's existing language and audience

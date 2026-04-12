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

## Documentation Types

| Type | Location | Purpose |
|------|----------|---------|
| Repository README | `README.md` | Explain what this repo contains and how the asset layers relate |
| Asset README | `agents/README.md`, `commands/*/README.md`, `docs/README.md` | Clarify scope and structure of one asset area |
| Workflow docs | `docs/workflows/**` | Human-facing workflow notes and command references |
| Workflow authoring spec | `docs/workflows/自定义工作流制作规范.md` | Cross-workflow authoring rules, including Trellis upgrade-compat baseline requirements |
| Trellis spec docs | `.trellis/spec/**` | Repo-local maintenance guidance plus workflow-authoring rules used by this repo |
| Library docs | `trellis-library/README.md`, `trellis-library/taxonomy.md` | Source-library architecture and taxonomy |

---

## Boundary

Do not add generic application README templates, frontend/backend doc advice, or
API-reference scaffolds here. This repository is an asset library and workflow
tooling repo, not a runnable app.

This directory should stay focused on repository-specific documentation
conventions and examples.

---

## Directory Structure

```text
docs/
  README.md
  workflows/
    新项目开发工作流/
      工作流总纲.md
      工作流思维导图.html    ← generated per workflow-mindmap-spec.md
      commands/
    旧项目重构工作流/
      工作流总纲.md
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
- **Use a clean Trellis baseline for source-workflow compatibility maintenance**: When documenting how this repository updates Trellis-based workflow source content after a Trellis upgrade, reference the `/tmp` fixture created by `trellis init`, not this repository's already customized `.trellis/` or CLI directories; do not present that rule as the target project's own upgrade-compat standard

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
- **Target-project ambiguity**: Referencing paths like `docs/...` without saying whether they live in this repo, a task directory, or the installed target project
- **Artifact conflation**: Treating task-local files such as `$TASK_DIR/prd.md` as equivalent to long-lived project requirement documents

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
[Workflow](../../../docs/workflows/新项目开发工作流/工作流总纲.md)
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

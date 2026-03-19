# Library Asset Authoring Guidelines

> How to create and maintain assets in the trellis-library.

---

## Overview

`trellis-library/` is the source asset library for Trellis project initialization. It contains six asset types registered in `manifest.yaml`:

| Asset Type | Root Directory | Format |
|-----------|---------------|--------|
| spec | `specs/` | Directory (4-file complex) or flat file |
| template | `templates/` | Single `.md` file |
| checklist | `checklists/` | Single `.md` file |
| example | `examples/` | Single `.md` file or directory |
| schema | `schemas/` | `.json` or `.yaml` file |
| script | `scripts/` | `.py` or `.sh` file |

---

## Guideline Files

Read these before authoring or modifying trellis-library assets:

| Document | When to Read |
|----------|-------------|
| [spec-authoring.md](./spec-authoring.md) | Creating or modifying spec concerns under `specs/` |
| [template-authoring.md](./template-authoring.md) | Creating or modifying templates under `templates/` |
| [checklist-authoring.md](./checklist-authoring.md) | Creating or modifying checklists under `checklists/` |
| [manifest-maintenance.md](./manifest-maintenance.md) | Registering, updating, or deprecating assets in `manifest.yaml` |

---

## Pre-Development Checklist

Before authoring or modifying ANY trellis-library asset:

1. [ ] Read the relevant guideline file from the table above
2. [ ] Check `manifest.yaml` for existing assets in the same domain
3. [ ] Read `trellis-library/taxonomy.md` for structural rules
4. [ ] If creating a new asset, read `manifest-maintenance.md` for registration rules
5. [ ] After changes, run validation:
   ```bash
   python3 trellis-library/cli.py validate --strict-warnings
   ```

---

## Naming Conventions

- **Directories**: kebab-case, e.g. `handoff-contracts`, `api-contracts`
- **Spec concerns**: `{domain}/{concern-name}/` pattern
- **Template files**: `{concern-name}-template.md`
- **Checklist files**: `{concern-name}-checklist.md`
- **Asset IDs**: `{type}.{domain_axis}.{domain}.{concern}` pattern

---

## Anti-Patterns

- Creating assets without registering them in `manifest.yaml`
- Forking imported governance specs without recording the divergence
- Using inconsistent naming (camelCase, snake_case) in directory names
- Skipping validation before committing

---

**Language**: English

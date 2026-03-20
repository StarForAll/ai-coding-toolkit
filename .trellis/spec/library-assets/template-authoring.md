# Template Authoring Guidelines

> How to create and maintain templates under `trellis-library/templates/`.

---

## Overview

Templates are reusable document structures that help standardize output across projects. They live under `templates/` organized by the same axes as specs:

```
templates/
├── universal-domains/
├── scenarios/
├── platforms/
└── technologies/
```

---

## File Format

Each template is a **single `.md` file** with the naming convention:

```
{concern-name}-template.md
```

Examples:
- `agent-handoff-template.md`
- `api-contract-template.md`
- `refactoring-plan-template.md`

---

## Content Structure

```markdown
# {Template Title}

## Purpose

<1-2 sentences: what this template is for and when to use it>

## Sections

### {Section 1 Name}

<placeholder content or instructions>

### {Section 2 Name}

<placeholder content or instructions>
```

**Rules:**
- Start with a clear title
- Include a Purpose section explaining when to use this template
- Use markdown sections as fill-in placeholders
- Keep placeholders descriptive enough that users know what to put
- Use `<placeholder>` or `<!-- instructions -->` for guidance

**Validator note:** `python3 trellis-library/cli.py validate --strict-warnings` now fails
with `invalid-template-structure` if a registered template is missing the top-level
`#` title or the `## Purpose` section.

---

## Example

```markdown
# Root Cause Analysis Template

## Purpose

Use this template to document the root cause of a defect or production issue.

## Issue Summary

<one-paragraph description of what happened>

## Timeline

### Detection

<when and how the issue was detected>

### Investigation

<steps taken to investigate>

### Resolution

<how the issue was resolved>

## Root Cause

<the underlying cause, not the symptom>

## Prevention

<what will prevent recurrence>

## Verification

<how to verify the fix works>
```

---

## Registration

Every template MUST be registered in `manifest.yaml`. See [manifest-maintenance.md](./manifest-maintenance.md).

Asset entry example:

```yaml
- id: template.universal-domains.contracts.api-contract-template
  type: template
  format: file
  path: templates/universal-domains/contracts/api-contract-template.md
  title: API Contract Template
  summary: Template for documenting API request/response contracts
  status: active
  version: 1.0.0
  domain_axis: universal-domains
  domain: contracts
  concern: api-contract-template
  atomicity: simple
  tags: [api, contract, template]
```

---

## Quality Checklist

Before finalizing a new template:

- [ ] File name ends with `-template.md`
- [ ] Purpose section explains when to use
- [ ] Sections are self-explanatory with placeholder guidance
- [ ] Registered in manifest.yaml
- [ ] Validation passes

---

**Language**: English

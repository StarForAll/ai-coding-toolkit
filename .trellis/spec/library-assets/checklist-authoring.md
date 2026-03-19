# Checklist Authoring Guidelines

> How to create and maintain checklists under `trellis-library/checklists/`.

---

## Overview

Checklists are reusable verification lists that help standardize review and readiness checks across projects. They live under `checklists/` organized by the same axes as specs:

```
checklists/
├── universal-domains/
├── scenarios/
├── platforms/
└── technologies/
```

---

## File Format

Each checklist is a **single `.md` file** with the naming convention:

```
{concern-name}-checklist.md
```

Examples:
- `handoff-readiness-checklist.md`
- `release-readiness-checklist.md`
- `security-review-checklist.md`

---

## Content Structure

```markdown
# {Checklist Title}

* <checkable item>
* <checkable item>
* <checkable item>
```

**Rules:**
- Title should match the concern name
- Each item is a bullet point
- Items must be binary checkable (pass/fail, yes/no)
- Use concrete, observable language — avoid vague criteria
- Order items by logical flow (what to check first → last)

---

## Example

```markdown
# Release Readiness Checklist

* All tests pass in CI
* No open critical or high-severity bugs
* Changelog is updated
* Rollback plan is documented
* Monitoring alerts are configured
* Feature flags are set correctly
```

---

## Relationship to Specs

Checklists often correspond to a spec concern's `verification.md`. The difference:

| File | Purpose | Audience |
|------|---------|----------|
| `verification.md` (in spec) | Formal verification criteria for the normative rules | Automated checks, formal review |
| `*-checklist.md` (in checklists) | Practical checklist for human/agent execution | Developers, AI agents during workflow |

If a spec concern has a `verification.md`, the corresponding checklist should be consistent with it but may be more practical/actionable.

---

## Registration

Every checklist MUST be registered in `manifest.yaml`. See [manifest-maintenance.md](./manifest-maintenance.md).

Asset entry example:

```yaml
- id: checklist.universal-domains.verification.release-readiness-checklist
  type: checklist
  format: file
  path: checklists/universal-domains/verification/release-readiness-checklist.md
  title: Release Readiness Checklist
  summary: Pre-release verification checklist
  status: active
  version: 1.0.0
  domain_axis: universal-domains
  domain: verification
  concern: release-readiness-checklist
  atomicity: simple
  tags: [release, verification, checklist]
```

---

## Quality Checklist

Before finalizing a new checklist:

- [ ] File name ends with `-checklist.md`
- [ ] All items are binary checkable
- [ ] Items use concrete, observable language
- [ ] Consistent with corresponding spec's verification.md (if exists)
- [ ] Registered in manifest.yaml
- [ ] Validation passes

---

**Language**: English

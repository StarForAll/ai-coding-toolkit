# Spec Authoring Guidelines

> How to create and maintain spec concerns under `trellis-library/specs/`.

---

## Overview

Specs are the normative rules of the trellis-library. They live under `specs/` organized by four axes:

```
specs/
├── universal-domains/    # Cross-project stable rules
├── scenarios/            # Process and execution scenarios
├── platforms/            # Runtime-platform constraints
└── technologies/         # Stack, framework, language constraints
```

---

## Standard Structure (Complex Concern)

Most specs use a **4-file directory** format:

```
specs/{axis}/{domain}/{concern-name}/
├── overview.md            # Purpose + Applicability
├── scope-boundary.md      # What IS and IS NOT covered
├── normative-rules.md     # The actual rules
└── verification.md        # How to verify compliance
```

### overview.md

Contains exactly two sections:

```markdown
# {Concern Name}

## Purpose

<1-3 sentences: what this concern governs>

## Applicability

<when to apply this concern>
```

**Rules:**
- Purpose must be concise and specific
- Applicability must define clear trigger conditions
- No rules or verification content here (that goes in other files)

### scope-boundary.md

Defines what the concern covers and excludes:

```markdown
# Scope Boundary

<what IS covered, 1-2 sentences>

<what IS NOT covered, 1-2 sentences>
```

**Rules:**
- Keep it short (2-4 sentences total)
- Be explicit about exclusions to prevent scope creep

### normative-rules.md

The core rules, using modal verbs (`must`, `should`, `must not`):

```markdown
# Normative Rules

* <rule using must/should/must not>
* <rule>
* <rule>
```

**Rules:**
- Each rule is a bullet point
- Use `must` for mandatory requirements
- Use `should` for recommended practices
- Use `must not` for prohibitions
- One rule per bullet, keep each rule focused
- No implementation details — state the requirement, not how to meet it

### verification.md

How to check compliance:

```markdown
# Verification

Check the following:

* <verification item>
* <verification item>
* <verification item>
```

**Rules:**
- Each item must be checkable (observable outcome)
- Frame as "check that X" rather than abstract criteria
- Cover all normative rules — every rule should have a corresponding check

---

## Alternative: Flat File Format

Some specs (especially under `technologies/`) use flat `.md` files with a `<meta>.yaml` sidecar instead of the 4-file directory. Use this format when:

- The concern has many sub-topics that don't fit the 4-file model
- The content is reference material rather than normative rules
- The concern is a technology-specific guide collection

Flat file structure:

```
specs/{axis}/{domain}/{concern-name}/
├── overview.md
├── <meta>.yaml
├── topic-1.md
├── topic-2.md
└── ...
```

---

## Registration

Every spec MUST be registered in `manifest.yaml`. See [manifest-maintenance.md](./manifest-maintenance.md).

Asset entry example:

```yaml
- id: spec.universal-domains.testing.test-strategy
  type: spec
  format: directory
  path: specs/universal-domains/testing/test-strategy
  title: Test Strategy
  summary: Rules for test pyramid, coverage targets, and test isolation
  status: active
  version: 1.0.0
  domain_axis: universal-domains
  domain: testing
  concern: test-strategy
  atomicity: complex
  tags: [testing, strategy, coverage]
```

---

## Naming Rules

- Domain and concern: kebab-case only
- Concern name must match directory name
- Asset ID format: `spec.{domain_axis}.{domain}.{concern}`
- Path format: `specs/{domain_axis}/{domain}/{concern}/`

---

## Quality Checklist

Before finalizing a new spec:

- [ ] All 4 files exist (overview, scope-boundary, normative-rules, verification)
- [ ] overview.md has Purpose and Applicability sections
- [ ] normative-rules.md uses must/should/must not correctly
- [ ] verification.md covers all normative rules
- [ ] Registered in manifest.yaml with correct metadata
- [ ] Validation passes: `python3 trellis-library/cli.py validate --strict-warnings`

---

**Language**: English

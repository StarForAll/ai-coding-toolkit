# Project Documentation Guidelines

> Project-local rules for writing and organizing documentation in this repository.

---

## Overview

This directory is the **project-local documentation layer**.
It complements imported governance specs under `.trellis/spec/universal-domains/`
instead of replacing them.

Use the imported governance specs for:
- requirement clarity and scope decisions
- acceptance criteria and verification expectations
- change management and evidence requirements

Use this document for:
- README and repository-document structure
- formatting and linking conventions
- documentation maintenance habits specific to this repo

---

## Documentation Types

| Type | Location | Purpose |
|------|----------|---------|
| README | Project root, subdirectories | Quick start, overview |
| Guides | `docs/guides/` | How-to tutorials |
| Specifications | `specs/`, `docs/specs/` | Technical specifications |
| References | `references/`, `docs/refs/` | API references, manuals |
| Changelogs | `CHANGELOG.md` | Version history |

---

## Boundary

Do not duplicate generic planning or governance rules here if they already live
under `.trellis/spec/universal-domains/`.

This directory should stay focused on repository-specific documentation
conventions and examples.

---

## Directory Structure

```
docs/
  guides/
    getting-started.md
    advanced-usage.md
  specs/
    architecture/
      overview.md
    api/
      v1/
        endpoints.md
  refs/
    glossary.md
    faq.md
```

---

## README Standards

### Project Root README

Must include:
- **Project title**: Clear, searchable name
- **One-line description**: What the project does
- **Quick start**: 3-5 lines to get running
- **Key features**: Bullet points
- **Installation**: How to install/setup
- **Links**: To more detailed docs

### Directory README

For subdirectories:
- **Purpose**: What this directory contains
- **Structure**: Overview of files
- **Usage**: How to use these files

---

## Writing Guidelines

### Language

- **Default**: English (matching project's primary language)
- **Consistency**: Pick one language, stick with it
- **Code comments**: English

### Formatting

- **Markdown**: Use standard MD syntax
- **Code blocks**: Language-specific syntax highlighting
- **Links**: Relative paths for internal links
- **Headings**: Use ATX-style (`#`, `##`, `###`)

### Content

- **Concise**: Get to the point
- **Actionable**: Tell reader what to do
- **Complete**: Include prerequisites, steps, verification
- **Current**: Keep up to date with code

---

## Template: README.md

```markdown
# Project Name

Brief description (one line).

## Quick Start

```bash
# Install
npm install

# Run
npm start
```

## Features

- Feature 1
- Feature 2

## Documentation

- [Guide 1](./docs/guide1.md)
- [Guide 2](./docs/guide2.md)

## Contributing

See CONTRIBUTING.md

## License

MIT
```

---

## Template: Guide Document

```markdown
# Guide Title

Brief introduction.

## Prerequisites

- Requirement 1
- Requirement 2

## Steps

### Step 1: Title

Description...

### Step 2: Title

Description...

## Verification

How to verify it worked.

## Troubleshooting

Common issues and solutions.
```

---

## Quality Standards

### Must Have

- [ ] Clear title and purpose
- [ ] Logical structure with headings
- [ ] Code examples where applicable
- [ ] Links to related docs

### Should Have

- [ ] Version info for versioned docs
- [ ] Last updated date
- [ ] Table of contents for long docs
- [ ] Examples section

### Anti-Patterns

- **Outdated docs**: Docs that contradict code
- **Incomplete steps**: "Do X" without explaining how
- **No context**: "Run this command" without explaining why
- **Broken links**: Internal links that don't work
- **Inconsistent formatting**: Mixed styles in same doc

---

## Code Examples

### Good

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

### Bad

```
Run npm install and then npm run dev
```

---

## Links

### Internal Links

```markdown
[Guide](./docs/guides/getting-started.md)
[API](./docs/api/reference.md)
```

### External Links

```markdown
[Node.js](https://nodejs.org)
```

---

## Maintenance

- Review docs when code changes
- Update version history
- Remove obsolete information
- Test all code examples

---

## Tools

- Markdown linters: `markdownlint`
- Link checkers: `lychee`
- Spell checkers: `cspell`

---

**Language**: English

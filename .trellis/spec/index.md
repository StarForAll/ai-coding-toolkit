# Project Specifications

> Development guidelines for this AI Coding Toolkit project.

---

## Overview

This project is an **AI Coding Toolkit** (meta-project), not a traditional web application.
It contains reusable assets for AI-assisted programming:
- Custom agents for different AI tools
- Reusable commands and scripts
- Installable skills (for Skills CLI)
- Configuration files for various AI assistants

---

## Specification Index

| Category | Description | Status |
|----------|-------------|--------|
| [agents](./agents/index.md) | AI agent configuration patterns | ✅ Ready |
| [commands](./commands/index.md) | Command/script patterns | ✅ Ready |
| [skills](./skills/index.md) | Skill definition patterns | ✅ Ready |
| [config](./config/index.md) | Configuration organization | ✅ Ready |
| [docs](./docs/index.md) | Project-specific documentation conventions | ✅ Ready |
| [guides](./guides/index.md) | Project-specific supplemental thinking guides | ✅ Ready |

## Imported Governance Specs

The following reusable governance concerns are imported from `trellis-library`
and should be treated as the primary source for cross-project planning,
verification, and sync rules in this repository:

| Domain | Concerns |
|--------|----------|
| Product and Requirements | `problem-definition`, `requirement-clarification`, `scope-boundary`, `acceptance-criteria` |
| Project Governance | `change-management`, `risk-tiering`, `library-sync-governance` |
| Verification | `evidence-requirements`, `verification-gates` |

Imported files live under:

- `./universal-domains/product-and-requirements/`
- `./universal-domains/project-governance/`
- `./universal-domains/verification/`

---

## Quick Start

1. **For scope and requirement clarity**: read `./universal-domains/product-and-requirements/`
2. **For change approval and sync governance**: read `./universal-domains/project-governance/`
3. **For evidence and verification expectations**: read `./universal-domains/verification/`
4. **For agent development**: read [agents/index.md](./agents/index.md)
5. **For command/script development**: read [commands/index.md](./commands/index.md)
6. **For skill development**: read [skills/index.md](./skills/index.md)
7. **For configuration**: read [config/index.md](./config/index.md)
8. **For project-local documentation conventions**: read [docs/index.md](./docs/index.md)
9. **For project-local supplemental guides**: read [guides/index.md](./guides/index.md)

---

## Project Type Note

This is a **meta-project** - a project that manages configurations for other tools.

- ❌ No traditional backend API surface
- ❌ No frontend UI/component development surface
- ✅ Configuration files (JSON, YAML, Markdown)
- ✅ Scripts (Shell, Python)
- ✅ Skills (Markdown with YAML frontmatter)
- ✅ Agent definitions (Markdown)
- ✅ Project-local process and documentation rules

---

## How to Fill Guidelines

The guidelines in this directory document **how this project works**, not ideals.
Only keep directories that are truly applicable to this repository. Do not keep
placeholder spec categories for work the project does not do.

Imported governance concerns under `universal-domains/` come from
`trellis-library` and should not be manually forked unless there is a deliberate
project-local divergence. When divergence is necessary, record it explicitly and
prefer contributing generalizable improvements back upstream.

For each area:
1. Document actual patterns from the codebase
2. Include real file paths as examples
3. List anti-patterns to avoid
4. Add common mistakes the team has made

---

**Language**: English

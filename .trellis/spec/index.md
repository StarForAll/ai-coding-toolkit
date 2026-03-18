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
| [docs](./docs/index.md) | Documentation standards | ✅ Ready |
| [guides](./guides/index.md) | Thinking guides for AI | ✅ Ready |
| [backend](./backend/index.md) | Backend patterns | ⚠️ N/A |
| [frontend](./frontend/index.md) | Frontend patterns | ⚠️ N/A |

---

## Quick Start

1. **For agent development**: Read [agents/index.md](./agents/index.md)
2. **For command/script development**: Read [commands/index.md](./commands/index.md)
3. **For skill development**: Read [skills/index.md](./skills/index.md)
4. **For configuration**: Read [config/index.md](./config/index.md)
5. **For documentation**: Read [docs/index.md](./docs/index.md)

---

## Project Type Note

This is a **meta-project** - a project that manages configurations for other tools.

- ❌ No backend API code
- ❌ No frontend UI components
- ✅ Configuration files (JSON, YAML, Markdown)
- ✅ Scripts (Shell, Python)
- ✅ Skills (Markdown with YAML frontmatter)
- ✅ Agent definitions (Markdown)

---

## How to Fill Guidelines

The guidelines in this directory document **how this project works**, not ideals.

For each area:
1. Document actual patterns from the codebase
2. Include real file paths as examples
3. List anti-patterns to avoid
4. Add common mistakes the team has made

---

**Language**: English

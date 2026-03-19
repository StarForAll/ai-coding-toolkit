# Script Conventions

> How to write and maintain Python and Shell scripts in this project.

---

## Overview

This project uses two types of automation scripts:

| Type | Locations | Purpose |
|------|-----------|---------|
| **Python** | `trellis-library/scripts/`, `.trellis/scripts/` | CLI tools, validation, assembly, sync |
| **Shell** | `scripts/`, `trellis-library/scripts/` | Lightweight validation, CI helpers |

---

## Guideline Files

| Document | When to Read |
|----------|-------------|
| [python-conventions.md](./python-conventions.md) | Writing or modifying Python scripts |
| [shell-conventions.md](./shell-conventions.md) | Writing or modifying Shell scripts |

---

## Pre-Development Checklist

Before writing or modifying ANY script:

1. [ ] Read the relevant convention file above
2. [ ] Check existing scripts in the same directory for patterns
3. [ ] If creating a new trellis-library script, register it in `manifest.yaml` (type: `script`)
4. [ ] Make the script executable: `chmod +x <script>`
5. [ ] Test with `--help` flag if applicable

---

## Script Locations

```
trellis-library/
├── cli.py                          # Unified CLI entry point
└── scripts/
    ├── validation/
    │   ├── validate-library-sync.py
    │   ├── validate-links.py
    │   └── validate-overview-links.py
    ├── assembly/
    │   ├── assemble-init-set.py
    │   └── write-library-lock.py
    └── sync/
        ├── sync-library-assets.py
        ├── diff-library-assets.py
        ├── propose-library-sync.py
        └── apply-library-sync.py

.trellis/scripts/
├── task.py                         # Task management
├── get_context.py                  # Session context
├── add_session.py                  # Session recording
├── init_developer.py               # Developer identity
├── get_developer.py                # Developer lookup
└── multi_agent/                    # Multi-agent pipeline
    ├── start.py
    ├── status.py
    ├── create_pr.py
    └── cleanup.py

scripts/
└── validate-skills.sh              # Skill structure validation
```

---

## Exit Code Conventions

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, missing input, runtime error) |
| 2 | Warning (only with `--strict-warnings` flag) |

---

## Anti-Patterns

- Hardcoded paths — use `Path(__file__).resolve().parent` or `argparse`
- Silent failures — always report status via stdout/stderr
- Missing `--help` — all scripts should support `-h`/`--help`
- No error handling — use `set -eu` (Shell) or proper exception handling (Python)

---

**Language**: English

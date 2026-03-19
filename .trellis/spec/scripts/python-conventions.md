# Python Script Conventions

> How to write and maintain Python scripts in this project.

---

## File Header

Every Python script must start with:

```python
#!/usr/bin/env python3
"""
<one-line description of what this script does>.
"""
```

For scripts that need future annotations:

```python
from __future__ import annotations
```

---

## CLI Interface

Use `argparse` for CLI scripts:

```python
import argparse

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="<description>")
    parser.add_argument("--library-root", default="trellis-library", help="...")
    parser.add_argument("--json", action="store_true", help="Emit output as JSON")
    parser.add_argument("--strict-warnings", action="store_true", help="...")
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    # ... implementation
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Rules:**
- `main()` returns an `int` exit code
- Use `raise SystemExit(main())` for the entry point
- Support `--json` for machine-readable output where applicable
- Support `--strict-warnings` for validation scripts

---

## Path Resolution

For scripts that need to reference files relative to their location:

```python
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # adjust as needed
```

**Rules:**
- Use `pathlib.Path`, not `os.path`
- Resolve to absolute paths early
- Pass library root as CLI argument when possible, don't assume cwd

---

## Data Classes

Use `@dataclass` for structured data:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Finding:
    level: str        # ERROR, WARN, INFO
    code: str         # kebab-case error code
    message: str      # human-readable
    path: str | None = None
    details: dict[str, Any] | None = None
```

---

## YAML Handling

```python
import yaml

def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise SystemExit(f"Failed to parse YAML: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Root must be a mapping: {path}")
    return data
```

---

## Output Formatting

Support both human-readable and JSON output:

```python
import json
from collections import defaultdict

def print_human(findings: list[Finding]) -> None:
    if not findings:
        print("PASS: no issues found")
        return

    by_level: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_level[finding.level].append(finding)

    for level in ["ERROR", "WARN", "INFO"]:
        group = by_level.get(level, [])
        if not group:
            continue
        print(f"{level} ({len(group)})")
        for item in group:
            suffix = f" [{item.path}]" if item.path else ""
            print(f"  - {item.code}: {item.message}{suffix}")
        print()

# In main():
if args.json:
    print(json.dumps([f.as_dict() for f in findings], indent=2, ensure_ascii=False))
else:
    print_human(findings)
```

---

## Exit Codes

| Code | Condition |
|------|-----------|
| 0 | No errors (warnings OK unless `--strict-warnings`) |
| 1 | At least one ERROR |
| 2 | Warnings with `--strict-warnings` |

```python
errors = sum(1 for f in findings if f.level == "ERROR")
warnings = sum(1 for f in findings if f.level == "WARN")

if errors:
    return 1
if warnings and args.strict_warnings:
    return 2
return 0
```

---

## CLI Dispatcher Pattern

For multi-command CLIs (like `cli.py`):

```python
SCRIPT_MAP = {
    "validate": "scripts/validation/validate-library-sync.py",
    "assemble": "scripts/assembly/assemble-init-set.py",
}

def run_script(script_rel_path: str, forwarded_args: list[str]) -> int:
    library_root = Path(__file__).resolve().parent
    script_path = library_root / script_rel_path
    result = subprocess.run([sys.executable, str(script_path), *forwarded_args], check=False)
    return result.returncode
```

---

## Quality Checklist

Before finalizing a Python script:

- [ ] Has `#!/usr/bin/env python3` shebang
- [ ] Has module docstring
- [ ] Uses `argparse` for CLI
- [ ] Returns proper exit codes
- [ ] Uses `pathlib.Path` for paths
- [ ] Handles errors with clear messages
- [ ] Supports `--help`
- [ ] Is executable: `chmod +x`

---

**Language**: English

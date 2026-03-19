# Shell Script Conventions

> How to write and maintain Shell scripts in this project.

---

## File Header

Every Shell script must start with:

```sh
#!/usr/bin/env sh
set -eu
```

**Rules:**
- Use `sh` (POSIX) unless bash-specific features are required
- `set -eu`: `-e` exit on error, `-u` error on undefined variables
- If bash is needed: `#!/usr/bin/env bash` and `set -euo pipefail`

---

## Error Handling

Use a `fail()` helper function:

```sh
fail() {
  echo "ERROR: $*" >&2
  exit 1
}
```

Usage:

```sh
[ -d "skills" ] || fail "missing ./skills directory"
command -v jq >/dev/null 2>&1 || fail "jq is required but not installed"
```

---

## Output

- Print errors to **stderr**: `echo "ERROR: ..." >&2`
- Print success to **stdout**: `echo "OK: validated N item(s)"`
- Use consistent prefixes: `ERROR:`, `WARN:`, `OK:`

---

## Variable Handling

```sh
# Quote all variable expansions
echo "$MY_VAR"

# Use ${VAR:-default} for optional variables
OUTPUT="${OUTPUT:-}"

# Use ${VAR:?} for required variables
INPUT="${INPUT:?INPUT is required}"

# Check if variable is set
if [ -z "${VERBOSE:-}" ]; then
  # verbose mode off
  :
fi
```

---

## Loops and Conditionals

```sh
# File iteration
for skill_md in skills/*/SKILL.md; do
  [ -f "$skill_md" ] || continue
  # process "$skill_md"
done

# String comparison
if [ "$first_line" != "---" ]; then
  fail "$skill_md must start with '---'"
fi

# Numeric comparison
if [ "$count" -eq 0 ]; then
  fail "no items found"
fi
```

---

## Command Validation

Check for required tools at the start:

```sh
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v jq >/dev/null 2>&1 || fail "jq is required"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (via `fail()` or command failure) |

---

## Example: Complete Script

```sh
#!/usr/bin/env sh
set -eu

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

# Validate prerequisites
[ -d "skills" ] || fail "missing ./skills directory"

found=0

for skill_md in skills/*/SKILL.md; do
  [ -f "$skill_md" ] || continue
  found=$((found + 1))

  first_line="$(sed -n '1p' "$skill_md" | tr -d '\r')"
  [ "$first_line" = "---" ] || fail "$skill_md must start with '---'"
done

[ "$found" -gt 0 ] || fail "no skills found"
echo "OK: validated $found skill(s)"
```

---

## Quality Checklist

Before finalizing a Shell script:

- [ ] Has `#!/usr/bin/env sh` shebang
- [ ] Has `set -eu` (or `set -euo pipefail` for bash)
- [ ] Has `fail()` helper function
- [ ] All variables are quoted
- [ ] Errors go to stderr
- [ ] Required commands are validated
- [ ] Is executable: `chmod +x`

---

**Language**: English

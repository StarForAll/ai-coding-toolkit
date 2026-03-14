#!/usr/bin/env sh
set -eu

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

if [ ! -d "skills" ]; then
  fail "missing ./skills directory"
fi

found=0

for skill_md in skills/*/SKILL.md; do
  if [ ! -f "$skill_md" ]; then
    continue
  fi

  found=$((found + 1))

  first_line="$(sed -n '1p' "$skill_md" | tr -d '\r')"
  if [ "$first_line" != "---" ]; then
    fail "$skill_md must start with '---' YAML frontmatter delimiter"
  fi

  # Find the closing delimiter. We expect the second '---' to appear near the top.
  closing_line="$(awk 'NR>1 { sub(/\r$/, ""); if ($0=="---") { print NR; exit } }' "$skill_md")"
  if [ -z "${closing_line:-}" ] || [ "$closing_line" -gt 120 ]; then
    fail "$skill_md missing closing '---' YAML frontmatter delimiter within first 120 lines"
  fi

  # Validate required keys are present somewhere in the YAML block.
  yaml_block="$(sed -n "2,$((closing_line - 1))p" "$skill_md" | tr -d '\r')"
  echo "$yaml_block" | grep -Eq '^[[:space:]]*name:[[:space:]]*[^[:space:]].*$' || fail "$skill_md missing YAML key: name"
  echo "$yaml_block" | grep -Eq '^[[:space:]]*description:[[:space:]]*[^[:space:]].*$' || fail "$skill_md missing YAML key: description"
done

if [ "$found" -eq 0 ]; then
  fail "no skills found under skills/*/SKILL.md"
fi

echo "OK: validated $found skill(s)"

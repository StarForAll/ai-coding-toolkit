#!/usr/bin/env sh
set -eu

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

validate_skill_dir() {
  _dir="$1"
  _label="$2"

  if [ ! -d "$_dir" ]; then
    return
  fi

  for skill_dir in "$_dir"/*/; do
    if [ ! -d "$skill_dir" ]; then
      continue
    fi

    skill_md="${skill_dir}SKILL.md"
    if [ ! -f "$skill_md" ]; then
      continue
    fi

    skill_name="$(basename "${skill_dir%/}")"

    found=$((found + 1))

    first_line="$(sed -n '1p' "$skill_md" | tr -d '\r')"
    if [ "$first_line" != "---" ]; then
      fail "$skill_md must start with '---' YAML frontmatter delimiter ($_label)"
    fi

    closing_line="$(awk 'NR>1 { sub(/\r$/, ""); if ($0=="---") { print NR; exit } }' "$skill_md")"
    if [ -z "${closing_line:-}" ] || [ "$closing_line" -gt 120 ]; then
      fail "$skill_md missing closing '---' YAML frontmatter delimiter within first 120 lines ($_label)"
    fi

    yaml_block="$(sed -n "2,$((closing_line - 1))p" "$skill_md" | tr -d '\r')"
    echo "$yaml_block" | grep -Eq '^[[:space:]]*name:[[:space:]]*[^[:space:]].*$' || fail "$skill_md missing YAML key: name ($_label)"
    echo "$yaml_block" | grep -Eq '^[[:space:]]*description:[[:space:]]*[^[:space:]].*$' || fail "$skill_md missing YAML key: description ($_label)"

    # Validate tests/ dir when SKILL.md declares scenario files
    if grep -Eq '^- `?tests/' "$skill_md" 2>/dev/null || grep -Eq 'Required persisted scenario files:' "$skill_md" 2>/dev/null; then
      if grep -Eq '^- `?tests/' "$skill_md" 2>/dev/null; then
        if [ ! -d "${skill_dir}tests" ]; then
          fail "$skill_md lists tests/ scenario files but ${skill_dir}tests/ does not exist ($_label, skill=$skill_name)"
        fi
      fi
    fi
    # Validate references/ dir when SKILL.md declares reference files
    if grep -Eq '^- `?references/' "$skill_md" 2>/dev/null; then
      if [ ! -d "${skill_dir}references" ]; then
        fail "$skill_md lists references/ files but ${skill_dir}references/ does not exist ($_label, skill=$skill_name)"
      fi
    fi
  done
}

found=0

# Public skills directory
if [ -d "skills" ]; then
  validate_skill_dir "skills" "public"
fi

# Repo-local skill directories
validate_skill_dir ".agents/skills" "agents"
validate_skill_dir ".claude/skills" "claude"

if [ "$found" -eq 0 ]; then
  fail "no skills found under skills/*/, .agents/skills/*/, or .claude/skills/*/"
fi

# ── Spec cross-validation ──
# For each spec under .trellis/spec/skills/*.md that lists Required persisted
# scenario files or references, verify:
#   1. Declared files exist in BOTH repo-local skill directories
#   2. tests/ and references/ file lists are identical between .agents/ and .claude/
# This catches single-side drift that would otherwise be missed.

spec_cross_fail=0

if [ -d ".trellis/spec/skills" ]; then
  for spec_file in .trellis/spec/skills/*.md; do
    if [ ! -f "$spec_file" ] || [ "$(basename "$spec_file")" = "index.md" ]; then
      continue
    fi

    spec_name="$(basename "$spec_file" .md)"

    # Collect declared test basenames from spec (lines like "- tests/01-xxx.md")
    spec_test_files="$(sed -n '/Required persisted scenario/,/^---\|^## /{ /^- /{ s/.*tests\///; s/`.*//; p } }' "$spec_file")"

    # Collect declared reference basenames from spec
    spec_ref_files="$(sed -n '/^## References/,/^---\|^## /{ /^- /{ s/.*references\///; s/`.*//; p } }' "$spec_file")"

    # Also read from the repo-local SKILL.md files
    agents_skill_md=".agents/skills/$spec_name/SKILL.md"
    claude_skill_md=".claude/skills/$spec_name/SKILL.md"

    # Build merged test file list from spec + both SKILL.md files
    # Only extract lines that contain "tests/" in the path
    all_test_files="$spec_test_files"
    for repo_md in "$agents_skill_md" "$claude_skill_md"; do
      if [ -f "$repo_md" ]; then
        repo_tests="$(sed -n '/Required persisted scenario\|^## Tests/,/^---\|^## /{ /^- /{ /tests\//{ s/.*tests\///; s/`.*//; p } } }' "$repo_md")"
        all_test_files="$(printf '%s\n%s' "$all_test_files" "$repo_tests")"
      fi
    done
    all_test_files="$(echo "$all_test_files" | sort -u | { grep -v '^$' || true; })"

    # Build merged reference file list
    # Only extract lines that contain "references/" in the path
    all_ref_files="$spec_ref_files"
    for repo_md in "$agents_skill_md" "$claude_skill_md"; do
      if [ -f "$repo_md" ]; then
        repo_refs="$(sed -n '/^## References/,/^---\|^## /{ /^- /{ /references\//{ s/.*references\///; s/`.*//; p } } }' "$repo_md")"
        all_ref_files="$(printf '%s\n%s' "$all_ref_files" "$repo_refs")"
      fi
    done
    all_ref_files="$(echo "$all_ref_files" | sort -u | { grep -v '^$' || true; })"

    # Check declared files exist in BOTH repo-local directories
    for repo_dir in ".agents/skills/$spec_name" ".claude/skills/$spec_name"; do
      repo_label="$(echo "$repo_dir" | cut -d/ -f1)"

      if [ -n "$all_test_files" ]; then
        if [ ! -d "$repo_dir/tests" ]; then
          echo "ERROR: $spec_name ($repo_label): declares test files but $repo_dir/tests/ does not exist" >&2
          spec_cross_fail=1
        else
          # Check each declared test file
          for tf in $all_test_files; do
            if [ ! -f "$repo_dir/tests/$tf" ]; then
              echo "ERROR: $spec_name ($repo_label): declared tests/$tf missing" >&2
              spec_cross_fail=1
            fi
          done
        fi
      fi

      if [ -n "$all_ref_files" ]; then
        if [ ! -d "$repo_dir/references" ]; then
          echo "ERROR: $spec_name ($repo_label): declares reference files but $repo_dir/references/ does not exist" >&2
          spec_cross_fail=1
        else
          # Check each declared reference file
          for rf in $all_ref_files; do
            if [ ! -f "$repo_dir/references/$rf" ]; then
              echo "ERROR: $spec_name ($repo_label): declared references/$rf missing" >&2
              spec_cross_fail=1
            fi
          done
        fi
      fi
    done

    # ── Dual-surface file-list drift detection ──
    # For skills in both .agents/ and .claude/, verify tests/ and references/
    # file lists are identical. Content differences are a separate concern.
    agents_dir=".agents/skills/$spec_name"
    claude_dir=".claude/skills/$spec_name"

    if [ -d "$agents_dir/tests" ] && [ -d "$claude_dir/tests" ]; then
      agents_test_list="$(ls "$agents_dir/tests/" 2>/dev/null | sort)"
      claude_test_list="$(ls "$claude_dir/tests/" 2>/dev/null | sort)"
      if [ "$agents_test_list" != "$claude_test_list" ]; then
        echo "ERROR: $spec_name tests/ file list drift between .agents/ and .claude/" >&2
        echo "  .agents: $(echo "$agents_test_list" | tr '\n' ' ')" >&2
        echo "  .claude: $(echo "$claude_test_list" | tr '\n' ' ')" >&2
        spec_cross_fail=1
      fi
    fi

    if [ -d "$agents_dir/references" ] && [ -d "$claude_dir/references" ]; then
      agents_ref_list="$(ls "$agents_dir/references/" 2>/dev/null | sort)"
      claude_ref_list="$(ls "$claude_dir/references/" 2>/dev/null | sort)"
      if [ "$agents_ref_list" != "$claude_ref_list" ]; then
        echo "ERROR: $spec_name references/ file list drift between .agents/ and .claude/" >&2
        echo "  .agents: $(echo "$agents_ref_list" | tr '\n' ' ')" >&2
        echo "  .claude: $(echo "$claude_ref_list" | tr '\n' ' ')" >&2
        spec_cross_fail=1
      fi
    fi
  done
fi

if [ "$spec_cross_fail" -ne 0 ]; then
  fail "spec cross-validation failed: declared files missing or dual-surface drift detected"
fi

echo "OK: validated $found skill(s) + spec cross-check passed"

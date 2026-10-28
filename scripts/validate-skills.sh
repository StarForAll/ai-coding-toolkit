#!/usr/bin/env sh
set -eu

# Space-separated skill ids intentionally defined in both `skills/` and a
# repo-local skill surface. Keep empty by default; add an entry only when the
# split is intentional and separately documented.
ALLOWLIST_PUBLIC_AND_REPO_LOCAL_DUPLICATES=""

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

extract_section_code_block() {
  _path="$1"
  _section="$2"
  awk -v section="$_section" '
    $0 == section { in_section=1; next }
    in_code {
      print
      if (/^```$/) {
        exit
      }
      next
    }
    in_section && /^```/ {
      if (!in_code) {
        in_code=1
        print
        next
      }
    }
    in_section && /^### / { exit }
  ' "$_path"
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
#   1. For repo-local maintainer skills: declared files exist in BOTH
#      repo-local skill directories, and file lists do not drift.
#   2. For installable public skills: declared files exist under skills/<name>/.
# This catches single-side drift while still supporting public skills that do
# not have .agents/.claude mirrors.

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

    public_skill_md="skills/$spec_name/SKILL.md"
    agents_skill_md=".agents/skills/$spec_name/SKILL.md"
    claude_skill_md=".claude/skills/$spec_name/SKILL.md"

    public_dir="skills/$spec_name"
    agents_dir=".agents/skills/$spec_name"
    claude_dir=".claude/skills/$spec_name"
    has_public=0
    has_repo_local=0

    [ -f "$public_skill_md" ] && has_public=1
    if [ -f "$agents_skill_md" ] || [ -f "$claude_skill_md" ]; then
      has_repo_local=1
    fi

    public_test_files="$spec_test_files"
    public_ref_files="$spec_ref_files"
    repo_local_test_files="$spec_test_files"
    repo_local_ref_files="$spec_ref_files"

    if [ -f "$public_skill_md" ]; then
      public_repo_tests="$(sed -n '/Required persisted scenario\|^## Tests/,/^---\|^## /{ /^- /{ /tests\//{ s/.*tests\///; s/`.*//; p } } }' "$public_skill_md")"
      public_repo_refs="$(sed -n '/^## References/,/^---\|^## /{ /^- /{ /references\//{ s/.*references\///; s/`.*//; p } } }' "$public_skill_md")"
      public_test_files="$(printf '%s\n%s' "$public_test_files" "$public_repo_tests")"
      public_ref_files="$(printf '%s\n%s' "$public_ref_files" "$public_repo_refs")"
    fi
    public_test_files="$(echo "$public_test_files" | sort -u | { grep -v '^$' || true; })"
    public_ref_files="$(echo "$public_ref_files" | sort -u | { grep -v '^$' || true; })"

    for repo_md in "$agents_skill_md" "$claude_skill_md"; do
      if [ -f "$repo_md" ]; then
        repo_tests="$(sed -n '/Required persisted scenario\|^## Tests/,/^---\|^## /{ /^- /{ /tests\//{ s/.*tests\///; s/`.*//; p } } }' "$repo_md")"
        repo_refs="$(sed -n '/^## References/,/^---\|^## /{ /^- /{ /references\//{ s/.*references\///; s/`.*//; p } } }' "$repo_md")"
        repo_local_test_files="$(printf '%s\n%s' "$repo_local_test_files" "$repo_tests")"
        repo_local_ref_files="$(printf '%s\n%s' "$repo_local_ref_files" "$repo_refs")"
      fi
    done
    repo_local_test_files="$(echo "$repo_local_test_files" | sort -u | { grep -v '^$' || true; })"
    repo_local_ref_files="$(echo "$repo_local_ref_files" | sort -u | { grep -v '^$' || true; })"

    if [ "$has_public" -eq 1 ]; then
      if [ -n "$public_test_files" ]; then
        if [ ! -d "$public_dir/tests" ]; then
          echo "ERROR: $spec_name (public): declares test files but $public_dir/tests/ does not exist" >&2
          spec_cross_fail=1
        else
          for tf in $public_test_files; do
            if [ ! -f "$public_dir/tests/$tf" ]; then
              echo "ERROR: $spec_name (public): declared tests/$tf missing" >&2
              spec_cross_fail=1
            fi
          done
        fi
      fi

      if [ -n "$public_ref_files" ]; then
        if [ ! -d "$public_dir/references" ]; then
          echo "ERROR: $spec_name (public): declares reference files but $public_dir/references/ does not exist" >&2
          spec_cross_fail=1
        else
          for rf in $public_ref_files; do
            if [ ! -f "$public_dir/references/$rf" ]; then
              echo "ERROR: $spec_name (public): declared references/$rf missing" >&2
              spec_cross_fail=1
            fi
          done
        fi
      fi
    fi

    if [ "$has_public" -eq 1 ] && [ "$has_repo_local" -eq 1 ]; then
      case " $ALLOWLIST_PUBLIC_AND_REPO_LOCAL_DUPLICATES " in
        *" $spec_name "*)
          ;;
        *)
          echo "ERROR: $spec_name is defined in both skills/ and repo-local skill directories; add an allowlist entry here only if the split is intentional and separately documented" >&2
          spec_cross_fail=1
          ;;
      esac
    fi

    # Check declared files exist in BOTH repo-local directories when this is a
    # repo-local maintainer skill surface.
    if [ "$has_repo_local" -eq 1 ]; then
      for repo_dir in "$agents_dir" "$claude_dir"; do
        repo_label="$(echo "$repo_dir" | cut -d/ -f1)"

        if [ -n "$repo_local_test_files" ]; then
          if [ ! -d "$repo_dir/tests" ]; then
            echo "ERROR: $spec_name ($repo_label): declares test files but $repo_dir/tests/ does not exist" >&2
            spec_cross_fail=1
          else
            # Check each declared test file
            for tf in $repo_local_test_files; do
              if [ ! -f "$repo_dir/tests/$tf" ]; then
                echo "ERROR: $spec_name ($repo_label): declared tests/$tf missing" >&2
                spec_cross_fail=1
              fi
            done
          fi
        fi

        if [ -n "$repo_local_ref_files" ]; then
          if [ ! -d "$repo_dir/references" ]; then
            echo "ERROR: $spec_name ($repo_label): declares reference files but $repo_dir/references/ does not exist" >&2
            spec_cross_fail=1
          else
            # Check each declared reference file
            for rf in $repo_local_ref_files; do
              if [ ! -f "$repo_dir/references/$rf" ]; then
                echo "ERROR: $spec_name ($repo_label): declared references/$rf missing" >&2
                spec_cross_fail=1
              fi
            done
          fi
        fi
      done
    fi

    # ── Dual-surface file-list drift detection ──
    # For skills in both .agents/ and .claude/, verify tests/ and references/
    # file lists are identical. Content differences are a separate concern.
    if [ "$has_repo_local" -eq 1 ] && [ -d "$agents_dir/tests" ] && [ -d "$claude_dir/tests" ]; then
      agents_test_list="$(ls "$agents_dir/tests/" 2>/dev/null | sort)"
      claude_test_list="$(ls "$claude_dir/tests/" 2>/dev/null | sort)"
      if [ "$agents_test_list" != "$claude_test_list" ]; then
        echo "ERROR: $spec_name tests/ file list drift between .agents/ and .claude/" >&2
        echo "  .agents: $(echo "$agents_test_list" | tr '\n' ' ')" >&2
        echo "  .claude: $(echo "$claude_test_list" | tr '\n' ' ')" >&2
        spec_cross_fail=1
      fi
    fi

    if [ "$has_repo_local" -eq 1 ] && [ -d "$agents_dir/references" ] && [ -d "$claude_dir/references" ]; then
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

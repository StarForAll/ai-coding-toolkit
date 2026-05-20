#!/usr/bin/env sh
set -eu

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

validate_workflow_scan_repair_contract() {
  scan_skill="skills/workflow-scan/SKILL.md"
  repair_skill="skills/workflow-repair/SKILL.md"
  scan_template="skills/workflow-scan/references/scan-output-template.md"
  correction_plan_template="skills/workflow-repair/references/correction-plan-template.md"
  repair_log_template="skills/workflow-repair/references/repair-log-template.md"
  issue_history_template="skills/workflow-repair/references/issue-history-template.md"
  scan_spec=".trellis/spec/skills/workflow-scan.md"
  repair_spec=".trellis/spec/skills/workflow-repair.md"
  skills_index=".trellis/spec/skills/index.md"

  [ -f "$scan_skill" ] || fail "missing $scan_skill"
  [ -f "$repair_skill" ] || fail "missing $repair_skill"
  [ -f "$scan_template" ] || fail "missing $scan_template"
  [ -f "$correction_plan_template" ] || fail "missing $correction_plan_template"
  [ -f "$repair_log_template" ] || fail "missing $repair_log_template"
  [ -f "$issue_history_template" ] || fail "missing $issue_history_template"
  [ -f "$scan_spec" ] || fail "missing $scan_spec"
  [ -f "$repair_spec" ] || fail "missing $repair_spec"
  [ -f "$skills_index" ] || fail "missing $skills_index"

  frontmatter_block="$(extract_section_code_block "$scan_template" '### YAML Frontmatter (Required)')"
  [ -n "$frontmatter_block" ] || fail "$scan_template missing YAML frontmatter example block"

  findings_block="$(extract_section_code_block "$scan_template" '### Findings Section (Required)')"
  [ -n "$findings_block" ] || fail "$scan_template missing markdown findings example block"

  # Shared frontmatter keys required by the workflow-scan/workflow-repair pair.
  for key in \
    "document-type: workflow-questions" \
    "protocol: workflow-scan-repair-v2" \
    "trellis-version:" \
    "workflow-version:" \
    "workflow-schema-version:" \
    "scan-timestamp:" \
    "temp-project-root:" \
    "total-findings:" \
    "p0-count:" \
    "p1-count:" \
    "p2-count:"
  do
    echo "$frontmatter_block" | grep -Fq "$key" || fail "$scan_template frontmatter example missing shared contract key: $key"
  done

  for section in \
    "## Scan Summary" \
    "## Analysis Summary" \
    "### WS-NNN"
  do
    grep -Fq "$section" "$scan_template" || fail "$scan_template missing required section marker: $section"
  done

  for field in \
    "- **Category**:" \
    "- **Severity Estimate**:" \
    "- **Origin**:" \
    "- **Evidence Layer**:" \
    "- **Evidence**:" \
    "- **Temp Project Location**:" \
    "- **Description**:" \
    "- **Suggested Investigation**:"
  do
    echo "$findings_block" | grep -Fq -- "$field" || fail "$scan_template findings example missing required field: $field"
  done

  grep -Fq "Count consistency rule:" "$scan_template" || fail "$scan_template missing count consistency rule section"
  grep -Fq "total-findings" "$scan_template" || fail "$scan_template missing count consistency reference for total-findings"
  grep -Fq "p0-count" "$scan_template" || fail "$scan_template missing count consistency reference for p0-count"
  grep -Fq "p1-count" "$scan_template" || fail "$scan_template missing count consistency reference for p1-count"
  grep -Fq "p2-count" "$scan_template" || fail "$scan_template missing count consistency reference for p2-count"

  # Guard against known drift that blocked workflow-repair intake.
  for bad_key in \
    "generated_at:" \
    "trellis_version:" \
    "workflow_version:" \
    "workflow_schema_version:" \
    "temp_project_path:" \
    "total_findings:" \
    "p0_count:" \
    "p1_count:" \
    "p2_count:"
  do
    if grep -Fq "$bad_key" "$scan_template"; then
      fail "$scan_template contains drift-prone snake_case key: $bad_key"
    fi
  done

  grep -Fq "Read-back validation is mandatory" "$scan_skill" || fail "$scan_skill missing read-back validation rule"
  grep -Fq "Immediately read the file back and verify" "$scan_skill" || fail "$scan_skill missing explicit post-write verification step"
  grep -Fq "count and per-severity counts" "$scan_skill" || fail "$scan_skill missing count consistency validation"
  grep -Fq "snake_case" "$scan_skill" || fail "$scan_skill should explicitly guard against snake_case contract drift"

  grep -Fq "\`document-type\` must be \`workflow-questions\`" "$repair_skill" || fail "$repair_skill missing repair-side intake requirement for document-type"
  grep -Fq "\`protocol\` must be \`workflow-scan-repair-v2\`" "$repair_skill" || fail "$repair_skill missing repair-side intake requirement for protocol"
  for repair_key in \
    "\`trellis-version\`" \
    "\`workflow-version\`" \
    "\`workflow-schema-version\`" \
    "\`scan-timestamp\`" \
    "\`temp-project-root\`" \
    "\`total-findings\`" \
    "\`p0-count\`" \
    "\`p1-count\`" \
    "\`p2-count\`"
  do
    grep -Fq "$repair_key" "$repair_skill" || fail "$repair_skill missing repair-side intake key reference: $repair_key"
  done
  grep -Fq "## Scan Summary" "$repair_skill" || fail "$repair_skill missing repair-side section validation for Scan Summary"
  grep -Fq "## Analysis Summary" "$repair_skill" || fail "$repair_skill missing repair-side section validation for Analysis Summary"
  grep -Fq "### WS-NNN" "$repair_skill" || fail "$repair_skill missing repair-side section validation for finding headings"
  grep -Fq "count and per-severity counts" "$repair_skill" || fail "$repair_skill missing count consistency validation"

  for template in \
    "$correction_plan_template" \
    "$repair_log_template" \
    "$issue_history_template"
  do
    grep -Fq "workflow-scan-repair-v2" "$template" || fail "$template missing shared protocol version"
  done
  grep -Fq "{trellis-version from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing trellis-version placeholder from scan report"
  grep -Fq "{workflow-version from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing workflow-version placeholder from scan report"
  grep -Fq "{scan-timestamp from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing scan-timestamp placeholder from scan report"
  grep -Fq "{temp-project-root from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing temp-project-root placeholder from scan report"
  grep -Fq "{absolute path to WORKFLOW_QUESTIONS.md}" "$repair_log_template" || fail "$repair_log_template missing source-report placeholder"
  grep -Fq "{absolute path to WORKFLOW_QUESTIONS.md}" "$issue_history_template" || fail "$issue_history_template missing report-path placeholder"

  grep -Fq "read-back validation" "$scan_spec" || fail "$scan_spec missing read-back validation contract"
  grep -Fq "read-back validation" "$repair_spec" || fail "$repair_spec missing paired read-back validation note"
  grep -Fq "read-back validation" "$skills_index" || fail "$skills_index missing paired contract read-back validation note"
  grep -Fq "count fields match the actual number of findings" "$scan_spec" || fail "$scan_spec missing count consistency contract"
  grep -Fq "declared total/severity counts" "$repair_spec" || fail "$repair_spec missing repair-side count consistency contract"
  grep -Fq "total/severity count semantics" "$skills_index" || fail "$skills_index missing paired count consistency note"
}

validate_workflow_scan_repair_contract

echo "OK: validated $found skill(s) + spec cross-check passed"

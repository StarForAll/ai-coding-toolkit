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

validate_workflow_scan_repair_contract() {
  scan_skill="skills/workflow-scan/SKILL.md"
  repair_skill="skills/workflow-repair/SKILL.md"
  scan_template="skills/workflow-scan/references/scan-output-template.md"
  scan_handoff_template="skills/workflow-scan/references/helper-handoff-template.md"
  correction_plan_template="skills/workflow-repair/references/correction-plan-template.md"
  repair_log_template="skills/workflow-repair/references/repair-log-template.md"
  closure_round_template="skills/workflow-repair/references/closure-round-template.md"
  issue_history_template="skills/workflow-repair/references/issue-history-template.md"
  scan_spec=".trellis/spec/skills/workflow-scan.md"
  repair_spec=".trellis/spec/skills/workflow-repair.md"
  skills_index=".trellis/spec/skills/index.md"

  [ -f "$scan_skill" ] || fail "missing $scan_skill"
  [ -f "$repair_skill" ] || fail "missing $repair_skill"
  [ -f "$scan_template" ] || fail "missing $scan_template"
  [ -f "$scan_handoff_template" ] || fail "missing $scan_handoff_template"
  [ -f "$correction_plan_template" ] || fail "missing $correction_plan_template"
  [ -f "$repair_log_template" ] || fail "missing $repair_log_template"
  [ -f "$closure_round_template" ] || fail "missing $closure_round_template"
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
    "protocol: workflow-scan-repair-v4" \
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
    "- **Repair Classification**:" \
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
  grep -Fq "Confirmed Defects" "$scan_template" || fail "$scan_template missing confirmed-defects analysis summary field"
  grep -Fq "Design-Debt Items" "$scan_template" || fail "$scan_template missing design-debt analysis summary field"
  grep -Fq "Evidence-Gap Items" "$scan_template" || fail "$scan_template missing evidence-gap analysis summary field"
  grep -Fq "Execution-mode note:" "$scan_template" || fail "$scan_template missing execution-mode note"
  grep -Fq "\`--agent\` helper assistance" "$scan_template" || fail "$scan_template missing explicit --agent execution-mode note"
  grep -Eq 'MUST NOT.*WORKFLOW_QUESTIONS\.md.*schema' "$scan_template" || fail "$scan_template missing normative no-schema-change rule"
  grep -Fq "coordinator-owned" "$scan_template" || fail "$scan_template missing coordinator-owned report note"
  grep -Fq "not part of the shared scan/repair protocol surface" "$scan_template" || fail "$scan_template missing explicit helper-handoff boundary note"
  grep -Fq "## Helper Scope" "$scan_handoff_template" || fail "$scan_handoff_template missing Helper Scope section"
  grep -Fq "## Confirmed Facts" "$scan_handoff_template" || fail "$scan_handoff_template missing Confirmed Facts section"
  grep -Fq "## Candidate Issues" "$scan_handoff_template" || fail "$scan_handoff_template missing Candidate Issues section"
  grep -Fq "## Open Questions" "$scan_handoff_template" || fail "$scan_handoff_template missing Open Questions section"
  grep -Fq "## Relative Paths" "$scan_handoff_template" || fail "$scan_handoff_template missing Relative Paths section"
  grep -Fq "## Status" "$scan_handoff_template" || fail "$scan_handoff_template missing Status section"

  for test_file in \
    "skills/workflow-scan/tests/01-inline-default-no-agents.md" \
    "skills/workflow-scan/tests/02-agent-assisted-supported.md" \
    "skills/workflow-scan/tests/03-agent-mode-unsupported.md" \
    "skills/workflow-scan/tests/04-helper-failure-local-compensation.md" \
    "skills/workflow-scan/tests/05-unresolved-helper-conflict-dropped.md" \
    "skills/workflow-scan/tests/06-partial-helper-output-local-followup.md" \
    "skills/workflow-scan/tests/07-inline-when-speed-or-depth-only.md" \
    "skills/workflow-scan/tests/08-classifies-repair-eligibility-before-emitting-findings.md"
  do
    [ -f "$test_file" ] || fail "missing $test_file"
    grep -Fq "## Purpose" "$test_file" || fail "$test_file missing Purpose section"
    grep -Fq "## Input" "$test_file" || fail "$test_file missing Input section"
    grep -Fq "## Expected Mode" "$test_file" || fail "$test_file missing Expected Mode section"
    grep -Fq "## Expected Key Behaviors" "$test_file" || fail "$test_file missing Expected Key Behaviors section"
    grep -Fq "## Must Not" "$test_file" || fail "$test_file missing Must Not section"
  done

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
  grep -Fq "\`--agent\`" "$scan_skill" || fail "$scan_skill missing explicit --agent input contract"
  grep -Fq "Inline default" "$scan_skill" || fail "$scan_skill missing inline-default execution rule"
  grep -Fq "Explicit agent opt-in only" "$scan_skill" || fail "$scan_skill missing explicit agent opt-in rule"
  grep -Fq "workflow-repair --auto" "$scan_skill" || fail "$scan_skill missing paired repair-side --auto compatibility note"
  grep -Fq "must not change scan output" "$scan_skill" || fail "$scan_skill missing scan-side schema stability note for repair-side --auto"
  grep -Fq "repair-side" "$scan_skill" || fail "$scan_skill missing explicit repair-side intake-assumption invariance note"
  grep -Fq "intake assumptions" "$scan_skill" || fail "$scan_skill missing explicit repair-side intake-assumption invariance note"
  grep -Fq "shared contract gate" "$scan_skill" || fail "$scan_skill missing explicit shared-contract-gate note for read-back validation"
  grep -Fq "matching \`workflow-repair\`" "$scan_skill" || fail "$scan_skill missing explicit reverse-direction coupled-update duty"
  grep -Fq "adaptation in the same change" "$scan_skill" || fail "$scan_skill missing explicit reverse-direction coupled-update duty"
  grep -Fq "including the literal \`--agent\` token in the request" "$scan_skill" || fail "$scan_skill missing literal --agent trigger rule"
  grep -Fq "using equivalent natural language such as" "$scan_skill" || fail "$scan_skill missing natural-language equivalent trigger rule"
  grep -Fq "scan deeper" "$scan_skill" || fail "$scan_skill missing speed/depth example"
  grep -Fq "do not by themselves enable helper-agent mode" "$scan_skill" || fail "$scan_skill missing explicit speed/depth-only inline rule"
  grep -Fq "Coordinator ownership is mandatory" "$scan_skill" || fail "$scan_skill missing coordinator ownership rule for agent mode"
  grep -Fq "Blocked / Agent Mode Unsupported" "$scan_skill" || fail "$scan_skill missing blocked behavior for unsupported agent mode"
  grep -Fq "Treat the current platform/session as agent-capable only when all of the" "$scan_skill" || fail "$scan_skill missing explicit agent-capable criteria"
  grep -Fq "helper-handoff-template.md" "$scan_skill" || fail "$scan_skill missing helper handoff template reference"
  grep -Fq "timed out, or fails outright" "$scan_skill" || fail "$scan_skill missing helper failure compensation rule"
  grep -Fq "If two helper handoffs conflict" "$scan_skill" || fail "$scan_skill missing helper conflict resolution rule"
  grep -Fq "recommended helper-count ceiling: 3 by default, 4 only" "$scan_skill" || fail "$scan_skill missing recommended helper-count ceiling"
  grep -Fq "Partial helper output may still be used as a lead for local re-check" "$scan_skill" || fail "$scan_skill missing partial-helper local follow-up rule"
  grep -Fq "This skill defines behavior only." "$scan_skill" || fail "$scan_skill missing behavior-only dispatch note"
  grep -Fq "platform-specific and may differ across executors" "$scan_skill" || fail "$scan_skill missing explicit platform-specific dispatch note"
  grep -Fq "minimum number of helper agents needed" "$scan_skill" || fail "$scan_skill missing bounded resource usage rule"
  grep -Fq "This rule applies to mode selection only" "$scan_skill" || fail "$scan_skill missing explicit scope boundary for no-silent-fallback rule"
  grep -Fq "Immediately read the file back and verify" "$scan_skill" || fail "$scan_skill missing explicit post-write verification step"
  grep -Fq "count and per-severity counts" "$scan_skill" || fail "$scan_skill missing count consistency validation"
  grep -Fq "snake_case" "$scan_skill" || fail "$scan_skill should explicitly guard against snake_case contract drift"
  grep -Fq "Repair classification is mandatory" "$scan_skill" || fail "$scan_skill missing mandatory repair-classification guard"
  grep -Fq "No complexity-only inflation" "$scan_skill" || fail "$scan_skill missing design-debt anti-inflation guard"
  grep -Fq "No evidence-gap inflation" "$scan_skill" || fail "$scan_skill missing evidence-gap anti-inflation guard"

  grep -Fq "\`document-type\` must be \`workflow-questions\`" "$repair_skill" || fail "$repair_skill missing repair-side intake requirement for document-type"
  grep -Fq "\`protocol\` must be \`workflow-scan-repair-v4\`" "$repair_skill" || fail "$repair_skill missing repair-side intake requirement for protocol"
  grep -Fq "Execution-mode agnostic intake" "$repair_skill" || fail "$repair_skill missing execution-mode agnostic intake rule"
  grep -Fq "\`--agent\`" "$repair_skill" || fail "$repair_skill missing explicit compatibility reference to --agent scan mode"
  grep -Fq "\`--auto\`" "$repair_skill" || fail "$repair_skill missing explicit --auto input contract"
  grep -Fq "No implied repair-side agent mode" "$repair_skill" || fail "$repair_skill missing no-implied-agent-mode clarification"
  grep -Fq "auto-follow-through" "$repair_skill" || fail "$repair_skill missing explicit auto follow-through mode"
  grep -Fq "reply \`ok\` exactly once" "$repair_skill" || fail "$repair_skill missing bounded commit-confirmation rule for --auto"
  grep -Fq "trellis-finish-work" "$repair_skill" || fail "$repair_skill missing finish-work command surface example for --auto"
  grep -Fq "request also includes \`--agent\`" "$repair_skill" || fail "$repair_skill missing explicit no-interaction rule for --auto with --agent"
  grep -Fq "authorization mode stays \`analysis-only\`" "$repair_skill" || fail "$repair_skill missing explicit no-effect rule for --auto under analysis-only rejection"
  grep -Fq "post-plan-confirmation" "$repair_skill" || fail "$repair_skill missing explicit post-plan-confirmation authorization state"
  grep -Fq "total-succeeded = 0" "$repair_skill" || fail "$repair_skill missing zero-success blocker rule for --auto"
  grep -Fq "total-attempted" "$repair_skill" || fail "$repair_skill missing explicit total-attempted recording rule"
  grep -Fq "Auto Follow-Through Outcome" "$repair_skill" || fail "$repair_skill missing continuation outcome logging rule"
  grep -Fq "update the repair log with the final" "$repair_skill" || fail "$repair_skill missing post-step-12 repair-log update step"
  grep -Fq "\`Auto Follow-Through Outcome\` value" "$repair_skill" || fail "$repair_skill missing explicit final continuation outcome update rule"
  grep -Fq "stop the close-out flow" "$repair_skill" || fail "$repair_skill missing explicit distinction between stopping close-out and final reporting"
  grep -Fq "Phase B" "$repair_skill" || fail "$repair_skill missing explicit record-and-report phase for Step 12"
  grep -Fq "total-blocked + total-manual-decision > 0" "$repair_skill" || fail "$repair_skill missing partial-accept unresolved-items rule"
  grep -Fq "yes/confirm style response" "$repair_skill" || fail "$repair_skill missing commit-confirmation recognition guidance"
  grep -Fq "never transitioned past" "$repair_skill" || fail "$repair_skill missing explicit scope note for the analysis-only no-op rule"
  grep -Fq "one-shot" "$repair_skill" || fail "$repair_skill missing explicit unreliable-identification guard for commit confirmation"
  grep -Fq "commit-confirmation identification is unreliable" "$repair_skill" || fail "$repair_skill missing explicit blocked behavior for unreliable commit-confirmation identification"
  grep -Fq "If any other interactive prompt appears" "$repair_skill" || fail "$repair_skill missing explicit stop rule for non-commit prompts"
  grep -Fq "If no Trellis finish-work command surface is available" "$repair_skill" || fail "$repair_skill missing explicit blocked behavior without finish-work command surface"
  grep -Fq "same-session skill surface available in the current project/runtime" "$repair_skill" || fail "$repair_skill missing command-to-skill fallback priority rule"
  grep -Fq "same-session \`trellis-continue\` skill surface available" "$repair_skill" || fail "$repair_skill missing explicit continue skill-surface fallback rule"
  grep -Fq "same-session \`trellis-finish-work\` skill surface available" "$repair_skill" || fail "$repair_skill missing explicit finish-work skill-surface fallback rule"
  grep -Fq "If no Trellis \`continue\` surface is available" "$repair_skill" || fail "$repair_skill missing explicit blocked behavior without continue surface"
  grep -Fq "Start that re-entry with the available" "$repair_skill" || fail "$repair_skill missing explicit continue-first close-out loop rule"
  grep -Fq "After a successful commit for the current repair task, return to the" "$repair_skill" || fail "$repair_skill missing explicit post-commit continue-loop rule"
  grep -Fq "reached-task-close" "$repair_skill" || fail "$repair_skill missing explicit continue-closes-task success outcome"
  grep -Fq "5 consecutive \`continue\` re-entries" "$repair_skill" || fail "$repair_skill missing bounded continue-loop ceiling"
  grep -Fq "tests/28-auto-stops-on-continue-loop-limit.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for continue-loop ceiling"
  grep -Fq "tests/29-auto-mixed-surface-availability.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for mixed-surface availability"
  grep -Fq "tests/30-auto-stops-on-unreliable-commit-confirmation.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for unreliable commit-confirmation identification"
  grep -Fq "tests/31-auto-continue-closes-task-before-commit.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for first-continue task closure"
  grep -Fq "tests/32-auto-mixed-surface-availability-reversed.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for reversed mixed-surface availability"
  grep -Fq "tests/33-auto-close-out-not-ready-or-safe.md" "$repair_skill" || fail "$repair_skill missing persisted scenario declaration for unsafe close-out readiness"
  grep -Fq "interrupted: session-did-not-complete" "$repair_skill" || fail "$repair_skill missing stale-pending continuation recovery rule"
  grep -Fq "latest" "$repair_skill" || fail "$repair_skill missing explicit resume-detection source for stale pending recovery"
  grep -Fq "repair log still shows" "$repair_skill" || fail "$repair_skill missing explicit pending-log signal for resumed-run detection"
  grep -Fq "repair-timestamp" "$repair_skill" || fail "$repair_skill missing explicit timestamp-based latest-log rule"
  grep -Fq "\`git commit\` itself fails mechanically" "$repair_skill" || fail "$repair_skill missing explicit commit-failure handling rule during auto follow-through"
  grep -Fq "target_focus" "$repair_skill" || fail "$repair_skill missing explicit target_focus scoping rule for auto close-out"
  grep -Fq "close-out safety decision" "$repair_skill" || fail "$repair_skill missing explicit target_focus scoping rule for auto close-out"
  grep -Fq "out-of-focus findings carry higher severity" "$repair_skill" || fail "$repair_skill missing explicit visibility rule for narrowed-scope auto close-out"
  grep -Fq "close-out cannot proceed safely" "$repair_skill" || fail "$repair_skill missing plan-stage blocker disclosure for auto follow-through"
  grep -Fq "sufficiently resolved for" "$repair_skill" || fail "$repair_skill missing explicit resolution test for blocked/manual-decision items"
  grep -Fq "repair-side agent interaction" "$repair_skill" || fail "$repair_skill missing explicit user-facing note when --agent is ignored"
  grep -Fq "\`--agent\` is not supported" "$repair_skill" || fail "$repair_skill missing explicit user-facing note when --agent is ignored"
  grep -Fq "stop after the" "$repair_skill" || fail "$repair_skill missing stop-after-summary rule for unsafe --auto close-out"
  grep -Fq "repair summary and report the blocker" "$repair_skill" || fail "$repair_skill missing blocker-report rule for unsafe --auto close-out"
  grep -Fq "instead of forcing completion" "$repair_skill" || fail "$repair_skill missing blocker escalation rule for unsafe --auto close-out"
  grep -Fq "Report Produced By \`workflow-scan --agent\`" "$repair_skill" || fail "$repair_skill missing example for --agent-produced report intake"
  grep -Fq "accepts validated reports produced by either inline \`workflow-scan\` runs or explicit \`workflow-scan --agent\` runs" "$repair_skill" || fail "$repair_skill missing compatibility note for inline and --agent scan reports"
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
  grep -Fq "Default repair-ready scope is narrow" "$repair_skill" || fail "$repair_skill missing confirmed-defect-only default gate"
  grep -Fq "Design debt is not auto-repair" "$repair_skill" || fail "$repair_skill missing design-debt default stop rule"
  grep -Fq "Evidence gaps block source edits" "$repair_skill" || fail "$repair_skill missing evidence-gap default stop rule"

  for template in \
    "$correction_plan_template" \
    "$repair_log_template" \
    "$closure_round_template" \
    "$issue_history_template"
  do
    grep -Fq "workflow-scan-repair-v4" "$template" || fail "$template missing shared protocol version"
  done
  grep -Fq "base-workflow-version:" "$closure_round_template" || fail "$closure_round_template missing base-workflow-version field"
  grep -Fq "round:" "$closure_round_template" || fail "$closure_round_template missing round field"
  grep -Fq "scenario-id" "$closure_round_template" || fail "$closure_round_template missing scenario-id field"
  grep -Fq "Issue Family ID" "$closure_round_template" || fail "$closure_round_template missing issue-family identifier field"
  grep -Fq "Round Outcome" "$closure_round_template" || fail "$closure_round_template missing round outcome section"
  grep -Fq "same-version" "$closure_round_template" || fail "$closure_round_template missing same-version boundary note"

  grep -Fq "{trellis-version from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing trellis-version placeholder from scan report"
  grep -Fq "{workflow-version from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing workflow-version placeholder from scan report"
  grep -Fq "{scan-timestamp from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing scan-timestamp placeholder from scan report"
  grep -Fq "{temp-project-root from WORKFLOW_QUESTIONS.md}" "$correction_plan_template" || fail "$correction_plan_template missing temp-project-root placeholder from scan report"
  grep -Fq "Report-side confirmed defects" "$correction_plan_template" || fail "$correction_plan_template missing report-side confirmed-defect summary"
  grep -Fq "Report-side design-debt items" "$correction_plan_template" || fail "$correction_plan_template missing report-side design-debt summary"
  grep -Fq "Report-side evidence-gap items" "$correction_plan_template" || fail "$correction_plan_template missing report-side evidence-gap summary"
  grep -Fq "**Report Classification**" "$correction_plan_template" || fail "$correction_plan_template missing report classification field"
  grep -Fq "Continuation Mode" "$correction_plan_template" || fail "$correction_plan_template missing continuation-mode header field"
  grep -Fq "execution-time source of truth" "$correction_plan_template" || fail "$correction_plan_template missing footer note redirecting execution-time mode to repair log"
  grep -Fq "narrowed" "$correction_plan_template" || fail "$correction_plan_template missing visibility note for narrowed-scope auto close-out"
  grep -Fq "auto-follow-through" "$correction_plan_template" || fail "$correction_plan_template missing auto-follow-through documentation"
  grep -Fq "stop and" "$correction_plan_template" || fail "$correction_plan_template missing explicit blocker disclosure for auto follow-through"
  grep -Fq "report a blocker" "$correction_plan_template" || fail "$correction_plan_template missing explicit blocker disclosure for auto follow-through"
  grep -Fq "If continuation mode = \`auto-follow-through\`" "$correction_plan_template" || fail "$correction_plan_template missing continuation-mode-scoped auto rule"
  grep -Fq "authorization mode at the time the" "$correction_plan_template" || fail "$correction_plan_template missing timing rule for authorization-mode header"
  grep -Fq "{absolute path to WORKFLOW_QUESTIONS.md}" "$repair_log_template" || fail "$repair_log_template missing source-report placeholder"
  grep -Fq "**Report Classification**" "$repair_log_template" || fail "$repair_log_template missing report classification field"
  grep -Fq "continuation-mode:" "$repair_log_template" || fail "$repair_log_template missing continuation-mode frontmatter"
  grep -Fq "total-reverted:" "$repair_log_template" || fail "$repair_log_template missing total-reverted counter"
  grep -Fq "Auto Follow-Through Outcome" "$repair_log_template" || fail "$repair_log_template missing structured continuation outcome field"
  grep -Fq "\`pending\` until the continuation result is known" "$repair_log_template" || fail "$repair_log_template missing pending-to-final continuation logging rule"
  grep -Fq "\`not-applicable\`" "$repair_log_template" || fail "$repair_log_template missing not-applicable rule for stop-after-summary mode"
  grep -Fq "interrupted: session-did-not-complete" "$repair_log_template" || fail "$repair_log_template missing interrupted continuation recovery state"
  grep -Fq "reached-task-close" "$repair_log_template" || fail "$repair_log_template missing explicit continuation outcome for normal task closure"
  grep -Fq "stopped-with-blocker: <brief reason> | interrupted: session-did-not-complete" "$repair_log_template" || fail "$repair_log_template missing single-line continuation outcome value set"
  grep -Fq "total-succeeded + total-failed + total-reverted" "$repair_log_template" || fail "$repair_log_template missing explicit total-attempted definition"
  grep -Fq "highest \`repair-timestamp\` value" "$repair_log_template" || fail "$repair_log_template missing explicit latest-log selection rule"
  grep -Fq "continuation-mode:" "$issue_history_template" || fail "$issue_history_template missing continuation-mode frontmatter"
  grep -Fq "Continuation Mode:" "$issue_history_template" || fail "$issue_history_template missing continuation mode session-summary field"
  grep -Fq "{absolute path to WORKFLOW_QUESTIONS.md}" "$issue_history_template" || fail "$issue_history_template missing report-path placeholder"
  grep -Fq "**Report Classification**" "$issue_history_template" || fail "$issue_history_template missing report classification field"
  grep -Fq "session-level header/summary fields" "$issue_history_template" || fail "$issue_history_template missing explicit session-level scoping for continuation mode"
  if [ "$(grep -Ec '^[0-9]+\. ' "$issue_history_template")" -ne "$(grep -Eo '^[0-9]+\.' "$issue_history_template" | sort -u | wc -l | tr -d ' ')" ]; then
    fail "$issue_history_template has duplicated numbered rules"
  fi

  grep -Fq "read-back validation" "$scan_spec" || fail "$scan_spec missing read-back validation contract"
  grep -Fq "read-back validation" "$repair_spec" || fail "$repair_spec missing paired read-back validation note"
  grep -Fq "read-back validation" "$skills_index" || fail "$skills_index missing paired contract read-back validation note"
  grep -Fq "\`--agent\`" "$scan_spec" || fail "$scan_spec missing explicit --agent mode contract"
  grep -Fq "execution-mode agnostic" "$repair_spec" || fail "$repair_spec missing execution-mode agnostic note"
  grep -Fq "post-plan-confirmation" "$repair_spec" || fail "$repair_spec missing explicit post-plan-confirmation spec note"
  grep -Fq "\`--agent\` assistance" "$skills_index" || fail "$skills_index missing paired execution-mode note"
  grep -Fq "helper failure/timeout/malformed-handoff compensated locally" "$scan_spec" || fail "$scan_spec missing helper failure scenario coverage note"
  grep -Fq "unresolved helper conflicts dropped conservatively instead of guessed through" "$scan_spec" || fail "$scan_spec missing unresolved helper conflict scenario coverage note"
  grep -Fq "partial helper output used only as a lead for local coordinator follow-up" "$scan_spec" || fail "$scan_spec missing partial-helper scenario coverage note"
  grep -Fq "speed/depth-only requests staying inline" "$scan_spec" || fail "$scan_spec missing speed/depth-only scenario coverage note"
  grep -Fq "main-session-only skill" "$repair_spec" || fail "$repair_spec missing repair-side no-agent clarification"
  grep -Fq "count fields match the actual number of findings" "$scan_spec" || fail "$scan_spec missing count consistency contract"
  grep -Fq "declared total/severity counts" "$repair_spec" || fail "$repair_spec missing repair-side count consistency contract"
  grep -Fq "total/severity count semantics" "$skills_index" || fail "$skills_index missing paired count consistency note"

  for test_file in \
    "skills/workflow-repair/tests/08-auto-follow-through-success.md" \
    "skills/workflow-repair/tests/09-auto-stops-on-zero-success.md" \
    "skills/workflow-repair/tests/10-auto-no-effect-under-analysis-only.md" \
    "skills/workflow-repair/tests/11-auto-stops-on-unexpected-prompt.md" \
    "skills/workflow-repair/tests/12-auto-blocked-without-finish-work-surface.md" \
    "skills/workflow-repair/tests/13-post-plan-confirmation-mode.md" \
    "skills/workflow-repair/tests/14-post-plan-confirmation-with-auto.md" \
    "skills/workflow-repair/tests/15-partial-accept-with-documented-blockers.md" \
    "skills/workflow-repair/tests/16-interrupted-pending-recovery.md" \
    "skills/workflow-repair/tests/17-commit-succeeds-but-finish-work-fails.md" \
    "skills/workflow-repair/tests/18-auto-zero-findings.md" \
    "skills/workflow-repair/tests/19-git-commit-fails-during-auto.md" \
    "skills/workflow-repair/tests/20-auto-with-preexisting-active-task.md" \
    "skills/workflow-repair/tests/21-auto-all-findings-ignored.md" \
    "skills/workflow-repair/tests/22-authorized-to-repair-partial-accept-with-auto.md" \
    "skills/workflow-repair/tests/23-target-focus-with-out-of-focus-high-severity.md" \
    "skills/workflow-repair/tests/24-auto-mixed-success-and-reverted.md" \
    "skills/workflow-repair/tests/25-auto-falls-back-to-skill-surfaces.md" \
    "skills/workflow-repair/tests/26-auto-stops-when-continue-surface-missing.md" \
    "skills/workflow-repair/tests/27-auto-continue-closes-task.md" \
    "skills/workflow-repair/tests/28-auto-stops-on-continue-loop-limit.md" \
    "skills/workflow-repair/tests/29-auto-mixed-surface-availability.md" \
    "skills/workflow-repair/tests/30-auto-stops-on-unreliable-commit-confirmation.md" \
    "skills/workflow-repair/tests/31-auto-continue-closes-task-before-commit.md" \
    "skills/workflow-repair/tests/32-auto-mixed-surface-availability-reversed.md" \
    "skills/workflow-repair/tests/33-auto-close-out-not-ready-or-safe.md" \
    "skills/workflow-repair/tests/55-stale-scan-report-blocked.md" \
    "skills/workflow-repair/tests/56-invalid-embedded-state-schema-mismatch.md" \
    "skills/workflow-repair/tests/57-closure-unresolved-in-scope-blocks-closeout.md" \
    "skills/workflow-repair/tests/58-closure-new-family-stops-auto-progression.md"
  do
    [ -f "$test_file" ] || fail "missing $test_file"
    grep -Fq "## Purpose" "$test_file" || fail "$test_file missing Purpose section"
    grep -Fq "## Input" "$test_file" || fail "$test_file missing Input section"
    grep -Fq "## Expected Mode" "$test_file" || fail "$test_file missing Expected Mode section"
    grep -Fq "## Expected Key Behaviors" "$test_file" || fail "$test_file missing Expected Key Behaviors section"
    grep -Fq "## Must Not" "$test_file" || fail "$test_file missing Must Not section"
  done
}

validate_workflow_scan_repair_contract

echo "OK: validated $found skill(s) + spec cross-check passed"

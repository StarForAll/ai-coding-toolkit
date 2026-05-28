# workflow-scan Skill Assessment

## Question

Determine whether the two false positives in
`/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` were caused by the
`workflow-scan` skill contract or by model execution.

## Findings

### WS-001: `.codex/skills/` Empty

**Cause**: model execution error, not a missing skill rule.

Evidence:

- `skills/workflow-scan/SKILL.md` already contains rule 26, which says
  `.agents/skills/*/SKILL.md` is the shared workflow primary carrier and
  `.codex/skills/*/SKILL.md` is only secondary.
- `skills/workflow-scan/references/scan-output-template.md` already says an
  empty `.codex/skills/` directory, or missing shared workflow skills there,
  is not a finding by itself.
- `skills/workflow-scan/tests/14-codex-secondary-skills-empty-is-not-finding.md`
  already covers the exact scenario where the install record lists patched
  Codex skills, `.agents/skills/` contains active carriers, and
  `.codex/skills/` is empty.

Conclusion: the scanner/model failed to follow existing workflow-scan
instructions. No additional WS-001 rule was required.

### WS-002: `finish-work-checklist.md` vs Template

**Cause**: skill contract gap.

Evidence:

- Before this repair, `workflow-scan` had general document-reference checks but
  no explicit rule distinguishing installed shared templates from task-local
  runtime evidence files.
- The temp project correctly contains
  `.trellis/workflow-docs/finish-work-checklist-template.md`.
- The generated `finish-work-checklist.md` is expected only after a task reaches
  delivery / finish-work close-out readiness.

Conclusion: the skill needed a false-positive guard so scan output does not
classify a missing task-local runtime file as a post-install defect in a fresh
temp project.

## Changes Applied

- Added `workflow-scan` rule v3.9 for installed templates vs task-local runtime
  evidence files.
- Updated the shared scan output template with the same classification rule.
- Updated `.trellis/spec/skills/workflow-scan.md` so repo-local skill spec stays
  aligned with the installable skill.
- Added prompt-level scenario test
  `skills/workflow-scan/tests/17-finish-work-checklist-template-is-not-missing-runtime-file.md`.

## Verification

- `./scripts/validate-skills.sh` passed:
  `OK: validated 28 skill(s) + spec cross-check passed`.

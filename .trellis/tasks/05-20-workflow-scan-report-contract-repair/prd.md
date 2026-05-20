# PRD

## Goal

Repair the `workflow-scan` report contract flow so `WORKFLOW_QUESTIONS.md`
output is forced to match the shared `workflow-scan-repair-v2` schema instead
of loosely "following the template" and drifting into incompatible field names
or section structure.

## What I already know

* A live report at `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md` failed
  `workflow-repair` intake because it omitted `document-type:
  workflow-questions` and used snake_case fields such as `generated_at`,
  `trellis_version`, `temp_project_path`, and `total_findings`.
* The shared template at
  `skills/workflow-scan/references/scan-output-template.md` already defines the
  correct frontmatter contract: `document-type`, `protocol`,
  `trellis-version`, `workflow-version`, `workflow-schema-version`,
  `scan-timestamp`, `temp-project-root`, `total-findings`, `p0-count`,
  `p1-count`, `p2-count`.
* `skills/workflow-scan/SKILL.md` currently tells the AI to "write the
  document using the format from references/scan-output-template.md", but it
  does not require a post-write field-by-field validation pass.
* `skills/workflow-repair/SKILL.md` correctly requires the repair-side intake to
  stop when `document-type: workflow-questions` is missing.
* Current repo validation for skills (`scripts/validate-skills.sh`) checks
  frontmatter presence and cross-surface references/tests, but it does not
  statically validate this paired scan/repair report contract.

## Root Cause

The contract failure is not in the shared template itself. The failure mode is
that `workflow-scan` relies on a natural-language instruction to "use the
template" without requiring a deterministic read-back validation step.

That leaves the AI free to regress into common YAML/report habits:

* snake_case keys instead of the paired kebab-case contract
* missing fixed keys such as `document-type`
* ad-hoc summary headings instead of the required summary sections

Because there is no repo-level executable check for this paired contract, that
drift can ship silently until `workflow-repair` blocks on the generated report.

## Requirements

* `workflow-scan` must require a post-write validation pass against the shared
  template before reporting success.
* That validation guidance must explicitly name the required frontmatter keys
  and summary sections, not only refer to the template abstractly.
* The paired `workflow-repair` / spec docs must stay aligned with the stronger
  scan-side validation expectation.
* Repo-local validation must gain an executable check for the
  `workflow-scan-repair` coupled contract so future drift is caught before a
  temp-project run.

## Acceptance Criteria

* [ ] `skills/workflow-scan/SKILL.md` includes a mandatory read-back validation
      step for `WORKFLOW_QUESTIONS.md`.
* [ ] The scan skill now explicitly names the required frontmatter keys and
      required summary/findings structure it must verify.
* [ ] Paired contract/spec wording remains aligned across:
      `skills/workflow-scan/SKILL.md`,
      `skills/workflow-repair/SKILL.md`,
      `skills/workflow-scan/references/scan-output-template.md`,
      `.trellis/spec/skills/index.md`,
      `.trellis/spec/skills/workflow-scan.md`,
      `.trellis/spec/skills/workflow-repair.md`.
* [ ] `scripts/validate-skills.sh` enforces the critical shared contract checks
      for the workflow-scan/workflow-repair pair.
* [ ] `./scripts/validate-skills.sh` passes after the change.

## Out Of Scope

* Re-running `workflow-scan` against a temp project in this task.
* Fixing any actual workflow product defect under
  `docs/workflows/新项目开发工作流/`.
* Redesigning the broader workflow-scan/workflow-repair process beyond the
  contract-hardening needed for this regression.

## Technical Notes

* Relevant files inspected:
  * `skills/workflow-scan/SKILL.md`
  * `skills/workflow-repair/SKILL.md`
  * `skills/workflow-scan/references/scan-output-template.md`
  * `.trellis/spec/skills/index.md`
  * `.trellis/spec/skills/workflow-scan.md`
  * `.trellis/spec/skills/workflow-repair.md`
  * `scripts/validate-skills.sh`
* Primary validation command:
  * `./scripts/validate-skills.sh`

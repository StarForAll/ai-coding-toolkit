# Create Workflow Scan And Repair Skills

## Goal

Create and validate two installable skills under `skills/` that support a fixed two-stage workflow for the embedded workflow product at `docs/workflows/新项目开发工作流/`: one skill runs inside a Trellis temp project to analyze the installed workflow and write `WORKFLOW_QUESTIONS.md`; the other runs in the source repository to consume that report, re-verify findings against the temp project and source workflow, and safely repair only `docs/workflows/新项目开发工作流/`.

## What I Already Know

- The user requires a temp project to be created via `commands/shell/init-trellis-temp-project.sh`.
- The temp project root is version-derived from `trellis -v` and follows `/tmp/trellis-{VERSION}-2`.
- The first skill must support analysis in the temp project and produce `WORKFLOW_QUESTIONS.md` in that temp project.
- The second skill must support analysis and repair in the current source repository using the report from the temp project.
- Repair scope is restricted to `docs/workflows/新项目开发工作流/`; other directories must not be modified, except task-local artifacts if needed.
- The user explicitly does not want agents used inside the actual workflow analysis/repair prompts.
- Existing untracked drafts already exist at `skills/workflow-scan/` and `skills/workflow-repair/`.
- `.trellis/spec/skills/index.md` already references `workflow-scan.md` and `workflow-repair.md`, but those spec files do not exist yet.

## Requirements

- Provide `skills/workflow-scan/` as the temp-project analysis skill.
- Provide `skills/workflow-repair/` as the source-project repair skill.
- Make the two skills form a clear paired contract around `WORKFLOW_QUESTIONS.md`.
- Encode the exact scenario meaning so an AI CLI using either skill can understand:
  - the temp project is created from `trellis init` plus workflow embed
  - the analysis target is the embedded workflow in the temp project, not the source repo runtime
  - the repair target is the source workflow under `docs/workflows/新项目开发工作流/`
  - `trellis-native` problems must be patched from within the workflow so later installs can fix them
  - repeated historical failures imply broad variant checking, not only one explicit finding
- Ensure the scan skill writes a structured report named exactly `WORKFLOW_QUESTIONS.md`.
- Ensure the repair skill consumes that report, re-verifies findings, and only fixes real issues.
- Ensure the repair skill explicitly guards against introducing new issues.
- Ensure the repair skill makes clear that similar issues should be searched for and fixed together when safe.
- Ensure both skills follow repository skill conventions and validation expectations.
- Ensure the final result can answer whether the two new skills in `git status` are compliant and fit-for-purpose.

## Acceptance Criteria

- [ ] `skills/workflow-scan/SKILL.md` clearly defines the temp-project analysis workflow, path resolution, report contract, boundaries, and output summary behavior.
- [ ] `skills/workflow-repair/SKILL.md` clearly defines report intake, source-vs-temp verification, correction planning, confirmation, safe repair, and verification behavior.
- [ ] Shared report contract documentation exists and matches both skills.
- [ ] Any missing repository spec artifacts needed for these new skills are added and aligned with the skill pair.
- [ ] `./scripts/validate-skills.sh` passes.
- [ ] A repo validation check shows no protocol drift between the paired skill docs and their reference templates.
- [ ] Final review can truthfully state whether the two skills satisfy the requested scenario and identify any residual risk.

## Technical Approach

- Treat `workflow-scan` and `workflow-repair` as a coupled skill pair, similar to the existing paired-skill pattern already used elsewhere in the repository.
- Reconcile the current drafts against the user's scenario details, especially:
  - no-agent execution expectations inside the embedded workflow prompts
  - explicit use of `commands/shell/init-trellis-temp-project.sh`
  - dynamic temp-project version/path resolution
  - repeated-issue / variant-fix expectations
  - source-repair scope lock to `docs/workflows/新项目开发工作流/`
- Add missing spec supplements under `.trellis/spec/skills/` if required by the repository's own skill index and validation expectations.
- Validate with the repo skill validator and targeted content review.

## Out Of Scope

- Actually running the workflow scan or repair process against a live temp project as part of this implementation task
- Fixing real workflow product defects under `docs/workflows/新项目开发工作流/`
- Changing unrelated repository skill surfaces

## Technical Notes

- Relevant files inspected:
  - `commands/shell/init-trellis-temp-project.sh`
  - `skills/workflow-scan/SKILL.md`
  - `skills/workflow-repair/SKILL.md`
  - `skills/workflow-scan/references/scan-output-template.md`
  - `skills/workflow-repair/references/correction-plan-template.md`
  - `skills/workflow-repair/references/repair-log-template.md`
  - `.trellis/spec/skills/index.md`
  - `scripts/validate-skills.sh`
- Key repo constraint: spec index references to missing supplement files are themselves a documentation drift risk.

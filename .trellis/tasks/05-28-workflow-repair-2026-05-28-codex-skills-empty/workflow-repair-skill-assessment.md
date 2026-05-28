# workflow-repair Skill Assessment

## Question

Strengthen `workflow-repair` so it does not blindly adopt scan findings before
checking whether the reported issue truly exists in the relevant files.

## Assessment

`workflow-repair` already had a strong general rule: reports are evidence, not
truth, and every finding must be rechecked against the temp project and source
workflow before repair. It also already covered the Codex secondary-skill false
positive:

- `skills/workflow-repair/tests/68-codex-secondary-skills-empty-defaults-to-ignored.md`
  requires empty `.codex/skills/` findings to resolve to `ignored` when
  `.agents/skills/` is the shared primary carrier.

The gap was narrower:

- document-reference / post-install-artifact findings did not explicitly require
  content-level file analysis before adoption
- `workflow-repair` did not explicitly name the installed-template vs
  task-local-runtime-file false-positive pattern

## Changes Applied

- Added `workflow-repair` v3.9 guidance requiring content-level verification
  for document-reference and post-install-artifact findings before adoption.
- Added a default-ignore rule for installed shared templates versus later-
  generated task-local runtime evidence files, including
  `finish-work-checklist-template.md` vs `finish-work-checklist.md`.
- Updated `.trellis/spec/skills/workflow-repair.md` with the same repair-side
  contract.
- Added prompt-level scenario test
  `skills/workflow-repair/tests/71-finish-work-checklist-template-defaults-to-ignored.md`.

## Verification

- `./scripts/validate-skills.sh` passed:
  `OK: validated 28 skill(s) + spec cross-check passed`.
- `git diff --check` passed with no output.

# 10 Final Compatibility Promotion Is Mandatory

## Purpose

Verify that `workflow-capability-audit` **mandates** writing the exact `trellis -v` output into `COMPATIBLE_TRELLIS_VERSION` after a confirmed successful audit conclusion.

## Input

User input:

> The audit is complete and the workflow looks compatible. Finish the compatibility audit and update the compatibility anchor for me if needed.

## Expected Mode

Confirmed-audit completion with mandatory `COMPATIBLE_TRELLIS_VERSION` write-back into `workflow_assets.py`.

## Expected Key Behaviors

- finish the audit conclusion normally
- write the exact `trellis -v` output value into `COMPATIBLE_TRELLIS_VERSION` in `workflow_assets.py` as a mandatory post-audit step
- preserve the literal version string from `trellis -v`, including any prerelease suffix (e.g., `-rc.3`, `-beta.1`)
- apply this rule even when the workflow was already compatible as-is or no additional source edits are needed

## Must Not

- must not write a rounded-up stable version (e.g., `"0.5.0"`) when `trellis -v` returns a prerelease version (`"0.5.0-rc.3"`)
- must not skip the version write-back and treat it as a separate follow-up step
- must not defer the promotion to a later implementation step

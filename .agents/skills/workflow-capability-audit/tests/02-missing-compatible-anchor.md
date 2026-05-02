# 02 Missing Compatible Anchor

## Purpose

Verify that `workflow-capability-audit` stops when `COMPATIBLE_TRELLIS_VERSION` is missing, asks the user to supply it, and treats writing that value into `workflow_assets.py` as the sole allowed pre-audit source edit exception.

## Input

User input:

> Run the Trellis capability compatibility audit for `docs/workflows/新项目开发工作流/`.

## Expected Mode

Version-gate stop waiting for user-supplied anchor value.

## Expected Key Behaviors

- detect missing `COMPATIBLE_TRELLIS_VERSION`
- stop before task creation
- emit the version-gate stop template with `Gate Result = missing-compatible-anchor`
- ask the user to provide the missing value
- after the user provides it, allow only one pre-audit source edit:
  - write the supplied value into `workflow_assets.py`
- rerun version gating before any other audit action

## Must Not

- must not auto-bootstrap into full audit with no anchor
- must not create A/B fixtures before the anchor exists
- must not perform any other source edit before audit conclusion

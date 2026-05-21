# Workflow Repair PRD

## Goal

Consume `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`, verify each finding
against the temp project and current workflow source, and apply only the safe
workflow-local repairs under `docs/workflows/新项目开发工作流/`.

## In Scope

- Re-check all 9 reported findings
- Apply safe fixes for:
  - patch helper `--help` / CLI consistency
  - AGENTS NL routing legacy `/trellis:start` prompt drift
  - `patch-workflow-phase.py` docstring loss
- Write repair artifacts for this run

## Out of Scope

- Re-introducing workflow overlays for Trellis native agents
- Renaming upstream / external `trellis-spec-bootstarp` carriers
- Auto close-out (`--auto` was not requested)

## Acceptance Anchors

- Safe repairs stay inside the workflow directory
- Relevant regression tests pass
- Repair log and issue history are written

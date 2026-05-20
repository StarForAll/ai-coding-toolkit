# 01 Inline Default No Agents

## Purpose

Verify that `workflow-scan` stays inline in the current CLI session when the
user does not explicitly provide `--agent`.

## Input

User input:

> Run `/workflow-scan` against the current Trellis temp project and generate `WORKFLOW_QUESTIONS.md`.

## Expected Mode

Inline scan in the current CLI session.

## Expected Key Behaviors

- resolve the temp project and scan mode without enabling helper agents
- perform the workflow surface inventory and verification inline
- keep final finding judgment, report writing, and read-back validation in the
  current session
- emit the normal `WORKFLOW_QUESTIONS.md` contract if the scan succeeds

## Must Not

- must not infer agent-assisted mode from product family, environment hints, or
  performance preference alone
- must not dispatch helper agents when `--agent` is absent
- must not treat inline execution as a degraded fallback that needs apology or
  reclassification

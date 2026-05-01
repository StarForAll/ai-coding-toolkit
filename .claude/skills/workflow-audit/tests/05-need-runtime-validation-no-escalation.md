# 05 need_runtime_validation no Escalation

## Purpose

Verify that `workflow-audit` does NOT silently skip runtime validation when the user set `need_runtime_validation: no` but A/B/C findings conclusively demonstrate that Step D is necessary. The skill must output a Needs Confirmation block explaining the conflict and let the user decide.

## Input

User input:

> Check `docs/workflows/新项目开发工作流/` for issues. I've audited most of it before, so keep it static — no `/tmp` validation needed.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues: []
need_runtime_validation: no
force_full_brainstorm: no
```

However, during Step A/B/C, the skill discovers that the workflow's embed scripts reference non-existent paths and the install state machine has structural gaps that can only be confirmed by running `trellis init` + embed chain.

## Expected Mode

The skill should NOT silently enter lightweight static mode. It must output a Needs Confirmation escalation before proceeding.

## Expected Key Behaviors

- execute evidence mainline steps A (understand mechanics), B (static evidence), and C (gap analysis)
- during Step C: identify issues that conclusively require runtime validation to confirm or refute
- recognize the conflict: user set `need_runtime_validation: no` but D trigger conditions are met
- do NOT silently skip D and enter lightweight static mode
- do NOT unilaterally proceed to D without user consent
- output a Needs Confirmation block that includes:
  - what was found in A/B/C that makes D necessary
  - why static analysis alone is insufficient for these specific findings
  - a clear statement that the user's `need_runtime_validation: no` conflicts with the evidence
  - a request for the user to decide: override and proceed with D, or accept lightweight mode with the gap noted as Evidence Gap
- stop and wait for user response before continuing

## Must Not

- must not silently skip D and output lightweight findings as if nothing is wrong
- must not proceed to D (`/tmp`, `trellis init`, embed chain) without explicit user confirmation
- must not discard A/B/C findings that indicate D is needed
- must not treat `need_runtime_validation: no` as an unconditional gate that overrides all evidence
- must not output a final confirmed-issue conclusion for findings that require D to confirm

# 04 Helper Failure Local Compensation

## Purpose

Verify that helper failure, timeout, malformed handoff, or conflicting helper
claims do not automatically fail the scan and instead return authority to the
coordinator.

## Input

User input:

> Run `/workflow-scan --agent`. One helper times out, and another helper returns a malformed or conflicting handoff for its assigned slice.

## Expected Mode

Agent-assisted scan with coordinator-side local compensation.

## Expected Key Behaviors

- treat failed, partial, malformed, or conflicting helper output as
  non-authoritative
- re-check the affected slice locally in the coordinator session or skip the
  slice conservatively if no safe claim can be made
- resolve helper conflicts from temp-project evidence before carrying any claim
  into final findings
- keep the final `WORKFLOW_QUESTIONS.md` contract valid if the coordinator can
  still complete the scan safely

## Must Not

- must not copy malformed helper output directly into final findings
- must not let helper timeout or crash by itself become a workflow finding
- must not fail the whole scan solely because one helper handoff was unusable
  when the coordinator can safely compensate locally

# 06 Partial Helper Output Local Follow-up

## Purpose

Verify that partial helper output may guide the coordinator's local follow-up
without being promoted directly into final findings.

## Input

User input:

> Run `/workflow-scan --agent`. Three helper agents are used. One returns a complete handoff, one returns `Status: partial` with useful relative paths and candidate issues, and one returns no relevant findings.

## Expected Mode

Agent-assisted scan with coordinator-side local follow-up for partial helper
output.

## Expected Key Behaviors

- treat the partial handoff as a lead for coordinator-side local re-check
- use the partial handoff's paths and candidate issues to guide local evidence
  collection
- require local temp-project confirmation before any partial-helper claim enters
  final findings
- continue the scan without treating partial status itself as either success or
  failure of the whole run

## Must Not

- must not copy a partial helper claim directly into final findings
- must not treat `Status: partial` as equivalent to a complete validated helper
  result
- must not discard useful partial leads when they can safely guide local
  coordinator follow-up

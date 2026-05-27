# workflow-repair-2026-05-27-codex-start-routing

## Goal

Consume `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`, re-verify each reported
finding against the temp project and source workflow, and repair only safe,
same-version defects within `docs/workflows/新项目开发工作流/`.

## Scope

- Source report protocol must remain `workflow-scan-repair-v4`
- Version gate must stay aligned at `trellis 0.5.17` and workflow
  `0.1.2801 / schema 3`
- Allowed source edits are limited to `docs/workflows/新项目开发工作流/`
- Task artifacts may be written under this task directory
- Optional audit shadow under `tmp/workflow-issues/` is allowed but not required

## Findings To Re-Verify

1. WS-001: Codex `trellis-start` quick reference misroutes implementation and
   formal check intents
2. WS-002: Claude strong-gate subagent hook soft-allows a forbidden dispatch
3. WS-003: Mirrored brainstorm skills contain broken placeholder links

## Execution Rules

- Re-check every finding against both the temp project and source workflow
- Keep non-confirmed findings at `ignored`, `blocked`, or `manual-decision`
- Run same-pattern variant sweep only within
  `docs/workflows/新项目开发工作流/`
- Update all must-update contract surfaces in the same repair batch when safe
- Record the correction plan inline before source edits
- Write `workflow-repair-log.md` and `closure-round-<N>.md` after execution

## Acceptance Criteria

- Every report finding receives one decision state with evidence
- Any applied fix is minimal, source-scoped, and verified
- Post-repair checks cover syntax, cross-reference, workflow-assets consistency,
  variant sweep, contract-surface coverage, and repeat-trigger search
- Closure verification produces at least one round artifact and does not leave
  unresolved in-scope findings

# workflow-audit: 新项目开发工作流

## Goal

Run a focused `workflow-audit` preparation flow for
`docs/workflows/新项目开发工作流/`, starting from the repeated repair-lineage
evidence already accumulated, so the next audit execution can verify whether
the workflow has deeper maintenance, contract, or closure problems.

## What I already know

- The workflow root under audit is fixed:
  `docs/workflows/新项目开发工作流/`.
- `workflow-audit` is a same-version maintenance audit, not a version-drift
  audit.
- Current version gate passes:
  `COMPATIBLE_TRELLIS_VERSION = 0.5.17`, `trellis -v = 0.5.17`.
- In Codex, `workflow-audit` may perform A/B/C static stages in the main
  session, but if Step D reaches formal embed execution it must stop and hand
  off to a main interactive Claude Code or OpenCode session.
- The repeated repair lineage uses the same source report path:
  `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`.
- The latest lineage history includes multiple repair logs on 2026-05-27 plus
  earlier same-lineage repair logs from 2026-05-20 and 2026-05-21.

## Assumptions (temporary)

- The next useful action is an audit-oriented investigation, not another
- ordinary `workflow-repair` batch.
- The latest five repair rounds are a sufficient seed set for bootstrapping the
  audit task, while older same-lineage logs remain available as extended
  context.

## Open Questions

- Which subset of the broader same-lineage history should count as the primary
  five-round evidence bundle for the next audit pass?
- Does the later audit need Step D runtime validation, or will A/B/C static
  evidence already prove the main defect class?

## Requirements (evolving)

- Preserve the current suitability judgment for `workflow-audit`.
- Persist the latest five same-lineage repair rounds with timestamps, protocols,
  counts, and closure status.
- Record the larger same-lineage context so later audit work can expand beyond
  the initial five-round bundle when needed.
- Keep the Codex handoff boundary explicit so the audit is not mis-scoped as an
  end-to-end Codex-only run.

## Acceptance Criteria (evolving)

- [ ] `audit-report.md` exists and records the audit boundary and current
      evidence state
- [ ] `research/lineage-evidence-summary.md` exists with the latest five repair
      rounds and broader lineage notes
- [ ] The task is ready for a later `workflow-audit` A/B/C run without relying
      on chat memory

## Definition of Done (team quality bar)

- Evidence files point to real task/archive paths
- No version-gate or CLI-boundary claim is left unreferenced
- The task clearly states what remains to be validated before any final audit
  conclusion

## Out of Scope (explicit)

- Executing the full runtime embed chain in this preparation step
- Applying ordinary `workflow-repair` fixes directly from this task
- Declaring final confirmed workflow defects before the actual audit run

## Technical Notes

- Primary behavior source: `.trellis/spec/skills/workflow-audit.md`
- Live shared skill surface: `.agents/skills/workflow-audit/SKILL.md`
- Claude-local deployed copy: `.claude/skills/workflow-audit/SKILL.md`
- Version anchor: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`

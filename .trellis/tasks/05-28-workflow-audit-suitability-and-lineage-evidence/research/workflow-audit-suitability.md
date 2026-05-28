# workflow-audit suitability notes

## Summary

`workflow-audit` is usable for the current situation, with one important
execution boundary: in a Codex main session it can complete static evidence
gathering and mode selection, but if runtime validation reaches the formal
embed step, it must stop and hand off to a main interactive Claude Code or
OpenCode session.

## Evidence

### Version gate

- Source: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Observed `COMPATIBLE_TRELLIS_VERSION`: `0.5.17`
- Runtime `trellis -v`: `0.5.17`
- Result: exact match, so the same-version gate does not block `workflow-audit`

### Behavioral source of truth

- Live skill says `.trellis/spec/skills/workflow-audit.md` is the behavioral
  source of truth if any conflict exists.
- The spec and live skill are materially aligned for the current decision:
  same-version maintenance audit, supported surface limited to Claude Code /
  OpenCode / Codex, and Codex handoff at the formal embed boundary.

### Codex execution boundary

- `workflow-audit` runs in the invoking CLI main session.
- Agent/sub-agent execution is not allowed for this skill.
- Under Codex, the skill must stop before the first formal embed execution and
  emit a handoff to Claude Code or OpenCode if runtime validation requires it.

### Why it fits the current loop

- The current problem is repeated scan/repair non-convergence across the same
  lineage rather than a normal one-off repair.
- `workflow-audit` is the repo-local skill intended to verify whether workflow
  issues are real before further source edits and to audit install/embed and
  CLI adaptation boundaries.
- This matches the user's need to decide whether the workflow itself has a
  deeper maintenance or closure problem.

## Caveat

Suitability here does not mean Codex can perform the entire runtime audit
alone. It means `workflow-audit` is the correct next audit surface, provided
the task records the expected Codex handoff boundary when Step D becomes
necessary.

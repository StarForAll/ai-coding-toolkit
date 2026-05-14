# workflow-audit agent-boundary tightening

## Goal

Tighten the `workflow-audit` execution contract so that, at the current stage,
the skill must not use Claude Code or OpenCode agents for audit execution or
Codex handoff continuation. Keep the existing workflow-audit scope and
evidence-first audit semantics intact while making the non-agent takeover rule
explicit in the spec, skill surfaces, references, and tests.

## What I already know

- The user explicitly stated that using agents is not appropriate at this stage
  because it is too time-consuming, in both OpenCode and Claude Code.
- The current `workflow-audit` contract requires a Codex handoff to Claude Code
  or OpenCode when formal embed execution is reached.
- The current contract does not clearly say that the takeover must happen in a
  main interactive CLI session rather than via another CLI's agent mechanism.
- The skill has coupled behavior surfaces in `.trellis/spec/skills/`,
  `.agents/skills/workflow-audit/`, and `.claude/skills/workflow-audit/`.

## Assumptions (temporary)

- The user wants to close only the agent-based execution path for this skill,
  not remove the existing cross-CLI handoff concept itself.
- OpenCode and Claude Code remain supported audit surfaces; the change is about
  how the audit executes, not which CLIs are in scope.

## Open Questions

- None at the moment.

## Requirements (evolving)

- Update the repo-local `workflow-audit` spec to state that the skill must run
  in the main session and must not dispatch Claude Code or OpenCode agents for
  audit execution or Codex handoff continuation.
- Update both maintained skill surfaces to match the spec.
- Update any handoff/reference text that currently implies a generic CLI
  takeover so it clearly requires a main interactive Claude Code or OpenCode
  session.
- Update or add tests so the no-agent rule is covered and existing handoff
  expectations remain coherent.

## Acceptance Criteria (evolving)

- [ ] `.trellis/spec/skills/workflow-audit.md` encodes the no-agent execution
      rule clearly.
- [ ] `.agents/skills/workflow-audit/` and `.claude/skills/workflow-audit/`
      reflect the same behavior semantics.
- [ ] The Codex handoff template explicitly says the takeover must happen in a
      non-agent main session.
- [ ] Test scenarios cover the new restriction without leaving contradictory
      expectations behind.

## Definition of Done (team quality bar)

- Relevant docs/specs/tests updated consistently
- Validation run against the changed workflow-audit surfaces
- No unrelated workflow-audit behavior changed accidentally

## Out of Scope (explicit)

- Removing Claude Code or OpenCode from the supported audit surface
- Reworking runtime validation mode selection
- Changing workflow-capability-audit
- Introducing a new cross-CLI execution mechanism

## Technical Notes

- Likely touched files live under:
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/`
  - `.claude/skills/workflow-audit/`
- Expected hot spots include the handoff rules, codex handoff template, and
  tests around Codex handoff / takeover ordering / no-handoff-target behavior.

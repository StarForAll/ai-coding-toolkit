# 68 Codex Secondary Skills Empty Defaults To Ignored

## Purpose

Verify that `workflow-repair` defaults scan findings about an empty
`.codex/skills/` directory to `ignored` when the temp project's contract treats
`.agents/skills/` as the shared workflow primary carrier.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding says `.codex/skills/` is empty or missing shared workflow skills, but
> the temp project's installed workflow docs/runtime rules say `.agents/skills/`
> is the shared workflow primary carrier and `.codex/skills/` is only a
> secondary carrier for Codex-specific or project-local extras.

## Expected Mode

Conservative repair intake with temp-project carrier-boundary re-check before
any adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must compare the finding against installed Codex carrier
  rules and active shared skill surfaces
- the item must resolve to `ignored` when no installed surface claims that a
  current workflow-owned skill should live under `.codex/skills/`
- no source edit may be planned for that item

## Must Not

- must not adopt the finding solely because the scan report labeled it as a
  defect
- must not treat `.codex/skills/` emptiness alone as enough evidence of a
  broken Codex workflow surface

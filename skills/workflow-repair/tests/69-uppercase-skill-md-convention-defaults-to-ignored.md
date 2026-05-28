# 69 Uppercase Skill MD Convention Defaults To Ignored

## Purpose

Verify that `workflow-repair` defaults scan findings about uppercase
`SKILL.md` to `ignored` when the temp project's installed workflow surfaces
consistently use that filename convention.

## Input

User input:

> Run `/workflow-repair` on a validated `WORKFLOW_QUESTIONS.md` where one
> finding says installed skills use uppercase `SKILL.md` instead of lowercase
> `skill.md`, but the temp project's installed skill carriers and workflow docs
> consistently reference uppercase `SKILL.md`.

## Expected Mode

Conservative repair intake with temp-project convention re-check before any
adopted-fix execution.

## Expected Key Behaviors

- repair-side intake must re-check the claimed filename issue against the temp
  project's actual installed convention
- the item must resolve to `ignored` when the temp project consistently uses
  uppercase `SKILL.md`
- no source edit may be planned for that item

## Must Not

- must not adopt the finding solely because the scan report assumes lowercase
  `skill.md`
- must not invent a repair requirement that is absent from the temp-project
  contract

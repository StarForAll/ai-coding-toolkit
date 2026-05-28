# 15 Uppercase Skill MD Convention Is Not A Finding

## Purpose

Verify that `workflow-scan` does not emit a workflow finding merely because
installed skill files consistently use uppercase `SKILL.md`.

## Input

User input:

> Run `/workflow-scan` against an embedded temp project where installed skill
> carriers under `.agents/skills/` consistently use `SKILL.md`, installed
> workflow docs also reference `.agents/skills/*/SKILL.md`, and no installed
> surface claims that lowercase `skill.md` is required.

## Expected Mode

Inline scan in the current CLI session using the shared v4 report contract.

## Expected Key Behaviors

- inspect installed skill files and installed docs/runtime references together
- recognize that the temp project's current workflow contract consistently uses
  uppercase `SKILL.md`
- omit this observation from the `### WS-NNN` finding set unless another
  installed surface explicitly contradicts that convention

## Must Not

- must not classify uppercase `SKILL.md` usage as `confirmed-defect` solely
  because lowercase `skill.md` does not exist
- must not emit an `evidence-gap` finding when the installed workflow surfaces
  already consistently use uppercase `SKILL.md`
- must not import external filename assumptions that are not present in the
  temp project contract

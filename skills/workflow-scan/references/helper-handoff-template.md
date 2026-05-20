# workflow-scan Helper Handoff Template

Use this template only for internal helper-agent handoffs during
`workflow-scan --agent`.

This artifact is **not** part of the shared `workflow-scan-repair-v2`
protocol. `workflow-repair` does not read it.

```markdown
## Helper Scope

- Scope Owner: <helper label>
- Owned Surface: <paths or artifact class>

## Confirmed Facts

- <fact grounded in temp-project evidence>

## Candidate Issues

- <candidate issue title> — <why it might matter>

## Open Questions

- <question the coordinator must resolve locally>

## Relative Paths

- <temp-project-relative path>

## Status

- complete | partial | failed
- Notes: <timeout / malformed output / ambiguity details if any>
```

Coordinator usage note:

- treat this template as a read-only evidence handoff, not as final findings
- follow the current coordinator rules in `skills/workflow-scan/SKILL.md`
  Step 1A and the paired `.trellis/spec/skills/workflow-scan.md`
- keep this template limited to the handoff shape so scan-side behavior rules
  do not drift across multiple files

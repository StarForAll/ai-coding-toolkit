# Lightweight Output Template

Lightweight mode does not create a task and does not persist `audit-report.md`.  
However, the chat response must still use a fixed simplified structure.

```markdown
## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Scope: static/document-only

## Static Checks Performed
- <which docs / indexes / command docs / specs were inspected>

## Confirmed Issues
- <or explicitly write "No change-worthy issue is currently confirmed">

## Unconfirmed Items / False Alarms
- <candidate issue> -> <unconfirmed / false alarm / invalid premise>

## Per-CLI Adaptation Conclusions (if in scope)
- Claude Code: <conclusion / not-applicable>
- OpenCode: <conclusion / not-applicable>
- Codex: <conclusion / not-applicable>

## Suggested Fix Directions
- <direction only, no execution>

## Whether Escalation to a Non-trivial Audit Is Required
- <yes/no>
- Reason:
```

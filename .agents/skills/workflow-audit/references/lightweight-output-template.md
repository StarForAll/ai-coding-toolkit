# Lightweight Output Template

Lightweight mode does not create a task and does not persist `audit-report.md`.  
However, the chat response must still use a fixed simplified structure.

```markdown
## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Scope: static/document-only (lightweight: evidence mainline steps A, B, C, E)

## System Mechanics Understood (step A)
- <key findings: trellis init model, CLI adaptation contracts, embed state machine>

## Static Evidence Gathered (step B)
- <evidence item> — Layer: <source repo>
- <referenced paths cross-checked against filesystem>

## Gap Analysis (step C)
- <gap finding> — Layer: <source repo | generated target project | runtime command output>
- <cross-layer comparison: doc claims vs definition completeness>

## Confirmed Issues
- <or explicitly write "No change-worthy issue is currently confirmed">

## Unconfirmed Items / False Alarms
- <candidate issue> -> <unconfirmed / false alarm / invalid premise>

## Blocked Items / Evidence Gaps
- <blocked item title>
  - Type: <Blocked | Evidence Gap | Needs Clarification>
  - Cause:
  - What is needed to continue:

## Per-CLI Adaptation Conclusions (if in scope)
- Claude Code: <conclusion / not-applicable>
- OpenCode: <conclusion / not-applicable>
- Codex: <conclusion / not-applicable>

## Suggested Fix Directions
- <direction only, no execution>

## Recommended Next Step
- Recommended action: <brainstorm | start | check | update-spec | plain-language action>
- Trigger condition: <why this is the right next step now>
- Recommendation reason: <why this path over stronger alternatives>

## Whether Escalation to a Task-based Audit Is Required
- <yes/no>
- Reason:
```

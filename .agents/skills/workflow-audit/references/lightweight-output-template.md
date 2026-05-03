# Lightweight Output Template

Lightweight mode does not create a task and does not persist `audit-report.md`.  
However, the chat response must still use a fixed simplified structure.

Every evidence line must keep an explicit source-layer tag.
Always keep the `Per-CLI Adaptation Conclusions` section. If CLI adaptation was not examined, mark each CLI as `not-applicable` and briefly say why.

```markdown
## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Scope: static/document-only (lightweight: evidence mainline A, B, C; output step E)

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
This section is for unresolved branches inside a continuing audit result. Hard-stop `Blocked / <subtype>` exits stop the audit earlier and are not rendered here.
- <blocked item title>
  - Type: <Blocked | Evidence Gap | Needs Clarification>
  - Cause:
  - What is needed to continue:

## Per-CLI Adaptation Conclusions
- Claude Code: <conclusion / not-applicable + reason>
- OpenCode: <conclusion / not-applicable + reason>
- Codex: <conclusion / not-applicable + reason>

## Suggested Fix Directions
- <direction only, no execution>

## Recommended Next Step
- Recommended action: <brainstorm | start | check | update-spec | plain-language action>
- Trigger condition: <why this is the right next step now>
- Recommendation reason: <why this path over stronger alternatives>
- Stronger alternatives not selected: <why other stronger options were rejected now>

## Whether Escalation to a Task-based Audit Is Required
- <yes/no>
- Reason:
```

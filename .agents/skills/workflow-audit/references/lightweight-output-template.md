# Lightweight Output Template

Lightweight mode does not create a task and does not persist `audit-report.md`.  
However, the chat response must still use a fixed simplified structure.

Every evidence line must keep an explicit source-layer tag.
If `generated target project` evidence appears, keep the same layer tag but explicitly note whether it came from the clean `trellis init` baseline or the workflow-installed state after `install-workflow.py`.
Always keep the `Per-CLI Adaptation Conclusions` section. If CLI adaptation was not examined, mark each CLI as `not-applicable` and briefly say why.

```markdown
## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Scope: static/document-only (lightweight: evidence mainline A, B, C; output step E)
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## System Mechanics Understood (step A)
- <key findings: `.trellis` runtime truth layer, session-scoped task model, `.agents/skills/` dual role, CLI adaptation contracts, embed state machine>

## Static Evidence Gathered (step B)
- <evidence item> — Layer: <source repo>
- <referenced paths cross-checked against filesystem>

## Gap Analysis (step C)
- <gap finding> — Layer: <source repo | generated target project | runtime command output>
- Format rule: if Layer is `generated target project`, add `Stage: <baseline after trellis init | workflow-installed state after install-workflow.py>` on the next line instead of treating Stage as a separate evidence item
- <cross-layer comparison: doc claims vs definition completeness vs clean baseline vs post-install state>

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

When CLI adaptation is examined, each CLI entry should also state:
- official docs checked
- repo-local evidence checked
- practical development-use evidence checked
- whether those sources agree or where they differ

## Suggested Fix Directions
- <direction only, no execution>

Do not propose “cleanup” or “optimization” directions for evidence-backed non-defects. If the strongest conclusion is that the current behavior is acceptable, state that directly.

## Recommended Next Step
- Recommended action: <trellis-brainstorm | start | check | update-spec | plain-language action>
- Trigger condition: <why this is the right next step now>
- Recommendation reason: <why this path over stronger alternatives>
- Stronger alternatives not selected: <why other stronger options were rejected now>

## Whether Escalation to a Task-based Audit Is Required
- <yes/no>
- Reason:
```

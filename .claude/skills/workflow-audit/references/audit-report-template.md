# audit-report.md Template

Task-based `workflow-audit` runs must maintain `audit-report.md` inside the task directory.
The file may be updated incrementally during the active audit and becomes the current finalized report at the stop-and-confirm boundary.
Every evidence item and confirmed-issue entry must keep explicit source-layer tags.
When the layer is `generated target project`, also record whether the evidence came from the clean `trellis init` baseline or from the workflow-installed state after `install-workflow.py`.

```markdown
# workflow-audit: <workflow-name>

## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: <task-based static | task-based runtime>
- Current CLI: <inferred or explicit>
- Candidate Issues: <none / list>
- Generated Target Project Root: <none in static mode | /tmp/...>
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- <evidence action> — Layer: <source repo>
- <evidence action> — Layer: <generated target project> — Stage: <baseline after trellis init | workflow-installed state after install-workflow.py>
- <evidence action> — Layer: <runtime command output>

## Confirmed Issues

### [P0|P1|P2] <issue title>
- Conclusion: <one-sentence issue conclusion>
- Evidence Source:
  - Layer: <source repo | generated target project | runtime command output>
  - Stage: <n/a | baseline after trellis init | workflow-installed state after install-workflow.py>
  - <file path + relevant lines>
  - <command + key result>
- Validation Action:
  - <what was done to confirm it>
  - <example: Compared script signature against documentation; exit code 0 but missing required JSON output>
- Impact Scope:
  - <which directories / platforms / steps are affected>
- Suggested Fix Direction:
  - <direction only, not execution>

## Unconfirmed Items / False Alarms
- <candidate issue> -> <unconfirmed / false alarm / invalid premise>

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
This section is for unresolved branches inside a continuing audit result. Hard-stop `Blocked / <subtype>` exits stop the audit instead of being listed here.
- <blocked item title>
  - Type: <Blocked | Evidence Gap | Needs Clarification>
  - Cause:
  - Impact:
  - What is needed to continue:

## Per-CLI Adaptation Conclusions

Use `not-applicable` with a brief reason when CLI adaptation was not examined for a given CLI in this audit.

### Claude Code
- Official docs checked:
- Repo-local evidence checked:
- Practical development-use evidence checked:
- Agreement / discrepancy:
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

### OpenCode
- Official docs checked:
- Repo-local evidence checked:
- Practical development-use evidence checked:
- Agreement / discrepancy:
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

### Codex
- Official docs checked:
- Repo-local evidence checked:
- Practical development-use evidence checked:
- Agreement / discrepancy:
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

## Suggested Fix Directions
- <direction 1>
- <direction 2>

Do not add “cleanup” or “optimization” directions for evidence-backed non-defects. If the strongest conclusion is that the current behavior is acceptable, say so and stop.

## Propagation Scope and Synchronized Update Range
- <affected file layers / doc layers / script layers / test layers>
- <propagation risk notes>

## Recommended Next Step
- Recommended action: <trellis-brainstorm | start | check | update-spec | plain-language action>
- Trigger condition: <why this is the right next step now>
- Recommendation reason: <why this path was chosen over alternatives>
- Stronger alternatives not selected: <why stronger options were rejected now>

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - <confirmation item 1>
  - <confirmation item 2>
```

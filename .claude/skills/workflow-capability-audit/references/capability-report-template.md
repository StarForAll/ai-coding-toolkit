# capability-report.md Template

Task-based `workflow-capability-audit` runs must maintain `capability-report.md` inside the task directory.

```markdown
# workflow-capability-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Current CLI: <inferred or explicit>
- Current Trellis Version: <value>
- Compatible Anchor: <value>
- Audit Scope: task-based version-upgrade compatibility audit

## Version Gate Outcome
- Result: <passed>
- Reason:

## Evidence-Gathering Actions Executed In This Round
- <action> — Layer: <source repo | generated target project | runtime command output>

## Discovered Baseline Capabilities
- <capability cluster summary>

## Workflow-Managed Surface Matrix

| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WM-001 | ... | ... | ai-discovered | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Workflow-Dependent Trellis-Native Surface Matrix

| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TN-001 | ... | ... | ai-discovered | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Rejected / Unconfirmed Supplemental Points
- Point:
  - Status: <rejected | unconfirmed>
  - Evidence checked:
  - Reason:

## Structural-Break Judgment
- Result: <no | possible | yes>
- Signals:
- Why:
- Required next action:

## Confirmed Fix Scope
- <confirmed follow-up scope after user confirmation>

## Applied Corrections
- <only when the lifecycle advances beyond audit conclusion>

## Post-Fix Revalidation
- <only when corrections have been applied>

## A/B Fixture Status
- A Root:
- B Root:
- Destroyed: <no / yes>
- Final destruction confirmed by user: <no / yes>

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - <item 1>
  - <item 2>
```

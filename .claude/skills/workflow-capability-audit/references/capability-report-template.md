# capability-report.md Template

Task-based `workflow-capability-audit` runs must maintain `capability-report.md` inside the task directory.

The matrix headers below define the emitted first-version column order and should be preserved as-is when a human or AI updates the report.

```markdown
# workflow-capability-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Current CLI: <claude | opencode | codex>
- Current Trellis Version: <value>
- Compatible Anchor: <value>
- Audit Scope: task-based version-upgrade compatibility audit

## Version Gate Outcome
- Result: <passed>
- Reason: <current Trellis version is newer than the compatible anchor>

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
- Result: <no | possible>
- Signals:
- <signal items or "none detected from current report state">
- Why: <summary of why the judgment was reached>
- Required next action: <"Stop and wait for explicit user confirmation..." | "Continue with the current confirmation boundary.">

## Confirmed Fix Scope
- none yet

## Applied Corrections
- none yet

## Post-Fix Revalidation
- none yet

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

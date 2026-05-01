# audit-report.md Template

Task-based `workflow-audit` runs must maintain `audit-report.md` inside the task directory.
The file may be updated incrementally during the active audit and becomes the current finalized report at the stop-and-confirm boundary.

```markdown
# workflow-audit: <workflow-name>

## Audit Target and Boundary
- Workflow Root: `<workflow_path>`
- Audit Scope: <task-based static | task-based runtime>
- Current CLI: <inferred or explicit>
- Candidate Issues: <none / list>

## Evidence-Gathering Actions Executed in This Round
- <evidence action> — Layer: <source repo>
- <evidence action> — Layer: <generated target project>
- <evidence action> — Layer: <runtime command output>

## Confirmed Issues

### [P0|P1|P2] <issue title>
- Conclusion: <one-sentence issue conclusion>
- Evidence Source:
  - Layer: <source repo | generated target project | runtime command output>
  - <file path + relevant lines>
  - <command + key result>
- Validation Action:
  - <what was done to confirm it>
- Impact Scope:
  - <which directories / platforms / steps are affected>
- Suggested Fix Direction:
  - <direction only, not execution>

## Unconfirmed Items / False Alarms
- <candidate issue> -> <unconfirmed / false alarm / invalid premise>

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- <blocked item title>
  - Type: <Blocked | Evidence Gap | Needs Clarification>
  - Cause:
  - Impact:
  - What is needed to continue:

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

### OpenCode
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

### Codex
- Expected carrier model:
- Does the current implementation match:
- If not, what is wrong:

## Suggested Fix Directions
- <direction 1>
- <direction 2>

## Propagation Scope and Synchronized Update Range
- <affected file layers / doc layers / script layers / test layers>
- <propagation risk notes>

## Recommended Next Step
- Recommended action: <brainstorm | start | check | update-spec | plain-language action>
- Trigger condition: <why this is the right next step now>
- Recommendation reason: <why this path was chosen over alternatives>

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - <confirmation item 1>
  - <confirmation item 2>
```

# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - brainstorm 到 implementation/test-first 缺少 L0 硬门禁
  - record-session 命令层仍可直接执行
  - degraded active-task fallback 为 repo 级共享文件
  - session-start 强门禁补丁保留不可达旧分支
  - brainstorm 文档与脚本对出口快照字段门禁语义漂移
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `workflow_assets.py` and ran `trellis -v` to confirm version gate — Layer: `source repo`
- Read workflow authoring specs, workflow-audit skill contract, and command/script specs — Layer: `source repo`
- Indexed workflow source assets and searched issue-related identifiers across `docs/workflows/新项目开发工作流/` and `/tmp/trellis-0.5.17-2` — Layer: `source repo`
- Compared installed workflow copies inside `/tmp/trellis-0.5.17-2` for brainstorm / delivery / record-session / hook carriers / workflow-state references — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`

## Confirmed Issues

Pending evidence confirmation.

## Unconfirmed Items / False Alarms

Pending classification.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

None currently.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: pending
- Practical development-use evidence checked: pending
- Agreement / discrepancy: pending
- Expected carrier model: pending
- Does the current implementation match: pending
- If not, what is wrong: pending

### OpenCode
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: pending
- Practical development-use evidence checked: pending
- Agreement / discrepancy: pending
- Expected carrier model: pending
- Does the current implementation match: pending
- If not, what is wrong: pending

### Codex
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: pending
- Practical development-use evidence checked: pending
- Agreement / discrepancy: pending
- Expected carrier model: pending
- Does the current implementation match: pending
- If not, what is wrong: pending

## Suggested Fix Directions

- Pending evidence confirmation.

## Propagation Scope and Synchronized Update Range

- `commands/*.md`
- `commands/shell/*.py`
- `commands/install-workflow.py`
- `commands/*test*.py`

## Recommended Next Step

- Recommended action: continue runtime audit and add regression coverage
- Trigger condition: candidate issues are grounded in multiple workflow layers and need source-to-installed verification
- Recommendation reason: direct source edits before test/evidence confirmation would risk reintroducing drift
- Stronger alternatives not selected: skip direct fixes until issue classification is finished

## Stop Point and Pending Confirmations

- Auto-continue allowed: No
- User confirmation required for:
  - none yet; continue after evidence classification

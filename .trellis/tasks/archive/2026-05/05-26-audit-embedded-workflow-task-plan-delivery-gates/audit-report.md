# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: task-based runtime
- Current CLI: codex
- Candidate Issues: parent plan -> leaf implementation 主路径、formal project-audit 与 task-level check 绑定、code-related 覆盖识别、project_audit_gate_status=not_run、验证结果与 gate status 一致性、coverage 粒度一致性
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and compared `COMPATIBLE_TRELLIS_VERSION` with `trellis -v` — Layer: source repo
- Read workflow authoring specs and `workflow-audit` skill contracts before auditing workflow product assets — Layer: source repo
- Read `docs/workflows/新项目开发工作流/commands/plan.md`, `project-audit.md`, `delivery.md`, `commands/shell/plan-validate.py`, `commands/shell/workflow-state.py`, `commands/shell/validators_gates.py` — Layer: source repo
- Inspected installed workflow files under `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/`, `.claude/commands/trellis/`, `.opencode/commands/trellis/`, `.agents/skills/` — Layer: generated target project — Stage: workflow-installed state after install-workflow.py
- Confirmed `/tmp/trellis-0.5.17-2` currently has installed workflow carriers but no existing task artifacts matching the candidate issue set, so targeted runtime reproduction is still pending — Layer: generated target project — Stage: workflow-installed state after install-workflow.py

## Confirmed Issues

Pending analysis.

## Unconfirmed Items / False Alarms
- Pending analysis.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- None yet.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable in this audit slice; current focus is task-plan / delivery gate behavior, not CLI adaptation drift
- Repo-local evidence checked: command carriers exist in `/tmp/trellis-0.5.17-2/.claude/commands/trellis/`
- Practical development-use evidence checked: not yet in scope
- Agreement / discrepancy: not-applicable
- Expected carrier model: not-applicable
- Does the current implementation match: not-applicable
- If not, what is wrong: not-applicable

### OpenCode
- Official docs checked: not-applicable in this audit slice; current focus is task-plan / delivery gate behavior, not CLI adaptation drift
- Repo-local evidence checked: command carriers exist in `/tmp/trellis-0.5.17-2/.opencode/commands/trellis/`
- Practical development-use evidence checked: not yet in scope
- Agreement / discrepancy: not-applicable
- Expected carrier model: not-applicable
- Does the current implementation match: not-applicable
- If not, what is wrong: not-applicable

### Codex
- Official docs checked: not-applicable in this audit slice; current focus is task-plan / delivery gate behavior, not CLI adaptation drift
- Repo-local evidence checked: shared skill carriers and `.codex/agents/trellis-*.toml` exist in `/tmp/trellis-0.5.17-2`
- Practical development-use evidence checked: not yet in scope
- Agreement / discrepancy: not-applicable
- Expected carrier model: not-applicable
- Does the current implementation match: not-applicable
- If not, what is wrong: not-applicable

## Suggested Fix Directions
- Pending confirmed issues.

## Propagation Scope and Synchronized Update Range
- Likely affected layers if issues are confirmed: `commands/*.md`, `commands/shell/*.py`, installed workflow script mirrors, and relevant workflow tests/fixtures if they exist
- Propagation risk notes: plan / project-audit / delivery gates are cross-document and cross-script contracts; any confirmed fix must update both doc contract and executable validator surface

## Recommended Next Step
- Recommended action: continue evidence gathering
- Trigger condition: current round has enough static evidence to justify targeted runtime reproduction inside `/tmp/trellis-0.5.17-2`
- Recommendation reason: several candidate issues depend on whether source contract and installed runtime behavior diverge in actual task transitions
- Stronger alternatives not selected: no source patch yet because confirmed issue set is not finalized

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - 修改 `docs/workflows/新项目开发工作流/` 的任何源码
  - 在确认问题后执行正式补丁

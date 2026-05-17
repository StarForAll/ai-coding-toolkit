# Task Info

## Execution Boundary

- Current task state: planning only.
- Formal execution pause: do not start implementation until the user explicitly resumes.
- Agent use: forbidden by user instruction; all future work must stay in the main Codex session.
- Repair edit boundary: only `docs/workflows/新项目开发工作流`.
- Allowed non-repair writes already performed: this task directory under `.trellis/tasks/05-17-workflow-gate-consistency-audit`.

## Audit Boundary

- Workflow path: `docs/workflows/新项目开发工作流`
- Target-project evidence path: `/tmp/trellis-0.5.16-2`
- Candidate issues: supplied by user, treated as hypotheses until validated.
- Version gate:
  - Compatible anchor: `0.5.16`
  - Current `trellis -v`: `0.5.16`
  - Target `.trellis/.version`: `0.5.16`
  - Status: passed

## Required Workflow-Audit Constraints

- The workflow target must remain exactly `docs/workflows/新项目开发工作流`.
- Evidence must keep source-layer tags:
  - `source repo`
  - `generated target project baseline`
  - `generated target project workflow-installed state`
  - `runtime command output`
- CLI surface in scope: Claude Code, OpenCode, Codex.
- If formal embed execution becomes necessary under Codex, stop and hand off to a main interactive Claude Code or OpenCode session; do not use an agent.

## Likely Source Areas To Inspect Later

- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
- `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/shell/patch-workflow-phase.py`
- `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/完整流程演练.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`

## Target Evidence Areas To Inspect Later

- `/tmp/trellis-0.5.16-2/.trellis/workflow.md`
- `/tmp/trellis-0.5.16-2/.trellis/scripts/task.py`
- `/tmp/trellis-0.5.16-2/.trellis/scripts/get_context.py`
- `/tmp/trellis-0.5.16-2/.trellis/scripts/workflow/workflow-state.py`
- `/tmp/trellis-0.5.16-2/.trellis/library-lock.yaml`
- `/tmp/trellis-0.5.16-2/.trellis/workflow-installed.json`
- `/tmp/trellis-0.5.16-2/AGENTS.md`
- `/tmp/trellis-0.5.16-2/.claude/hooks/session-start.py`
- `/tmp/trellis-0.5.16-2/.agents/skills/trellis-start/SKILL.md`
- `/tmp/trellis-0.5.16-2/.agents/skills/trellis-finish-work/SKILL.md`

## Resume Instruction

When the user resumes, load this task context, then run formal workflow-audit evidence steps A/B/C in the main session. Only after evidence confirms defects should repair edits begin.

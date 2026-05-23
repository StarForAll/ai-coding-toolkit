# PRD

## Goal
Repair `docs/workflows/新项目开发工作流` so the embedded workflow remains consistent with Trellis 0.5.17 target-project installs and does not regress when native command/skill assets exist in either `commands/` or `skills/` carrier locations.

## Scope
- Fix confirmed documentation drift in workflow docs under `docs/workflows/新项目开发工作流`
- Fix confirmed runtime patch drift in workflow helper scripts under `docs/workflows/新项目开发工作流/commands`
- Improve install/upgrade detection so Trellis native assets are resolved from the correct command or skill carrier when one location is absent
- Keep changes limited to `docs/workflows/新项目开发工作流`

## Requirements
- `continue.md` must no longer reference removed or stale routing-table wording
- `finish-work.md` must no longer refer to obsolete Phase 3.4 numbering
- Strong-gate stage/state docs must be internally consistent and cover the full confirmed stage chain
- `workflow_phase.py` patch behavior must not disable step-level compatibility in a way that breaks the embedded workflow's documented contract
- `session-start.py` fallback output must remain actionable when `workflow-state.py route` fails
- OpenCode subagent injection must not silently bypass stage gates, and Bash command prefix injection must avoid mutating user commands unless required for session identity propagation
- Install/upgrade logic must search both command and skill carriers where Trellis native assets may live, instead of assuming one fixed path

## Verification
- Run focused text/structure checks over modified workflow docs
- Run targeted Python syntax checks on modified helper scripts
- Confirm install/upgrade helper lookup logic still resolves both carrier locations safely

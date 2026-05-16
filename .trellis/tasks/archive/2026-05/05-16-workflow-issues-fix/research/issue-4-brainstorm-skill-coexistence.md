# Research: Issue 4 - Old skill and new skill coexist, routing conflicts

- **Query**: Do trellis-brainstorm (old) and brainstorm (new) skills coexist and cause routing conflicts?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Both Skills Exist in Embedded Target

In the embedded project at `/tmp/trellis-0.5.16-2/.agents/skills/`:

| Skill Directory | Size (SKILL.md) | Origin | Description |
|----------------|-----------------|--------|-------------|
| `brainstorm/` | 23,088 bytes | New workflow command | Strong-gate brainstorm requiring `assessment.md` first; adds L0/L1/L2 classification, project-level estimation gate, customer-facing PRD gate |
| `trellis-brainstorm/` | 15,993 bytes | Trellis native/legacy | Simpler brainstorm; creates tasks directly without requiring feasibility assessment |

### Key Behavioral Differences

| Aspect | New `brainstorm` | Old `trellis-brainstorm` |
|--------|-------------------|--------------------------|
| Assessment gate | Mandatory: must have valid `assessment.md` before entry | No assessment requirement |
| workflow-state.json init | Explicit: `workflow-state.py init "$TASK_DIR" --stage brainstorm` | Not mentioned |
| Gate validation | Explicit: `workflow-state.py validate <task-dir>` | Not mentioned |
| Complexity classification | L0/L1/L2 with formal routing | Trivial/Simple/Moderate/Complex (informational, not gating) |
| Project-level estimation | Mandatory gate before leaving brainstorm | Not mentioned |
| customer-facing-prd.md | Required before entering design | Not mentioned |
| Phase state machine | Constrained by strong-gate protocol | Not constrained |
| Skill references | Calls `prd` skill | No external skill references |

### Routing Conflicts

1. **trellis-start routes to trellis-brainstorm** (`/tmp/trellis-0.5.16-2/.agents/skills/trellis-start/SKILL.md:48-49`):
   ```
   - **Active task + no `prd.md`** → Phase 1.1. Load the `trellis-brainstorm` skill.
   - **No active task** → when the user describes multi-step work, load the `trellis-brainstorm` skill
   ```
   And in the routing table (line 57):
   ```
   | New feature / unclear requirements | `trellis-brainstorm` |
   ```

2. **embedded workflow.md routes to trellis-brainstorm** (`/tmp/trellis-0.5.16-2/.trellis/workflow.md:160`):
   ```
   (2) if assessment allows, load `trellis-brainstorm` skill to discuss requirements and iterate on prd.md
   ```
   Also lines 176, 189, 339, 341 reference `trellis-brainstorm`.

3. **AGENTS.md routing table** (the new NL routing, lines 41):
   ```
   | ... | `/trellis:brainstorm` | 描述需求澄清意图，或显式触发 `brainstorm` skill | §2 需求发现 |
   ```
   This references `brainstorm` (new), not `trellis-brainstorm`.

4. **Codex no_task bootstrap** (`inject-workflow-state.py:86-99`):
   The `CODEX_NO_TASK_BOOTSTRAP_NOTICE` tells Codex to read `trellis-start` skill, which then routes to `trellis-brainstorm`.

### Conflict Summary

There are TWO parallel routing paths:

**Path A (New workflow)**:
User -> AGENTS.md NL routing -> `brainstorm` skill -> assessment gate -> L0/L1/L2 -> strong gate

**Path B (Legacy/Compatibility)**:
User -> inject-workflow-state.py no_task bootstrap -> `trellis-start` skill -> `trellis-brainstorm` skill -> direct task creation (no assessment gate)

**Which path wins depends on how the AI enters the workflow:**
- If the AI reads AGENTS.md first (as Codex naturally does): it may find `brainstorm` and use the new path.
- If the AI reads `trellis-start` via the bootstrap notice (Codex no-task state): it will be routed to `trellis-brainstorm` (old).
- On Claude Code / OpenCode: The `/trellis:brainstorm` command exists and points to the new skill, so the new path is used. But the `trellis-brainstorm` skill still exists in `.agents/skills/` and could be loaded by mistake.

### Source Files Involved

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/brainstorm.md` | New brainstorm command source |
| `docs/workflows/新项目开发工作流/commands/install-workflow.py` | Installer that writes both skills |
| `.agents/skills/brainstorm/SKILL.md` (embedded) | New brainstorm skill |
| `.agents/skills/trellis-brainstorm/SKILL.md` (embedded) | Legacy brainstorm skill |
| `.agents/skills/trellis-start/SKILL.md` (embedded) | Routes to trellis-brainstorm (old) |
| `.trellis/workflow.md` (embedded) | Routes to trellis-brainstorm (old) |
| `AGENTS.md` (embedded) | Routes to brainstorm (new) |

## Verdict

**REAL** -- Both `brainstorm` and `trellis-brainstorm` coexist in `.agents/skills/`. The legacy routing chain (`trellis-start` -> `trellis-brainstorm`) still routes to the old skill. The new AGENTS.md NL routing table routes to the new `brainstorm` skill. Depending on which entry path the AI takes, it may use the old skill (which bypasses assessment gates) or the new skill (which enforces them).

### Proposed Fix Scope

1. `trellis-start` SKILL.md: Update to route to new `brainstorm` skill instead of `trellis-brainstorm`.
2. `workflow.md` (the embedded template): Update references from `trellis-brainstorm` to `brainstorm`.
3. `install-workflow.py`: Either remove `trellis-brainstorm` from the installed skill set, or add a deprecation notice and redirect to the new `brainstorm`.
4. `inject-workflow-state.py`: Update `CODEX_NO_TASK_BOOTSTRAP_NOTICE` if needed.

## Caveats / Not Found

- `trellis-brainstorm` is also installed as a Trellis native skill on Claude Code (visible in the available skills list at the top of this conversation). Removing it from `.agents/skills/` alone won't remove the globally installed skill.
- The test file `test_workflow_installers.py:158` references `trellis-brainstorm` and creates it in test fixtures.

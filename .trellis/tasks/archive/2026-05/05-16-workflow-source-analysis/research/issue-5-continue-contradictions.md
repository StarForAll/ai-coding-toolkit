# Research: Issue 5 - /trellis:continue has internal contradictions

- **Query**: Does continue.md start with native status/artifact routing but later add a strong gate Phase Router, creating contradictions?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/ops/.../commands/start-patch-phase-router.md` | Source template for continue command (Phase Router only) |
| `/tmp/trellis-0.5.16-2/.claude/commands/trellis/continue.md` | Embedded continue command |

### Analysis

#### Source template (start-patch-phase-router.md)

The source template is ONLY the Phase Router section (77 lines total). It contains:
- Core positioning: "only do current confirmed stage identification and re-entry"
- Execution steps: get context -> run workflow-state.py route -> execute by action field
- Implementation constraints
- Next-step recommendation format

There is NO native status/artifact routing in the source template. It is purely a Phase Router.

#### Embedded continue.md

The embedded version (77 lines) is IDENTICAL to the source template. It contains:
1. **Line 7-9**: Core positioning -- Phase Router only, no cross-stage auto-advance
2. **Lines 16-26**: Execution steps with `workflow-state.py route` command
3. **Lines 28-44**: Action routing table (first_entry, reenter, awaiting_confirmation, blocked, etc.)
4. **Lines 46-54**: Implementation constraints
5. **Lines 56-77**: Next-step recommendation format

There is NO "native status/artifact routing" section at the beginning. The command starts directly with the Phase Router.

#### Comparison with issue description

The issue describes: "starts with native status/artifact routing but later adds a strong gate Phase Router"

This does NOT match the actual content. The embedded continue.md:
- Does NOT have any native status/artifact routing section
- Does NOT have a "line 23 area (native routing)" vs "line 59 area (gate router)" split
- Starts directly with the Phase Router from line 1
- Has no contradictions within its content

### Verdict: NOT_REAL

**Evidence:**
1. The source template (`start-patch-phase-router.md`) is a single coherent Phase Router document with no contradictory sections
2. The embedded version is identical to the source template
3. There is no "native status/artifact routing" section anywhere in continue.md
4. The command structure is clean: get context -> route -> execute by action -> output recommendation
5. No internal contradictions were found between any sections

### Source files involved

- `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` -- source template, clean and consistent
- No fix needed

### Proposed fix scope

None. The continue command is internally consistent.

## Caveats / Not Found

- It is possible the issue description refers to an older version of continue.md that has since been fixed
- Or the issue may have been conflated with the workflow.md's Phase 1/2/3 structure (Issue 1) which does have a native Plan/Execute/Finish framing that contradicts the gate chain
- If the issue is about a different continue command variant (e.g. for a different CLI platform), that was not found in the embedded project

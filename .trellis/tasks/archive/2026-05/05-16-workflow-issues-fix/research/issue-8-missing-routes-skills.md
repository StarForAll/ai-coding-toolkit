# Research: Issue 8 - Missing routes and missing skills

- **Query**: Do AGENTS.md and workflow source reference skills that don't exist in .agents/skills/?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Skills Referenced in AGENTS.md (Embedded Target)

The embedded AGENTS.md at `/tmp/trellis-0.5.16-2/AGENTS.md` references these skills in its NL routing table (lines 40-64):

| Referenced Skill | Exists in `.agents/skills/`? | Referenced By |
|-----------------|------------------------------|---------------|
| `feasibility` | YES | AGENTS.md line 40 |
| `brainstorm` | YES | AGENTS.md line 41 |
| `design` | YES | AGENTS.md line 42 |
| `plan` | YES | AGENTS.md line 43 |
| `test-first` | YES | AGENTS.md line 44 |
| `project-audit` | YES | AGENTS.md line 45 |
| `check` | YES | AGENTS.md line 46 |
| `review-gate` | YES | AGENTS.md line 47 |
| `trellis-finish-work` | YES (as `trellis-finish-work`) | AGENTS.md line 48 |
| `delivery` | YES | AGENTS.md line 49 |
| `trellis-research` | NOT a skill (sub-agent) | AGENTS.md line 56 |
| `trellis-continue` | YES (as `trellis-continue`) | AGENTS.md line 57 |
| `trellis-break-loop` | YES | AGENTS.md line 58 |
| `trellis-update-spec` | YES | AGENTS.md line 59 |
| **`check-cross-layer`** | **NO** | AGENTS.md line 60 |
| **`integrate-skill`** | **NO** | AGENTS.md line 61 |
| `trellis-before-dev` | YES | AGENTS.md line 62 |
| **`onboard`** | **NO** | AGENTS.md line 63 |
| **`create-command`** | **NO** | AGENTS.md line 64 |

### Skills Referenced in plan SKILL.md

The embedded `plan/SKILL.md:118` references:
```
**调用 Skill**：`project-planner` + `writing-plans`
```

These skills are referenced as skills to call during the plan phase but do NOT exist:
- `project-planner` -- NOT found in `.agents/skills/`
- `writing-plans` -- NOT found in `.agents/skills/`

### Complete Missing Skills List

| Missing Skill | Where Referenced | Expected Behavior |
|--------------|-----------------|-------------------|
| `check-cross-layer` | AGENTS.md NL routing, 命令映射.md line 244/522/534, commands/check.md line 25, commands/design.md line 553, install-workflow.py line 167 | Cross-layer consistency checking |
| `integrate-skill` | AGENTS.md NL routing, 命令映射.md line 523, install-workflow.py line 168 | Skill integration |
| `onboard` | AGENTS.md NL routing, 命令映射.md line 525, install-workflow.py line 170 | Project onboarding |
| `create-command` | AGENTS.md NL routing, 命令映射.md line 526, install-workflow.py line 171 | Creating new commands |
| `project-planner` | plan/SKILL.md line 118, 命令映射.md line 367/427, 多CLI通用新项目完整流程演练.md line 478 | Task planning assistance |
| `writing-plans` | plan/SKILL.md line 118, 命令映射.md line 367/428, 多CLI通用新项目完整流程演练.md line 479 | Plan writing assistance |

### What Actually Exists in .agents/skills/

```
brainstorm/          (new workflow command)
check/               (new workflow command)
delivery/            (new workflow command)
design/              (new workflow command)
feasibility/         (new workflow command)
plan/                (new workflow command)
project-audit/       (new workflow command)
review-gate/         (new workflow command)
test-first/          (new workflow command)
trellis-before-dev/  (Trellis native)
trellis-brainstorm/  (Trellis native, legacy)
trellis-break-loop/  (Trellis native)
trellis-check/       (Trellis native)
trellis-continue/    (Trellis native)
trellis-finish-work/ (Trellis native)
trellis-meta/        (Trellis native)
trellis-start/       (Trellis native)
trellis-update-spec/ (Trellis native)
.backup-original/    (installer backup)
```

Total: 21 directories, 17 actual skill directories, 1 backup, 1 subdirectory.

### Impact Assessment

1. **AGENTS.md routing table** (lines 60-64): When a user's intent matches `check-cross-layer`, `integrate-skill`, `onboard`, or `create-command`, the AI is told to "显式触发 `xxx` skill" but no such skill exists in `.agents/skills/`. The AI will either:
   - Fail to find the skill and fall back to general behavior
   - Misinterpret the routing and do something else

2. **plan/SKILL.md** (line 118): The instruction "调用 Skill：project-planner + writing-plans" cannot be followed because these skills don't exist. The AI will skip this instruction and proceed without external skill assistance, which may reduce plan quality but won't block execution.

3. **命令映射.md** (lines 367, 427-428): Documents `project-planner` and `writing-plans` as the reusable skills for plan, but they're not installed.

### Source Files Involved

| File Path | Description |
|---|---|
| `docs/workflows/新项目开发工作流/commands/install-workflow.py:167-171` | Writes NL routing table with missing skill references |
| `docs/workflows/新项目开发工作流/命令映射.md:367,427-428,522-526,534` | Documents missing skills as mapped |
| `docs/workflows/新项目开发工作流/commands/plan.md:118` | References project-planner + writing-plans |
| `docs/workflows/新项目开发工作流/commands/check.md:25` | References check-cross-layer |
| `docs/workflows/新项目开发工作流/commands/design.md:553` | References check-cross-layer |
| `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md:478-479` | References project-planner + writing-plans |

## Verdict

**REAL** -- Six skills are referenced in AGENTS.md routing, plan SKILL.md, and workflow documentation but do not exist in `.agents/skills/`:
- `check-cross-layer` -- Referenced in AGENTS.md and 3 workflow source files
- `integrate-skill` -- Referenced in AGENTS.md and install-workflow.py
- `onboard` -- Referenced in AGENTS.md and install-workflow.py
- `create-command` -- Referenced in AGENTS.md and install-workflow.py
- `project-planner` -- Referenced in plan SKILL.md, 命令映射.md, and flow walkthrough
- `writing-plans` -- Referenced in plan SKILL.md, 命令映射.md, and flow walkthrough

The AGENTS.md routing table explicitly tells Codex to "trigger" these skills, but they don't exist. For `project-planner`/`writing-plans`, the plan SKILL.md instructs the AI to call them but provides no fallback when they're absent.

### Proposed Fix Scope

Two approaches:

**Approach A: Remove references** -- Remove the missing skill references from AGENTS.md NL routing, 命令映射.md, and plan SKILL.md. Replace with inline instructions or mark as "not yet implemented."

**Approach B: Create stub skills** -- Create minimal SKILL.md files for each missing skill that provide basic guidance without external dependencies. This is the more correct approach since the routing table already points to them.

Files to modify:
1. `commands/install-workflow.py`: Either remove the routing entries or add stub skill creation
2. `commands/plan.md`: Add fallback when `project-planner`/`writing-plans` are not available
3. `命令映射.md`: Update skill mapping table
4. (Optionally) Create source skill files under `commands/skills/` for the missing 6 skills

## Caveats / Not Found

- Some of these skills may exist as globally installed skills on Claude Code (visible in the system reminder skills list). For example, `trellis-check` exists globally. But for Codex, which reads `.agents/skills/`, they are genuinely missing.
- `check-cross-layer` is not in the global Claude Code skills list either.
- `project-planner` and `writing-plans` are not in the global Claude Code skills list.

# Research: Reference Project workflow.md (v0.5.16-2)

- **Query**: workflow.md structure, Phase Index, breadcrumb blocks, no_task/planning/in_progress blocks, Plan/Execute/Finish three-phase model
- **Scope**: internal (reference project at /tmp/trellis-0.5.16-2/)
- **Date**: 2026-05-16

## Findings

### File Location

`/tmp/trellis-0.5.16-2/.trellis/workflow.md` (810 lines, 41033 bytes)

### Structure Overview

The file follows this major section structure:

1. **Lines 1-12**: Core Principles (5 principles)
2. **Lines 15-96**: Trellis System (Developer Identity, Spec System, Task System, Workspace System, Context Script)
3. **Lines 99-140**: WORKFLOW-STATE BREADCRUMB CONTRACT comment block (implementation contract)
4. **Lines 142-152**: ## Phase Index (the ASCII phase listing)
5. **Lines 154**: Strong gate rule
6. **Lines 156-162**: `[workflow-state:no_task]` block
7. **Lines 164-179**: Phase 1: Plan + `[workflow-state:planning]` block
8. **Lines 181-192**: `[workflow-state:planning-inline]` block (Codex inline alternate)
9. **Lines 194-211**: Phase 2: Execute + `[workflow-state:in_progress]` block
10. **Lines 213-222**: `[workflow-state:in_progress-inline]` block (Codex inline alternate)
11. **Lines 224-243**: Phase 3: Finish + `[workflow-state:completed]` block (DEAD)
12. **Lines 245-304**: Rules, Skill Routing tables, DO NOT skip skills
13. **Lines 306-637**: Detailed Phase 1/2/3 walkthrough
14. **Lines 640-698**: Customizing Trellis (for forks)
15. **Lines 700-810**: Development Process, Session End

### Phase Index (Lines 142-152)

```
Phase 1: Feasibility → 项目可行性评估 (assessment.md)
Phase 2: Brainstorm  → 需求明确与确认 (prd.md)
Phase 3: Design      → 技术架构与设计 (design/)
Phase 4: Plan        → 任务拆解与规划 (task_plan.md)
Phase 5: Implement   → 代码实现与自检
Phase 6: Check       → 质量检查与验证
Phase 7: Delivery    → 交付与收尾
```

**Strong gate rule** (line 154): Each phase must enter `awaiting_user_confirmation` after completion; `/trellis:continue` only re-enters current confirmed phase, cannot auto-advance.

### Plan -> Execute -> Finish Three-Phase Model (Lines 164-243)

The detailed walkthrough uses a three-phase grouping:

- **Phase 1: Plan** (lines 164-456) — Steps 1.0 through 1.5
  - 1.0 Create task `[required once]`
  - 1.1 Requirement exploration `[required repeatable]`
  - 1.2 Research `[optional repeatable]`
  - 1.3 Configure context `[required once]`
  - 1.4 Activate task `[required once]`
  - 1.5 Completion criteria

- **Phase 2: Execute** (lines 459-550) — Steps 2.1 through 2.3
  - 2.1 Implement `[required repeatable]`
  - 2.2 Quality check `[required repeatable]`
  - 2.3 Rollback `[on demand]`

- **Phase 3: Finish** (lines 553-637) — Steps 3.1 through 3.5
  - 3.1 Quality verification `[required repeatable]`
  - 3.2 Debug retrospective `[on demand]`
  - 3.3 Spec update `[required once]`
  - 3.4 Commit changes `[required once]`
  - 3.5 Wrap-up reminder

### `[workflow-state:no_task]` Block (Lines 158-162)

Three routing options:
- **A Direct answer** — pure Q&A, no file writes, one-line answer, repo reads <= 2 files
- **B Create a task** — load `feasibility` skill -> `trellis-brainstorm` skill -> `task.py start`
- **C Inline change** — escape hatch requiring explicit trigger phrases from user ("skip trellis" / "no task" / "just do it" / etc.)

### `[workflow-state:planning]` Block (Lines 175-179)

Precondition: feasibility done, assessment allows brainstorm.
Load `trellis-brainstorm` skill, iterate on prd.md.
Phase 1.3 jsonl curation required before `task.py start`.

### `[workflow-state:planning-inline]` Block (Lines 188-192)

Codex-only alternate. Phase 1.3 jsonl curation SKIPPED. Main session loads `trellis-before-dev` directly in Phase 2.

### `[workflow-state:in_progress]` Block (Lines 206-211)

Flow: trellis-implement -> trellis-check -> trellis-update-spec -> commit -> `/trellis:finish-work`.
Default: dispatch sub-agents. Sub-agent self-exemption rule. Dispatch protocol requires `Active task:` line.
Inline override requires explicit user phrases.

### `[workflow-state:in_progress-inline]` Block (Lines 219-222)

Codex inline alternate. Main session loads `trellis-before-dev` -> edits code -> loads `trellis-check` -> fixes -> `trellis-update-spec` -> commit -> `/trellis:finish-work`.

### `[workflow-state:completed]` Block (Lines 239-243)

Currently DEAD in normal flow. `cmd_archive` writes status=completed and moves dir in same call, so resolver loses pointer. Block preserved for future redesign.

### Skill Routing Tables (Lines 253-280)

Two platform groups:
1. `[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi]` — dispatch sub-agents for implement/check
2. `[codex-inline, Kilo, Antigravity, Windsurf]` — main session implements directly using `trellis-before-dev` and `trellis-check`

### Breadcrumb Contract (Lines 99-140)

Key invariants:
- 4 `[workflow-state:STATUS]` blocks are the single source of truth
- inject-workflow-state.py only parses them, no fallback dict
- STATUS charset: `[A-Za-z0-9_-]+`
- When tag missing, degrades to generic "Refer to workflow.md for current step."
- TAG to PHASE scoping: no_task -> before Phase 1; planning -> all Phase 1; in_progress -> Phase 2 + Phase 3.1-3.4; completed -> currently DEAD

## Caveats / Not Found

- The Phase Index shows 7 phases (Feasibility through Delivery), but the detailed walkthrough only covers 3 grouped phases (Plan/Execute/Finish). This is the intended design: the Phase Index lists granular phases, while the Plan/Execute/Finish structure is the runtime grouping.
- The `completed` workflow-state block is explicitly marked as DEAD — it never fires because archive moves the directory immediately.

# Findings

## Current Status

- This task has moved from pure analysis into document implementation.
- Workflow docs were modified in the current session.
- This session completed the first-pass delivery of the new primary walkthrough and reverse-link cleanup.
- Do not run `record-session` yet; the skill requires human-tested and committed work.

### Landed In This Session

- Added:
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- Updated:
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/完整流程演练.md`
- Corrected mapping drift:
  - `brainstorming` -> `brainstorm`

### Verification Run

- `git diff --check -- docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md docs/workflows/新项目开发工作流/工作流总纲.md docs/workflows/新项目开发工作流/命令映射.md docs/workflows/新项目开发工作流/完整流程演练.md`
  - Result: pass
- `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
  - Result: pass
  - Notes: 2 informational `stale-related-asset` messages only

## Confirmed Decisions

### New Primary Walkthrough

- Add a new first-entry document:
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- Role:
  - Primary entry for new readers
  - General new-project walkthrough
  - Native multi-CLI guidance for Claude Code, Codex, OpenCode

### Existing `完整流程演练.md`

- Keep `docs/workflows/新项目开发工作流/完整流程演练.md`
- Reposition it as:
  - Dual-track delivery-control special case
  - Not the default first-read walkthrough

### Linking Strategy

- Prefer `new -> old`
- The new walkthrough should route readers to:
  - `工作流总纲.md`
  - `命令映射.md`
  - `完整流程演练.md`
- Old docs should add minimal reverse hints:
  - First-time readers should start from `多CLI通用新项目完整流程演练.md`
- Reverse hints should be role-specific, not copy-pasted with one identical template

## New Walkthrough Structure

### Opening Order

1. Explain how to read this workflow
2. Then enter the stage-based mainline

### Opening Content

- Keep a navigation table:
  - `场景 / 先看 / 再看 / 为什么`
- Keep a short roles table:
  - `文档 / 角色`

### Stage Chain

- `feasibility`
- `brainstorm`
- `design`
- `plan`
- `test-first + start`
- `self-review + check`
- `finish-work`
- `delivery`
- `record-session`

### Unified Stage Template

Each stage section should include:

1. Stage goal
2. Entry conditions
3. CLI entry differences
4. Recommended capabilities
5. Execution actions
6. Conditional branches
7. Outputs and verification
8. Next step

## CLI and Capability Writing Rules

### CLI Entry Differences

- Use a stable per-stage section for:
  - Claude Code
  - OpenCode
  - Codex
- Keep it at protocol level only:
  - How to enter the stage
  - Short note on entry model
- Do not include runtime config details

### Recommended Capabilities

- Use concrete tool/skill names and fallback order
- Do not include provider setup, secrets, MCP registration, or platform config

Recommended format:

- `场景 / 优先能力 / 回退`

### Downgrade Rules

- Try the stage-defined fallback chain first
- If evidence remains insufficient, explicitly mark `[Evidence Gap]`
- Platform config details stay in platform-specific README files

## External Delivery Branch Scope

### Explicit Branch Needed

- `feasibility`
- `brainstorm`
- `design`
- `plan`
- `delivery`

### Light Reminder Only

- `self-review + check`
- `finish-work`
- `record-session`

### Usually No Workflow Branch

- `test-first + start`

## Files Modified In This Session

- `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/命令映射.md`
- `docs/workflows/新项目开发工作流/完整流程演练.md`

## Remaining Follow-Up

1. Human review the new walkthrough against intended reader flow
2. Decide whether `docs/README.md` needs a repo-level pointer to this workflow entry
3. Commit the workflow doc changes
4. Run `record-session` only after commit exists

## Notes For Next Session

- The current PRD already contains the decision trail.
- `findings.md` is the implementation handoff summary.
- Start the next session from this task directory, not from scratch.

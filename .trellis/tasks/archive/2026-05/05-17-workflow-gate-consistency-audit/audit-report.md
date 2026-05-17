# Audit Report: 新项目开发工作流强门禁一致性问题

## Audit Boundary

- Workflow Path: `docs/workflows/新项目开发工作流`
- Target Project: `/tmp/trellis-0.5.16-2`
- Compatible Anchor Version: `0.5.16`
- Current Trellis Version: `0.5.16`
- Target Project Trellis Version: `0.5.16`
- Version Gate: passed
- Current CLI: OpenCode
- Agent Use: forbidden by user instruction
- Formal Execution Status: in progress (audit + remediation)

## Evidence Collected

| Source Layer | Evidence | Status |
| --- | --- | --- |
| source repo | `docs/workflows/新项目开发工作流/commands/workflow_assets.py` declares `COMPATIBLE_TRELLIS_VERSION = "0.5.16"` | recorded |
| runtime command output | `trellis -v` returned `0.5.16` | recorded |
| generated target project workflow-installed state | `/tmp/trellis-0.5.16-2/.trellis/.version` contains `0.5.16` | recorded |
| generated target project workflow-installed state | `/tmp/trellis-0.5.16-2/.trellis/workflow-installed.json` records `profile: outsourcing` and `workflow_version: 0.1.28` | recorded |
| target session-start hook | `.claude/hooks/session-start.py` line 304: no-task guidance directs to `trellis-brainstorm` + `task.py create` without feasibility gate check | confirmed |
| target route script | `.trellis/scripts/workflow/workflow-state.py` line 1198: `profile_hint = "personal"` set when `assessment.md` missing, regardless of `workflow-installed.json` profile | confirmed |
| target finish-work skill | `.agents/skills/trellis-finish-work/SKILL.md` Steps 1-4 describe archive + record-session; lines 111-119 patch override says finish-work does NOT execute archive/add_session | confirmed |
| target task.py | `.trellis/scripts/task.py` line 96: degraded mode returns exit 0 + sets status=in_progress when no session identity; workflow.md line 76 claims it "fails" | confirmed |
| target spec directories | `.trellis/spec/scenarios/` and `.trellis/spec/universal-domains/` exist but have no `index.md` files; `get_context --mode packages` lists them but Pre-Development Checklist is unavailable | confirmed |
| target workflow.md | Phase 1/2/3 structure is standard Trellis baseline template; 12-stage strong-gate stages are added via projectization patch; no conflict | confirmed (not a defect) |
| target stage-switch quick reference | Step B is the post-confirmation command; two-step protocol described in preceding text; Step A shows readiness condition/command | confirmed (not a defect) |

## Candidate Issue Matrix

| ID | Hypothesis | Status | Source Layer | Validation |
| --- | --- | --- | --- | --- |
| C1 | Old Phase 1/2/3 model remains in target `.trellis/workflow.md` and conflicts with 12-stage strong gates | **false-alarm** | target workflow.md | Phase 1/2/3 is standard baseline; strong-gate stages added via patch; no conflict |
| C2 | Claude `SessionStart` no-task prompt may bypass feasibility by directing users to brainstorm/create task | **confirmed** | target `.claude/hooks/session-start.py` | Line 304: no-task guidance → `trellis-brainstorm` + `task.py create`; AGENTS.md NL routing table requires feasibility for outsourcing, but hook guidance bypasses it |
| C3 | Initial profile hint incorrectly falls back to personal despite installed `profile: outsourcing` | **confirmed** | target `workflow-state.py` | Line 1198: `profile_hint = "personal"` when `assessment.md` missing; `workflow-installed.json` has `profile: outsourcing` but route ignores it |
| C4 | Stage-switch quick reference commands omit the required `awaiting_user_confirmation` pre-state | **false-alarm** | target workflow.md | Step B is post-confirmation command; two-step protocol in preceding text; Step A shows readiness condition |
| C5 | `trellis-finish-work` contains contradictory archive/add_session instructions | **confirmed** | target `.agents/skills/trellis-finish-work/SKILL.md` | Steps 1-4 describe archive + record-session; patch (line 111-119) says finish-work does NOT execute them; direct contradiction |
| C6 | `task.py start` degraded mode behavior differs from workflow docs | **confirmed** | target `task.py` + `workflow.md` | task.py line 96: degraded mode → exit 0 + status=in_progress; workflow.md line 76: claims "fails with session identity hint" |
| C7 | Imported universal/scenario specs are not discoverable through ordinary context injection | **confirmed** | target `.trellis/spec/` | `scenarios/` and `universal-domains/` have no `index.md`; `get_context --mode packages` lists them but Pre-Development Checklist unavailable |

## Repair Log

### R1: C2 — session-start no-task guidance bypasses feasibility (source patch)

**File**: `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md` or equivalent install-time patch
**Fix**: Update the session-start no-task guidance to reference the AGENTS.md NL routing table for profile-specific entry routing, rather than unconditionally directing to brainstorm/create task.

### R2: C3 — profile_hint fallback ignores workflow-installed.json (source patch)

**File**: `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` or equivalent install-time patch
**Fix**: In `cmd_route`, when `assessment.md` is missing, check `workflow-installed.json` for the actual profile before defaulting to "personal".

### R3: C5 — trellis-finish-work contradictory instructions (source patch)

**File**: `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
**Fix**: The patch already correctly describes the override. The issue is in the target's SKILL.md where the patch is applied. The fix is to ensure the install-time patch clearly marks Steps 3-4 as overridden, not just appended.

### R4: C6 — task.py start degraded mode docs inconsistency (source docs)

**File**: `docs/workflows/新项目开发工作流/工作流总纲.md` or workflow.md patch
**Fix**: Update the workflow documentation to accurately describe `task.py start` degraded mode behavior: returns exit 0, sets status=in_progress, writes degraded fallback file.

### R5: C7 — imported specs lack index.md (source docs/installer)

**File**: `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md` or installer logic
**Fix**: Document that imported spec directories from library packs need `index.md` files for discoverability, or update the installer to generate them.

## Verification Log

| Check | Result | Details |
| --- | --- | --- |
| `test_workflow_state.py` | ✅ 68 tests OK | All route/profile tests pass |
| `test_workflow_installers.py` (finish_work) | ✅ 7 passed | finish-work patch tests pass |
| `test_workflow_installers.py` (profile/route) | ✅ 4 passed | profile hint and route tests pass |
| `trellis-library/cli.py validate --strict-warnings` | ✅ INFO only | 5 stale-related-asset warnings (informational, not errors) |
| `test_workflow_state.py` (route/profile) | ✅ 17 passed | Route and profile hint tests pass |

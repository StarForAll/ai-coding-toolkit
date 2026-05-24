# Embedded Workflow Audit Notes

## Boundary

- Source workflow root: `docs/workflows/新项目开发工作流/`
- Generated target project: `/tmp/trellis-0.5.17-2`
- Compatible anchor: `0.5.17`
- Runtime `trellis -v`: `0.5.17`
- Current conclusion scope: pre-repair audit only; no source edits performed yet

## Confirmed Non-Issues / Already Covered

### 1. `workflow-state.json` vs `task.json.status` double-truth conflict

- User hypothesis is **not true in the current embedded target project**.
- Evidence:
  - `/.trellis/scripts/common/tasks.py` derives live task status from `workflow-state.json.stage`
  - `/.trellis/scripts/task.py list --status <stage>` filters on derived `t.status`, not raw `task.json.status`
  - `/.trellis/scripts/common/task_queue.py` no longer treats `planning` as the pending-task subset
  - `/.trellis/scripts/task.py start` only prints the strong-gate skip message instead of flipping `planning -> in_progress`
- Remaining use of `task.json.status` is coarse lifecycle bookkeeping (`planning`, archive-time `completed`), not live stage routing.

### 2. `repair` asymmetry for execution stages

- **Not a live defect**; current implementation intentionally hard-blocks execution-stage repair without explicit confirmation fields.
- Evidence:
  - `commands/shell/workflow-state.py cmd_repair()`
  - `manual_confirmation_required` is emitted when execution-stage repair lacks `--execution-authorized true` / `--transition-from`
  - `commands/start-patch-phase-router.md` already documents the same rule

### 3. personal profile brainstorm bootstrap assessment timing

- **No runtime gap found**.
- Evidence:
  - `commands/brainstorm.md` already requires bootstrap assessment to be filled inside brainstorm and not deferred to design/plan
  - `commands/shell/state_utils.py:is_personal_brainstorm_bootstrap_allowed()`
  - `commands/shell/workflow-state.py route/validate/set`
  - tests cover warning-while-in-brainstorm and blocker-on-exit behavior

### 4. `profile_hint=unknown` handling

- **No functional defect found**.
- Evidence:
  - `workflow-state.py route` returns `profile_hint=unknown`
  - `reason` explicitly instructs the AI/user to confirm whether the project is `personal` or `outsourcing`
  - tests cover the `unknown -> feasibility fallback` path

### 5. Baseline Step Compatibility section

- **Not redundant in the current contract**.
- Evidence:
  - `commands/workflow-patch-projectization.md` explicitly says it preserves `get_context.py --mode phase --step <X.Y>` compatibility
  - installer tests and `patch-workflow-phase.py` still depend on that baseline step lookup contract

### 6. implementation-stage research ability with subagents disabled

- **Capability exists today**.
- Evidence:
  - installed `trellis-continue` skill defines main-session `research -> implement -> check`
  - target-project `AGENTS.md` routes research intent back to the current main session and explicitly forbids agent/subagent dispatch

## Confirmed Real Issues

### A. `embed_integrity.py` is too brittle and over-blocking

- Current behavior upgrades multiple non-runtime-fatal conditions directly to `embed_invalid`, which stops route re-entry entirely.
- Evidence:
  - `commands/shell/embed_integrity.py`
  - `detect_embed_invalid()` blocks on:
    - missing patch markers
    - patched codex skill semantic drift
    - distributed command cross-platform content drift
  - there is no warning/advisory mode; only fatal invalidation
- Why this is a real problem:
  - target projects can end up with harmless carrier-local edits or semantically equivalent patch movement
  - exact marker/hash dependence is fragile for long-lived embedded workflows
  - route becomes unavailable even when runtime-critical behavior is still intact

### B. Gate-validator diagnostics are truncated too aggressively

- The problem is not process count alone; it is **lossy failure reporting**.
- Evidence:
  - `commands/shell/state_utils.py:summarize_validator_output()` returns only the last non-empty line
  - `validators_gates.py` calls external validators that print multiple detailed failures
  - route blockers therefore collapse rich validator output into a single trailing line per validator
- Why this is a real problem:
  - user-facing blockers lose actionable detail
  - repeated repair cycles become more likely because earlier failure lines are hidden

### C. `_workflow_display_extra` is user-visible but undocumented

- Evidence:
  - `task.py list` prints `{...}` extra status hints derived from `_workflow_display_extra`
  - `common/tasks.py` populates it from `workflow-state.json`
  - no workflow docs currently explain what these braces mean or whether users should edit the field
- Why this is a real problem:
  - target-project users see `{block=...}` / `{status=...}` in task lists with no explanation
  - maintainers have no documented contract for the field

### D. `plan` stage Context7 scope is only fully defined in `design`, not where the gate is enforced

- Evidence:
  - `plan.md` gate text says “与已确认技术架构直接相关的全部 spec”
  - the concrete boundary (“third-party-doc-constrained specs must be reviewed; pure internal/team/project-private specs do not require Context7”) is documented in `design.md` / installed `design` skill, not in `plan.md`
- Why this is a real problem:
  - the gating stage is `plan`
  - a reader entering from `plan` alone can still treat the phrase as ambiguous

### E. Change-management “pure clarification” lacks a conservative fallback rule

- Evidence:
  - `需求变更管理执行卡.md` currently uses five binary checks
  - there is no explicit “if unsure, default to formal change management” rule
- Why this is a real problem:
  - ambiguous clarifications can be silently absorbed into the current stage
  - the workflow should bias toward escalation when impact is uncertain

## Partial / Low-Risk Clarity Issues

### F. “触发词” wording is underspecified

- Current behavior is not broken, but the wording can mislead readers into treating trigger text as a hard route rather than heuristic metadata.
- Evidence:
  - frontmatter descriptions with `触发词`
  - target-project routing also depends on stage gates, AGENTS tables, and platform-specific skill/command carriers
- Suggested direction:
  - rename or annotate as `自然语言路由提示 / 适用场景`
  - state explicitly that stage gates override trigger hits

## Proposed Repair Directions (Pending User Approval)

1. `embed_integrity.py`
   - split checks into:
     - fatal runtime-break checks
     - advisory drift checks
   - accept either semantic-fragment validation or multiple marker variants for route patches
   - keep fatal behavior for missing helper files, syntax errors, missing critical route functionality
   - downgrade pure marker/hash drift to warnings surfaced by route / validation output

2. Gate validator summarization
   - keep current validator scripts
   - replace “last line only” summarization with a compact multi-line failure summary built from `❌` lines or the first few meaningful lines
   - avoid a large validator merge refactor in this patch

3. `_workflow_display_extra` docs
   - document it as a derived, read-only display hint sourced from `workflow-state.json`
   - explain the brace output in task lists and give examples

4. Context7 scope docs
   - add the explicit “third-party-doc-constrained vs internal-only” boundary to `plan.md`
   - cross-link the same definition in `命令映射.md` / related stage docs if needed

5. Change-management conservative fallback
   - add “无法确定时，默认按正式变更处理” to:
     - `需求变更管理执行卡.md`
     - propagated references such as `命令映射.md` / `工作流总纲.md`

6. Trigger-word wording cleanup
   - optional low-risk doc-only cleanup if bundled with the above propagation pass

## Recommended Repair Priority

1. `embed_integrity.py` brittleness / over-blocking
2. Gate-validator diagnostic loss
3. `_workflow_display_extra` documentation
4. Context7-scope clarity in `plan`
5. Conservative fallback for pure clarification
6. Trigger-word wording cleanup

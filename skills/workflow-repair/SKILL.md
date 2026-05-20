---
name: workflow-repair
description: Apply safe source-workflow fixes from a `WORKFLOW_QUESTIONS.md` report, including recurring findings from earlier repair attempts. Use when re-checking an embedded Trellis temp project report and repairing `docs/workflows/新项目开发工作流/`.
compatibility: Requires `trellis` on PATH, access to the temp project report plus the workflow source repo, and inline CLI execution with local filesystem access.
---

# workflow-repair

## Version History

- **v1.4**: Added recurrence-closure, contract-surface coverage, and anti-regression gates to reduce repeated repairs and leftover issues
- **v1.3**: Aligned frontmatter with the latest public skill spec by making the description explicitly cover both purpose and trigger, and by adding compatibility requirements
- **v1.2**: Replaced misleading fixed example paths and task-directory placeholders with runtime-sensitive placeholders
- **v1.1**: Clarified temp-project-first verification, explicit repair authorization, no-agent execution, and same-pattern variant handling
- **v1.0**: Initial release

## Purpose

Consume a `WORKFLOW_QUESTIONS.md` report produced by `workflow-scan`, verify each finding against the temp project and the source project, and apply safe repairs to workflow source files — ONLY within `docs/workflows/新项目开发工作流/`.

This skill is the **consumer/fixer** half of the `workflow-scan` / `workflow-repair` coupled pair.

Its target of judgment is still the embedded workflow result in `/tmp/trellis-{VERSION}-2`; the source repository is the repair location, not the primary truth source for whether a reported issue exists.

## When to Use

Use this skill when any of the following is true:

- a `WORKFLOW_QUESTIONS.md` report exists in the temp project and needs to be consumed
- the user wants to analyze `/tmp/trellis-{VERSION}-2` and fix the source workflow based on real confirmed problems
- the user asks to "repair workflow issues" or "fix workflow findings"
- the user asks to "apply workflow corrections" or "run workflow-repair"
- the same class of workflow issue has already reappeared after one or more earlier repair attempts
- a workflow-scan cycle has completed and the repair phase should begin

## When Not to Use

- you need to scan for issues first: use `workflow-scan` in the temp project
- you need a comprehensive audit with version gates and runtime validation: use `workflow-audit`
- you need version-drift analysis: use `workflow-capability-audit`
- you are doing a normal implementation task without workflow repair

## Core Rules

1. **Fix scope**: ONLY modify files within `docs/workflows/新项目开发工作流/` (and the current task directory for the repair log). No other directories.
2. **Main CLI only**: do not use agents, sub-agents, or task orchestration to perform the repair. Work directly in the current CLI session.
3. **Temp-project-first verification**: the report and the temp project are the primary behavior evidence. The source repo explains and repairs the issue, but does not by itself prove the issue exists.
4. **Do no harm**: must not introduce new problems when fixing. Every proposed change must include side-effect analysis.
5. **Explicit repair language counts as authorization**: if the current user instruction already says to fix real confirmed issues, that instruction counts as permission after the correction plan is echoed. If the user only asked for analysis/judgment, stop after the plan.
6. **Reports are evidence, not truth**: re-check every finding. A scan finding is a hypothesis, not a confirmed fact.
7. **Task files persist**: task files (repair log, correction plan) are NOT deleted after completion — they serve as the permanent audit trail.
8. **Conservative adoption**: only adopt a fix where the repair is clear, minimal, and safe. If in doubt, mark as `manual-decision`.
9. **Root-cause closure is required**: do not stop at symptom repair. Every adopted or trellis-native fix must explain why the issue survived into the temp project and what source-side change closes that path.
10. **Variant sweep is required**: once a finding is confirmed, search only within `docs/workflows/新项目开发工作流/` for the same pattern or same root-cause class and fix safe siblings together.
11. **Contract-surface closure is required**: if a fix changes a behavior contract, path, marker, declaration, or workflow rule, update every in-scope source surface that must stay aligned in the same repair batch when safe. This can include scripts, docs, metadata declarations, and in-tree tests under the workflow directory.
12. **Repeated-findings escalation**: if a current finding matches a previously attempted repair cluster, do not repeat the same narrow patch blindly. Expand the investigation to the missed contract surfaces or mark the item `manual-decision`.
13. **Trellis-native routing**: when Origin = `trellis-native`, the fix must NOT modify files outside the workflow directory. Design a patch within the workflow so the installer can apply it (add patch script to `commands/`, update `HELPER_SCRIPTS`, or add overlay/post-install adjustment).
14. **Coupled contract**: this skill must consume WORKFLOW_QUESTIONS.md in the exact format defined in `skills/workflow-scan/references/scan-output-template.md`. If the protocol version does not match, stop.

## Inputs

| Input | Required | Default | Meaning |
|-------|----------|---------|---------|
| `report_path` | No | auto-detect | Absolute path to WORKFLOW_QUESTIONS.md |
| `temp_project_path` | No | from report | Absolute path to the temp project root |
| `target_focus` | No | empty | Specific WS-NNN IDs to prioritize |

### Report Path Resolution

1. If `report_path` is explicitly provided, use it.
2. Otherwise: run `trellis -v` to get VERSION, construct path `/tmp/trellis-{VERSION}-2/WORKFLOW_QUESTIONS.md`.
3. Validate: the file must exist and have `document-type: workflow-questions` in frontmatter.
4. If not found: stop as **Blocked / Report Not Found**.

### Source Project Root

The source project root is the repository where this skill runs (for example `<SOURCE_PROJECT_ROOT>`). Verify it matches the `source-project-root` field in the report frontmatter.

### Repair Authorization Mode

Determine execution mode from the current user request:

- If the user explicitly says to fix, repair, or process real confirmed issues, use `authorized-to-repair`.
- If the user asks only to analyze, judge, or produce a plan, use `analysis-only`.
- If ambiguous, default to `analysis-only`.

## Output

Two artifacts:

1. **Correction plan**: presented to the user inline (not written to file unless the user requests it). Format: see `references/correction-plan-template.md`.
2. **Repair log**: written to the current task directory (`.trellis/tasks/{task-id}/`). If no task is active, write to a timestamped file at the project root: `workflow-repair-log-{timestamp}.md`. Format: see `references/repair-log-template.md`.

## Workflow

### Step 0: Locate and Validate Report

1. Resolve the report path (see Path Resolution above).
2. Read WORKFLOW_QUESTIONS.md and validate frontmatter:
   - `document-type` must be `workflow-questions`
   - `protocol` must be `workflow-scan-repair-v1`
   - `source-project-root` must match the current working directory (or a parent of it)
3. Read version fields:
   - `trellis-version` from report vs `trellis -v` current
   - `workflow-version` from report vs `workflow_assets.py` current
4. Resolve the temp project root:
   - use `temp_project_path` if provided
   - otherwise read `temp-project-root` from the report
   - if neither is available, derive `/tmp/trellis-{VERSION}-2`
5. Determine repair authorization mode (see `Repair Authorization Mode` above).
6. If protocol mismatch: stop as **Blocked / Protocol Version Mismatch**.
7. If source-project-root mismatch: stop as **Blocked / Source Project Mismatch**.
8. If the temp project root does not exist or does not match the report context: stop as **Blocked / Temp Project Mismatch**.

### Step 1: Parse and Classify Findings

1. Extract all findings from the report. Each finding has: WS-NNN ID, Category, Severity Estimate, Origin, Evidence Layer, Evidence list, Temp Project Location, Suspected Source Location, Description, Suggested Investigation.
2. Group findings by Origin (`trellis-native` vs `workflow-source`).
3. Within each origin group, sort by Severity Estimate (P0 first, then P1, then P2).

### Step 2: Load Repair History and Recurrence Signals

Before verifying findings, inspect any prior repair history that is already available:

1. Check the current task directory for earlier workflow-repair logs.
2. If none exist there, check the project root for prior `workflow-repair-log-*.md` files.
3. For each current finding, look for recurrence clues:
   - same `WS-NNN` title or same source/temp location
   - same marker, path, command, hook, or helper-script contract
   - same failure theme described with different wording
4. Build a recurrence note for each finding:
   - `first-seen`
   - `repeated-after-prior-repair`
   - `no-history-found`
5. If a finding looks repeated after an earlier repair, require a broader contract-surface review before marking it `adopted`.

### Step 3: Verify Each Finding Against Temp Project and Source Project

For each finding, re-check against both the temp project and the source project:

1. Read the `Temp Project Location` artifact (if specified) in the temp project.
2. Read the `Suspected Source Location` file (if specified) in the source project.
3. Compare the temp-project behavior/evidence against the source-side declaration and the finding evidence.
4. Cross-reference with `workflow_assets.py` declarations and, when relevant, `commands/shell/init-trellis-temp-project.sh`.
5. Identify the root-cause class before deciding:
   - stale declaration drift
   - incomplete installer patch
   - partial cross-file update
   - wrong runtime assumption
   - missing cleanup / residual artifact
   - another clearly named root-cause class
6. Assign a verification result:
   - **Confirmed**: the finding is real in the temp project and the source workflow contains a clear, safe repair path → mark as `adopted`
   - **False alarm**: the finding is already fixed, was misidentified, or does not survive the temp-project/source cross-check → mark as `ignored`
   - **Blocked**: verification cannot proceed due to missing files, ambiguous paths, or external constraints → mark as `blocked`
   - **Needs user input**: the finding is real but the fix involves ambiguity, risk, or a trade-off → mark as `manual-decision`
   - **Trellis-native**: the issue is in a trellis-installed artifact, not workflow source → mark as `trellis-native`
7. Apply the **negative-optimization guardrail**: if a fix would change behavior that currently works correctly (even if the code looks wrong), prefer `manual-decision` over `adopted`.
8. If the item is a repeated finding and the current fix proposal does not explain why the earlier repair missed it, downgrade the item to `manual-decision` or `blocked`.

### Step 4: Variant Sweep Inside the Workflow Root

For every finding marked `adopted` or `trellis-native`:

1. Search only within `docs/workflows/新项目开发工作流/` for the same pattern, stale reference, script contract, or root-cause class.
2. Bundle same-root-cause variants into the same planned repair when:
   - the fix shape is materially the same
   - the added scope stays inside the workflow directory
   - the side effects remain understandable and low-risk
3. If a similar location might be affected but the root cause is not clearly the same, document it in the plan instead of auto-fixing it.
4. Record the sweep result in the correction plan and repair log, even if the result is `none`.

### Step 5: Build Contract-Surface Coverage Map

For every finding marked `adopted` or `trellis-native`:

1. Identify the source surfaces that should stay aligned if this fix is correct:
   - source script(s)
   - source markdown/doc references
   - `workflow_assets.py` declarations
   - in-tree tests under `docs/workflows/新项目开发工作流/commands/`
   - other workflow-local metadata or generated-source companions
2. Classify each surface:
   - `must-update`
   - `must-verify-only`
   - `out-of-scope-but-note`
3. If the issue came from a partially updated contract, do not plan a single-file fix when other `must-update` surfaces clearly exist.
4. Record the coverage map in the correction plan and later in the repair log.

### Step 6: Build Correction Plan

For each `adopted` or `trellis-native` finding:

1. Design the minimal fix:
   - File: relative path within `docs/workflows/新项目开发工作流/`
   - Before: description of current state
   - After: description of intended state
   - Change Type: add / modify / remove
   - Root Cause Class: the class identified in verification
   - Recurrence Status: `first-seen` | `repeated-after-prior-repair` | `no-history-found`
   - Related Variants Covered: the sibling files or patterns fixed together, or `none`
   - Contract Surfaces Covered: every `must-update` and `must-verify-only` surface, or `none`
2. Verify the fix does not introduce new problems:
   - Check downstream references that depend on the changed content
   - Check other CLI carriers that may be affected
   - Check `workflow_assets.py` consistency
   - Check whether the same stale marker/path/string still exists elsewhere in the workflow directory
3. Write side-effect analysis: list every downstream reference, CLI surface, or script affected and how.
4. For `trellis-native` findings: design a patch that lives within the workflow directory (typically a new or modified script in `commands/`) so the `install-workflow.py` installer can apply it.
5. For repeated findings: explicitly state why this plan is broader or safer than the earlier attempted repair.

For each `ignored` finding: document the reason.

For each `blocked` finding: document the blocker.

For each `manual-decision` finding: write a concrete question with trade-off explanation.

Format the complete correction plan using `references/correction-plan-template.md`.

### Step 7: Present Correction Plan and Decide Whether to Execute

1. Display the full correction plan inline.
2. If mode = `authorized-to-repair`, treat the current user instruction as standing authorization after the plan is echoed, unless the user explicitly limited the run to analysis only.
3. If mode = `analysis-only`, wait for explicit user confirmation. Options:
   - **Accept all**: apply all `adopted` and `trellis-native` fixes
   - **Accept partial**: specify which WS-NNN findings to apply
   - **Reject**: do not apply any changes
   - **Modify**: request adjustments to specific proposed fixes
4. If the user chooses **Modify**: adjust the specified fixes and re-present the updated plan before proceeding.

### Step 8: Execute Confirmed Repairs

1. Apply only the fixes the user confirmed.
2. For each fix:
   - Record the before state (key excerpt, not entire file)
   - Apply the change
   - Record the after state
   - Record the root-cause class and recurrence status
   - Record the related variants covered (or `none`)
   - Record the contract surfaces updated and verified
3. Scope enforcement: if a fix would modify a file outside `docs/workflows/新项目开发工作流/`, skip it and record the violation in the repair log.
4. For each applied fix, record in the per-fix section of the repair log.

### Step 9: Post-Repair Verification

For each applied fix, verify:

1. **Syntax check**: the modified file is syntactically valid (shell/Python script parses, markdown is well-formed).
2. **Cross-reference check**: references from the modified file still resolve to existing targets.
3. **Workflow-assets consistency**: the change does not contradict declarations in `workflow_assets.py` (e.g., HELPER_SCRIPTS, DISTRIBUTED_COMMANDS, RETIRED_HELPER_SCRIPTS).
4. **Variant sweep check**: the same-pattern locations that were intentionally fixed together now reflect the intended state.
5. **Contract-surface check**: every surface marked `must-update` or `must-verify-only` in the plan was actually updated or verified.
6. **Repeat-trigger check**: search the workflow directory for the stale marker/path/string/contract symptom that caused the current finding. If the same trigger still exists in an in-scope location, mark the fix `unverified`.
7. **Overall**: if all checks pass, mark as `verified`. If any fails, mark as `unverified` and record the failure.

If verification fails for a fix:
- Attempt to revert the change to the before state.
- Record the revert in the repair log.
- Mark the fix status as `failed` or `reverted`.

### Step 10: Write Repair Log and Stop

1. Write the repair log using `references/repair-log-template.md`.
2. Save to the current task directory (`.trellis/tasks/{task-id}/`) or a timestamped file at project root.
3. Echo the summary:
   - report path consumed
   - total findings processed
   - adopted / ignored / blocked / manual-decision / trellis-native counts
   - succeeded / failed / skipped counts
   - repair log path
4. Suggest the next step:
   - Re-run `workflow-scan` on a fresh temp project to verify repairs took effect
   - Or run `workflow-audit` for comprehensive validation
5. Do not delete task files or the repair log.

## Decision State Semantics

| State | Meaning | Action |
|-------|---------|--------|
| `adopted` | Finding confirmed, fix is clear, minimal, and safe | Apply the fix after user confirms the plan |
| `ignored` | Finding is false alarm, already fixed in source, or not actionable | No action needed; document the reason |
| `blocked` | Verification or repair cannot proceed due to external constraint | Report blocker; no fix attempted |
| `manual-decision` | Finding is real but fix involves ambiguity, risk, or trade-off | Present the question to the user; do not auto-adopt |
| `trellis-native` | Issue is in trellis-installed artifact, not workflow source | Design a patch within the workflow so the installer can apply it |

## Error Handling

| Case | Behavior |
|------|----------|
| Report not found | Stop as **Blocked / Report Not Found**. Suggest running `workflow-scan` first. |
| Protocol version mismatch | Stop as **Blocked / Protocol Version Mismatch**. The report was produced by a different protocol version. |
| Source project mismatch | Stop as **Blocked / Source Project Mismatch**. The report's `source-project-root` does not match the current project. |
| Temp project mismatch | Stop as **Blocked / Temp Project Mismatch**. The report and the live temp project do not line up. |
| Repeated finding with no broader safe fix | Stop as **Blocked / Repeated Finding Needs Broader Closure**. Do not repeat a previously narrow patch without a stronger closure plan. |
| No findings in report | Write repair log with `total-attempted: 0` and all counts at 0. |
| Fix scope violation | Skip the fix, record the violation in the repair log. Do not modify files outside `docs/workflows/新项目开发工作流/`. |
| Post-repair verification failure | Revert the change, record the failure and revert in the repair log. |
| User rejects all | Write repair log with all findings as `skipped`. No files modified. |

## Related Skills

- `workflow-scan`: analyzer/producer pair — produces the WORKFLOW_QUESTIONS.md this skill consumes
- `workflow-audit`: comprehensive audit with version gates, evidence mainline, and runtime validation (complementary, not replacement)
- `workflow-capability-audit`: version-drift audit

## Examples

### Example 1: Standard Repair Cycle

```text
User: /workflow-repair

AI:
1. Auto-detect report from the current `trellis -v` result: `/tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md`
2. Validate frontmatter: protocol=workflow-scan-repair-v1, source-project matches
3. Resolve temp project root from the report
4. Parse 5 findings: P0×1, P1×2, P2×2
5. Load prior repair logs and classify recurrence risk
6. Verify each against the temp project and source workflow:
   - WS-001 (P0): confirmed → adopted
   - WS-002 (P1): source already fixed → ignored
   - WS-003 (P1): confirmed, but fix risky → manual-decision
   - WS-004 (P2): trellis-native → trellis-native
   - WS-005 (P2): false alarm → ignored
7. Run the same-pattern sweep inside `docs/workflows/新项目开发工作流/`
8. Build the contract-surface coverage map
9. Build correction plan for WS-001, WS-003, WS-004
10. The user already asked to fix real confirmed issues, so the echoed plan counts as authorization
11. Apply WS-001 and WS-004 fixes
12. Post-repair verification: syntax, cross-reference, workflow-assets, contract-surface, and repeat-trigger checks all pass
13. Write repair log to `.trellis/tasks/{task-id}/`
14. Echo:
    ✅ Workflow repair complete
    📄 Report consumed: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
    📊 Findings: 5 total (adopted: 1, ignored: 2, blocked: 0, manual: 1, trellis-native: 1)
    🔧 Applied: 2 succeeded, 0 failed, 1 skipped
    📝 Repair log: .trellis/tasks/{task-id}/workflow-repair-log.md
    ➡️ Next: re-run /workflow-scan on a fresh temp project to verify
```

### Example 2: Report Not Found

```text
User: /workflow-repair

AI:
❌ Blocked / Report Not Found
   Expected: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   The file does not exist at the expected path.
   Suggestion: run /workflow-scan first to produce the report.
```

### Example 3: Analysis Only, No Auto-Repair

```text
User: /workflow-repair

AI:
1. Load prior repair logs to see whether the same finding cluster already reappeared
2. Verify 3 findings against the temp project and source workflow
3. Build correction plan (2 adopted, 1 ignored)
4. Current user request asks only for judgment, so mode = analysis-only
5. Present plan and stop for confirmation
6. No files modified yet

   ⏸ Workflow repair paused for confirmation
   📊 Findings: 3 total (adopted: 2, ignored: 1)
   🔧 Applied: 0 so far
   📝 Repair log: not written yet
```

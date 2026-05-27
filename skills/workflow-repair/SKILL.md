---
name: workflow-repair
description: Apply safe source-workflow fixes from a `WORKFLOW_QUESTIONS.md` report. Use when re-checking an embedded Trellis temp project report, consulting prior workflow issue history, and repairing `docs/workflows/新项目开发工作流/`.
compatibility: Requires `trellis` on PATH, access to the temp project report plus the workflow source repo, ability to run `task.py create` and `task.py start`, and inline CLI execution with local filesystem access. Repair itself remains main-session inline, but it accepts validated reports produced by either inline `workflow-scan` runs or explicit `workflow-scan --agent` runs. When `--auto` is requested, the current session is expected to support the repository's normal task close-out flow, including current-task `continue` re-entry, commit confirmation, and a reachable Trellis `finish-work` surface exposed either as a command or as a same-session skill; if both surfaces are unavailable at the moment they are needed, auto follow-through stops gracefully at the blocker.
---

# workflow-repair

## Version History

- **v3.1**: Clarified that repair-side defect judgment in this skill version is
  limited to Claude Code / OpenCode / Codex workflow surfaces; findings that
  only depend on other CLI usage stay out of scope unless the managed surface
  later expands
- **v3.2**: Clarified that valid `.backup-original/` carrier trees paired with
  active patched/overlay assets default to `ignored`, not repairable defects
- **v3.0**: Upgraded the shared contract to `workflow-scan-repair-v4`,
  requires three-way same-version report validation, replaces cross-version
  issue-history memory with task-local closure artifacts, and makes bounded
  closure part of repair convergence

- **v2.8**: Added report-side repair-classification gating so
  `confirmed-defect` is the only default repair-ready class, while
  `design-debt` and `evidence-gap` stop conservative by default, and upgraded
  the prior shared report contract to `workflow-scan-repair-v3`
- **v2.7**: Tightened `--auto` commit-scope confirmation boundaries so mixed-
  scope prompts and misleading all-success/result wording block instead of
  auto-confirming, and formally defined `current repair-task artifacts`
- **v2.6**: Expanded `--auto` commit-confirmation detection to accept explicit
  current-task commit-plan/scope confirmations that enumerate proposed commits
  or task-local artifacts while still asking for one-shot `ok`/yes approval
- **v2.5**: Refined `--auto` into a current-task Trellis close-out loop driven
  by `continue` first, added command-surface to skill-surface fallback rules
  for `continue` / `finish-work`, and defined stop conditions when `continue`
  closes the task or cannot safely advance further
- **v2.4**: Added explicit `--auto` follow-through mode so repair can continue
  into task close-out only after successful repair verification, using current-
  task-scoped commit confirmation plus the platform's available Trellis
  finish-work command surface
- **v2.3**: Clarified that repair-side intake is execution-mode agnostic and
  depends only on the validated `WORKFLOW_QUESTIONS.md` contract, whether the
  scan ran inline or with explicit `--agent` assistance
- **v2.2**: Clarified that successful `workflow-scan` output must already pass
  scan-side read-back validation and that repair-side intake stops when the
  shared report contract is still incomplete
- **v2.1**: Added mandatory repair-task bootstrap, `tmp/workflow-issues/` history documents, all-history replay on every run, strict-review completion rules without mandatory re-embed, and expanded write-scope rules for task and issue-history artifacts
- **v2.0**: Aligned intake with temp-project-only scan reports; removed source-project-root matching and source-location requirements from the shared report contract
- **v1.4**: Added recurrence-closure, contract-surface coverage, and anti-regression gates to reduce repeated repairs and leftover issues
- **v1.3**: Aligned frontmatter with the latest public skill spec by making the description explicitly cover both purpose and trigger, and by adding compatibility requirements
- **v1.2**: Replaced misleading fixed example paths and task-directory placeholders with runtime-sensitive placeholders
- **v1.1**: Clarified temp-project-first verification, explicit repair authorization, no-agent execution, and same-pattern variant handling
- **v1.0**: Initial release

## Purpose

Consume a `WORKFLOW_QUESTIONS.md` report produced by `workflow-scan`, verify
each finding against the temp project and the source project, and apply safe
repairs to workflow source files — ONLY within
`docs/workflows/新项目开发工作流/`.

This skill is the **consumer/fixer** half of the `workflow-scan` /
`workflow-repair` coupled pair.

Its target of judgment is still the embedded workflow result in
`/tmp/trellis-{VERSION}-2`; the source repository is the repair location, not
the primary truth source for whether a reported issue exists.

This skill now requires bounded same-run closure verification using fresh
task-local fixtures. Strict source-side review still matters, but it is no
longer the only convergence gate.

## When to Use

Use this skill when any of the following is true:

- a `WORKFLOW_QUESTIONS.md` report exists in the temp project and needs to be
  consumed
- the user wants to analyze `/tmp/trellis-{VERSION}-2` and fix the source
  workflow based on real confirmed problems
- the user asks to "repair workflow issues" or "fix workflow findings"
- the user asks to "apply workflow corrections" or "run workflow-repair"
- the user wants the repair flow to continue automatically into normal task
  close-out by explicitly adding `--auto`
- the same class of workflow issue has already reappeared after one or more
  earlier repair attempts
- a workflow-scan cycle has completed and the repair phase should begin

## When Not to Use

- you need to scan for issues first: use `workflow-scan` in the temp project
- you need a comprehensive audit with version gates and runtime validation: use
  `workflow-audit`
- you need version-drift analysis: use `workflow-capability-audit`
- you are doing a normal implementation task without workflow repair

## Core Rules

1. **Fix scope**: ONLY modify files within
   `docs/workflows/新项目开发工作流/`, the current repair task directory, and
   `tmp/workflow-issues/`. No other directories.
2. **Main CLI only**: do not use agents, sub-agents, or task orchestration to
   perform the repair. Work directly in the current CLI session.
3. **Temp-project-first verification**: the report and the temp project are the
   primary behavior evidence. The source repo explains and repairs the issue,
   but does not by itself prove the issue exists.
4. **Do no harm**: must not introduce new problems when fixing. Every proposed
   change must include side-effect analysis and strict source-side review.
5. **Explicit repair language counts as authorization**: if the current user
   instruction already says to fix real confirmed issues, that instruction
   counts as permission after the correction plan is echoed. If the user only
   asked for analysis/judgment, stop after the plan.
6. **Reports are evidence, not truth**: re-check every finding. A scan finding
   is a hypothesis, not a confirmed fact.
7. **Dedicated repair task is required**: this skill must always run inside a
   dedicated trellis repair task. If there is no active task, create one and
   continue. If there is already an active task, create a new repair task and
   switch to it instead of reusing the existing task.
8. **Same-version truth only**: repair may consume only reports whose
   workflow-version matches the temp-project install record and the current
   source `WORKFLOW_VERSION`.
9. **Cross-version issue-history replay is removed**: old
   `tmp/workflow-issues/` memory is not part of the `v4` repair decision path.
10. **Repair artifacts persist**: task files remain the audit trail, including
    task-local closure-round artifacts.
11. **Conservative adoption**: only adopt a fix where the repair is clear,
    minimal, and safe. If in doubt, mark as `manual-decision`.
12. **Root-cause closure is required**: do not stop at symptom repair. Every
    adopted or trellis-native fix must explain why the issue survived into the
    temp project and what source-side change closes that path.
13. **Variant sweep is required**: once a finding is confirmed, search only
    within `docs/workflows/新项目开发工作流/` for the same pattern or same
    root-cause class and fix safe siblings together.
14. **Contract-surface closure is required**: if a fix changes a behavior
    contract, path, marker, declaration, or workflow rule, update every
    in-scope source surface that must stay aligned in the same repair batch when
    safe. This can include scripts, docs, metadata declarations, and in-tree
    tests under the workflow directory.
15. **Bounded closure is required**: after source edits, repair must run fresh
    closure verification rounds and may not close out or bump the workflow
    version while unresolved new in-scope findings remain.
16. **Closure scope is bounded**: closure may auto-absorb only same-family,
    same-contract-surface findings. New-family findings stop automatic
    progression of the current repair batch.
17. **Trellis-native routing**: when Origin = `trellis-native`, the fix must
    NOT modify files outside the workflow directory. Design a patch within the
    workflow so the installer can apply it (add patch script to `commands/`,
    update `HELPER_SCRIPTS`, or add overlay/post-install adjustment).
18. **Round-local rollback**: if closure-added repairs fail inside a round, the
    round's additions must roll back without forcing a full repair-batch reset.
19. **Current closure truth wins**: current same-version closure evidence
    overrides older scan interpretation when they conflict.
20. **Coupled contract**: this skill must consume `WORKFLOW_QUESTIONS.md` in
    the exact format defined in
    `skills/workflow-scan/references/scan-output-template.md`. If the protocol
    version does not match, stop.
21. **Execution-mode agnostic intake**: repair-side validation depends on the
    final `WORKFLOW_QUESTIONS.md` contract only. A report produced by
    `workflow-scan --agent` is acceptable only if the coordinator's final
    output still passes the same shared read-back validation as an inline scan.
22. **No implied repair-side agent mode**: scan-side `--agent` support does
    not extend to `workflow-repair`. Repair remains main-CLI-only unless its
    own contract changes in a separate scoped update.
23. **`--auto` is explicit and gated**: auto follow-through is allowed only
    when the input explicitly includes `--auto`. It never bypasses correction-
    plan presentation, repair authorization, post-repair verification, current-
    task commit readiness, or the normal safety gates required before
    `finish-work`.
24. **Default repair-ready scope is narrow**: only findings whose report-side
    repair classification is `confirmed-defect` may enter the ordinary adopted
    repair path by default.
25. **Design debt is not auto-repair**: `design-debt` findings must default to
    `manual-decision` or `ignored` unless the user explicitly broadens scope
    beyond confirmed defects after the correction plan is shown.
26. **Evidence gaps block source edits**: `evidence-gap` findings must default
    to `blocked` or `manual-decision` until further temp-project or audit
    evidence closes the gap.
27. **Supported CLI defect scope is fixed for this skill version**: repair-side
    adoption may concern only the current workflow's Claude Code / OpenCode /
    Codex managed surfaces. If a finding depends only on behavior in some other
    CLI and does not break these three supported surfaces, it is out of scope
    and must not be treated as a current workflow defect.
28. **Preserved restore surfaces are not auto-defects**: findings that only
    complain about `.backup-original/` carrier trees must default to `ignored`
    when temp-project evidence shows those copies are intentional restore
    surfaces paired with active patched/overlay assets in
    `.trellis/workflow-installed.json`.

## Inputs

| Input | Required | Default | Meaning |
|-------|----------|---------|---------|
| `report_path` | No | auto-detect | Absolute path to `WORKFLOW_QUESTIONS.md` |
| `temp_project_path` | No | from report | Absolute path to the temp project root |
| `target_focus` | No | empty | Specific WS-NNN IDs to prioritize |
| `--auto` | No | off | After a successful repair run, continue into the current repair task's normal Trellis close-out flow instead of stopping at the repair summary. Eligible commit confirmations, independent scope proof, blocker rules, and post-commit continuation are defined in `Auto Follow-Through Mode` and Step 12.8 below. |

### Report Path Resolution

1. If `report_path` is explicitly provided, use it.
2. Otherwise: run `trellis -v` to get VERSION, construct path
   `/tmp/trellis-{VERSION}-2/WORKFLOW_QUESTIONS.md`.
3. Validate: the file must exist and have `document-type: workflow-questions`
   in frontmatter.
4. If not found: stop as **Blocked / Report Not Found**.

### Repair Authorization Mode

Determine execution mode from the current user request:

- If the user explicitly says to fix, repair, or process real confirmed issues,
  use `authorized-to-repair`.
- If the user asks only to analyze, judge, or produce a plan, use
  `analysis-only`.
- If ambiguous, default to `analysis-only`.
- If the request started as `analysis-only` and the user later explicitly
  accepts all or partial execution in Step 8, switch authorization mode to
  `post-plan-confirmation` for the actual repair execution, repair-log
  recording, and any later auto follow-through decisions.

### Auto Follow-Through Mode

Determine continuation mode from the current user request:

- If the user explicitly includes the literal `--auto` token, use
  `auto-follow-through`.
- Otherwise, use `stop-after-summary`.
- `--auto` changes only what happens after a successful repair run. It does not
  skip correction-plan presentation, repair authorization, post-repair
  verification, or any required Trellis close-out prerequisite.
- When `target_focus` explicitly narrows the repair scope, findings outside that
  focus do not participate in the close-out safety decision for `--auto`.
  If those out-of-focus findings carry higher severity, surface that fact in
  the correction plan so the user can see that auto close-out is proceeding on
  a narrowed repair scope rather than on a fully clean report.
- In `auto-follow-through` mode, if the current repair task reaches a normal
  close-out prompt that asks for its one-shot commit confirmation, including an
  explicit commit-plan/scope confirmation that asks for `ok`/yes-style
  approval while naming proposed commits, unrecognized working-tree files that the
  prompt explicitly frames as part of the current repair task's commit scope,
  or current repair-task artifacts, reply `ok` exactly once and continue.
- `unrecognized working-tree files` means working-tree paths that the close-out
  flow surfaces outside the proposed commit batches and requires the operator
  to include or exclude explicitly; they may be modified or untracked.
- `current repair-task artifacts` means any file that lives inside the current
  repair task directory and is being enumerated by the close-out flow as part
  of the task's commit scope.
- Current repair-task artifacts are acceptable by task-directory membership
  plus explicit current-task prompt scoping; they do not need separate current-
  run output proof.
- The current repair run's independently provable output set applies only to
  out-of-directory files from the skill's other allowed write-scope locations
  when this run can tie them to its own recorded outputs:
  - workflow source files changed by confirmed repair work under
    `docs/workflows/新项目开发工作流/`
  - the current run's own optional `tmp/workflow-issues/NNNN.md` audit shadow
- A file counts as tied to this run's recorded outputs only when the current
  run's repair log records it as a changed, written, or output file for this
  run.
- Exclude reverted files from that independently provable output set; a file
  changed and later reverted during post-repair verification is not a remaining
  current-run output for close-out.
- Reverted files inside the current repair task directory are likewise not
  remaining current-run outputs for close-out, even though the files still live
  in the task directory.
- If the prompt includes working-tree files outside the current repair task's commit
  scope, or the close-out flow does not make that scope explicit enough to
  prove current-task-only scope, stop and report the blocker instead of
  treating it as eligible for auto-confirmation.
- Minimum-acceptable explicit current-task scoping examples include wording
  such as `commit the current repair task changes`, `commit the current repair
  task artifacts`, or `commit the focused repairs` when the rest of the prompt
  stays consistent with that scope.
- Those examples are illustrative rather than exhaustive; semantically
  equivalent phrasing may also qualify when it meets the same explicit
  current-task scope bar.
- Insufficient scoping examples include wording such as `commit these changes`
  or `commit working tree changes` when they do not explicitly frame the scope
  as the current repair task.
- If the prompt's commit-scope or repair-result wording would materially
  misstate the actual repair outcome, such as implying that all attempted fixes
  are verified even though some were reverted, failed, left unresolved, or
  left out by `target_focus`, stop and report the blocker instead of
  auto-confirming it.
- Wording such as `commit the successful repairs` or `commit the current repair
  task changes` may be honest when it does not imply every attempted or every
  reported fix was verified and when the file list remains consistent with that
  narrower claim.
- Bounded auto-confirmation rule: per Step 12.8, reply `ok` exactly once, and
  only for the current repair task's eligible commit confirmation. Here
  `exactly once` means once per close-out run for the first qualifying one-shot
  confirmation prompt, not once per subsequent qualifying prompt inside that
  same run and not once for the entire repair task across later resumed runs.
- If any other interactive prompt appears, stop and report the blocker instead
  of guessing a reply.
- In `auto-follow-through` mode, the post-repair close-out path must re-enter
  the current repair task's normal Trellis flow through the available
  `continue` surface before attempting `finish-work`.
- One close-out run means the full post-repair continuation sequence beginning
  with the first `continue` re-entry for this repair task and ending only when
  the task reaches `finish-work`, `reached-task-close`, or stops with a
  blocker.
- If a blocker ends that sequence and the task is later resumed, treat the
  resumed continuation as a new close-out run rather than as a continuation of
  the previous one.
- Treat a Trellis surface as available in this priority order:
  1. callable platform command surface for the current session
  2. same-session skill surface available in the current project/runtime
  Only when both are unavailable should the surface be treated as missing.
- For `continue`, examples include `trellis-continue` or
  `/trellis:continue` as command surfaces, plus a same-session
  `trellis-continue` skill surface when the platform exposes the behavior as a
  skill instead of a command.
- For `finish-work`, examples include `trellis-finish-work` or
  `/trellis:finish-work` as command surfaces, plus a same-session
  `trellis-finish-work` skill surface when the platform exposes the behavior as
  a skill instead of a command.
- If no Trellis `continue` surface is available in the current
  platform/session, stop and report the blocker. Do not simulate or replace
  `continue`.
- If no Trellis finish-work command surface is available in the current
  platform/session, fall back to the same-session `trellis-finish-work` skill
  surface when it exists.
- If no Trellis `finish-work` surface is available in the current
  platform/session after checking both the command surface and the same-session
  skill surface, stop and report the blocker. Do not simulate or replace
  `finish-work`.
- If the current task is not ready for commit or finish-work, stop after the
  repair summary and report the blocker instead of forcing completion.
- If authorization mode stays `analysis-only` and the user rejects or never
  confirms execution, `--auto` has no effect because no repair run completed.
- If the request also includes `--agent`, ignore that flag for mode expansion:
  repair remains main-session-only and `--auto` does not introduce any
  repair-side agent interaction.

### Optional Legacy Issue-History Shadow

Optional location: `tmp/workflow-issues/`

- A `v4` repair run may still write one numeric Markdown file there as an
  audit shadow.
- `v4` repair decisions must not depend on reading that directory as a
  cross-version memory source.

## Output

Four artifacts:

1. **Correction plan**: presented to the user inline (not written to file
   unless the user requests it). Format: see
   `references/correction-plan-template.md`.
2. **Repair log**: written to the current repair task directory. Format: see
   `references/repair-log-template.md`.
3. **Closure round artifacts**: written to the current repair task directory
   as `closure-round-<N>.md`. Format: see
   `references/closure-round-template.md`.
4. **Issue-history shadow**: optional, written to
   `tmp/workflow-issues/{NNNN}.md` only as an audit shadow. Format: see
   `references/issue-history-template.md`.

If continuation mode = `auto-follow-through`, the skill also continues into the
current task's normal close-out flow after these repair artifacts are written
and echoes that follow-through result inline.

## Workflow

### Step 0: Ensure Report Path and Repair Task Context

1. Resolve the report path (see Path Resolution above).
2. Read enough of the report to derive a short topic:
   - prefer `target_focus` when provided
   - otherwise use the first finding title if available
   - otherwise fall back to `workflow-issues`
3. Sanitize the short topic to a compact kebab-style fragment.
4. Check whether an active task already exists.
5. If there is **no** active task:
   - create a new task titled `workflow-repair-<date>-<short-topic>`
   - start that task
6. If there **is** an active task:
   - create a new task titled `workflow-repair-<date>-<short-topic>`
   - switch to the new repair task
   - do **not** reuse the previous task
7. From this point onward, all task-local artifacts belong to the dedicated
   repair task.
8. If task creation or task start fails: stop as
   **Blocked / Repair Task Setup Failed**.

### Step 1: Locate and Validate Report

1. Read `WORKFLOW_QUESTIONS.md` and validate frontmatter:
   - `document-type` must be `workflow-questions`
   - `protocol` must be `workflow-scan-repair-v4`
   - the shared scan-side report keys must still be present:
     `trellis-version`, `workflow-version`, `workflow-schema-version`,
     `scan-timestamp`, `temp-project-root`, `total-findings`, `p0-count`,
     `p1-count`, `p2-count`
   - required report sections must still exist:
     `## Scan Summary`, `## Analysis Summary`, and `### WS-NNN` finding blocks
   - the `total-findings`, `p0-count`, `p1-count`, and `p2-count` values must
     match the actual finding count and per-severity counts in the report body
   - each finding block must include `Repair Classification`
   - the analysis summary must expose `Confirmed Defects`,
     `Design-Debt Items`, and `Evidence-Gap Items`
2. Read version fields:
   - `trellis-version` from report vs `trellis -v` current
   - `workflow-version` from report
   - `workflow-schema-version` from report
   - current source `WORKFLOW_VERSION`
   - current source `WORKFLOW_SCHEMA_VERSION`
   - temp-project install-record `workflow_version`
   - temp-project install-record `workflow_schema_version`
3. Resolve the temp project root:
   - use `temp_project_path` if provided
   - otherwise read `temp-project-root` from the report
   - if neither is available, derive `/tmp/trellis-{VERSION}-2`
4. Determine repair authorization mode and continuation mode (see the
   `Repair Authorization Mode` and `Auto Follow-Through Mode` sections above).
   If the request also included `--agent`, note once that repair-side
   `--agent` is not supported and that any `--auto` follow-through still runs
   in main-session-only mode.
5. If protocol mismatch: stop as **Blocked / Protocol Version Mismatch**.
6. If report workflow version, temp-project install-record workflow version,
   and current source `WORKFLOW_VERSION` are not all equal: stop as
   **Blocked / Stale Scan Report** and tell the user to re-embed and re-run
   `workflow-scan`.
7. If the workflow versions match but any compared
   `workflow-schema-version` does not match the current source schema version:
   stop as **Blocked / Invalid Embedded State**.
8. If the temp project root does not exist or does not match the report
   context: stop as **Blocked / Temp Project Mismatch**.
9. If the shared keys/sections above are missing, treat the report as a
   scan-side contract failure and stop instead of trying to infer the intended
   fields from alternate names such as `generated_at`, `trellis_version`,
   `temp_project_path`, or `total_findings`.
10. Do not reject or special-case the report based on whether the scan was run
   inline or with `--agent`; only the validated document contract matters.

### Step 2: Parse and Classify Findings

1. Extract all findings from the report. Each finding has: WS-NNN ID, Category,
   Severity Estimate, Repair Classification, Origin, Evidence Layer, Evidence
   list, Temp Project Location, Description, Suggested Investigation.
2. Group findings first by Repair Classification (`confirmed-defect`,
   `design-debt`, `evidence-gap`).
3. Within each repair-classification group, group by Origin
   (`trellis-native` vs `workflow-source`).
4. Within each origin group, sort by Severity Estimate (P0 first, then P1,
   then P2).

### Step 2A: Apply The Default Repair-Eligibility Gate

Before any source-side fix decision is drafted:

1. `confirmed-defect` findings may proceed into the ordinary verification and
   adoption flow.
2. `design-debt` findings must not be treated as adopted-fix candidates by
   default.
   - Keep them at `manual-decision` when a broader design trade-off or explicit
     user scope choice is still needed.
   - Keep them at `ignored` when they are merely optimization ideas and the
     current request is still limited to real confirmed defects.
3. `evidence-gap` findings must not enter source-edit execution.
   - Keep them at `blocked` when more temp-project proof or broader audit
     evidence is needed.
   - Keep them at `manual-decision` only when the missing evidence can be
     closed by an explicit user decision rather than by guessing.
4. The correction plan must make this gating visible instead of silently
   treating every finding as equally repair-ready.

### Step 3: Build Same-Version Repair Context

Before verifying findings:

1. Check the current repair task directory for earlier repair logs or
   closure-round artifacts if this run is being resumed.
2. Treat same-version task-local closure artifacts as the only convergence
   memory surface for this repair task.
3. Do not read old `tmp/workflow-issues/` documents as cross-version repair
   memory in `v4`.
4. Build recurrence notes from current-task same-version evidence only:
   - `first-seen`
   - `repeated-within-current-repair`
   - `no-prior-task-evidence`

### Step 4: Verify Each Finding Against Temp Project and Source Project

For each finding, re-check against both the temp project and the source
project:

1. Read the `Temp Project Location` artifact (if specified) in the temp
   project.
2. Infer the likely source-side repair surface from the finding's temp-project
   evidence and description.
3. Read the relevant source-project file(s) needed to test that hypothesis.
4. Compare the temp-project behavior/evidence against the source-side
   declaration and the finding evidence.
5. Cross-reference with workflow-local declarations such as
   `workflow_assets.py` when relevant to the suspected repair path.
6. Identify the root-cause class before deciding:
   - stale declaration drift
   - incomplete installer patch
   - partial cross-file update
   - wrong runtime assumption
   - missing cleanup / residual artifact
   - another clearly named root-cause class
7. Assign a verification result:
   - **Confirmed**: the finding is real in the temp project and the source
     workflow contains a clear, safe repair path → mark as `adopted`
   - **False alarm**: the finding is already fixed, was misidentified, or does
     not survive the temp-project/source cross-check → mark as `ignored`
   - **Blocked**: verification cannot proceed due to missing files, ambiguous
     paths, or external constraints → mark as `blocked`
   - **Needs user input**: the finding is real but the fix involves ambiguity,
     risk, or a trade-off → mark as `manual-decision`
   - **Trellis-native**: the issue is in a trellis-installed artifact, not
     workflow source → mark as `trellis-native`
8. Apply the **negative-optimization guardrail**: if a fix would change
   behavior that currently works correctly (even if the code looks wrong),
   prefer `manual-decision` over `adopted`.
9. If the symptom depends only on a CLI outside the current supported
   three-platform surface (Claude Code / OpenCode / Codex), downgrade the item
   to `ignored` instead of treating it as a current workflow defect.
10. If the symptom is only that a managed `.backup-original/` carrier tree is
   present, and the temp project's install record plus active asset names show
   it is an intentional restore surface, downgrade the item to `ignored`
   instead of treating it as a current workflow defect.
11. If the item is a repeated finding and the current fix proposal does not
   explain why the earlier repair missed it, downgrade the item to
   `manual-decision` or `blocked`.

### Step 5: Variant Sweep Inside the Workflow Root

For every finding marked `adopted` or `trellis-native`:

1. Search only within `docs/workflows/新项目开发工作流/` for the same pattern,
   stale reference, script contract, or root-cause class.
2. Bundle same-root-cause variants into the same planned repair when:
   - the fix shape is materially the same
   - the added scope stays inside the workflow directory
   - the side effects remain understandable and low-risk
3. If a similar location might be affected but the root cause is not clearly
   the same, document it in the plan instead of auto-fixing it.
4. Record the sweep result in the correction plan, repair log, and any
   same-version closure-round artifacts, even if the result is `none`.

### Step 6: Build Contract-Surface Coverage Map

For every finding marked `adopted` or `trellis-native`:

1. Identify the source surfaces that should stay aligned if this fix is
   correct:
   - source script(s)
   - source markdown/doc references
   - `workflow_assets.py` declarations
   - in-tree tests under `docs/workflows/新项目开发工作流/commands/`
   - other workflow-local metadata or generated-source companions
2. Classify each surface:
   - `must-update`
   - `must-verify-only`
   - `out-of-scope-but-note`
3. If the issue came from a partially updated contract, do not plan a
   single-file fix when other `must-update` surfaces clearly exist.
4. Record the coverage map in the correction plan and later in the repair log.

### Step 7: Build Correction Plan

For each `adopted` or `trellis-native` finding:

1. Design the minimal fix:
   - File: relative path within `docs/workflows/新项目开发工作流/`
   - Before: description of current state
   - After: description of intended state
   - Change Type: add / modify / remove
   - Root Cause Class: the class identified in verification
   - Recurrence Status:
     `first-seen` | `repeated-within-current-repair` | `no-prior-task-evidence`
   - Related Variants Covered: the sibling files or patterns fixed together, or
     `none`
   - Contract Surfaces Covered: every `must-update` and `must-verify-only`
     surface, or `none`
2. Verify the fix does not introduce new problems:
   - Check downstream references that depend on the changed content
   - Check other CLI carriers that may be affected
   - Check `workflow_assets.py` consistency
   - Check whether the same stale marker/path/string still exists elsewhere in
     the workflow directory
   - Check whether same-version task-local evidence suggests closely related
     in-scope variants that should be fixed together or explicitly left
     unresolved
3. Write side-effect analysis: list every downstream reference, CLI surface, or
   script affected and how.
4. For `trellis-native` findings: design a patch that lives within the workflow
   directory (typically a new or modified script in `commands/`) so the
   `install-workflow.py` installer can apply it.
5. For repeated findings: explicitly state why this plan is broader or safer
   than the earlier attempted repair.

For each `ignored` finding: document the reason.

For each `blocked` finding: document the blocker.

For each `manual-decision` finding: write a concrete question with trade-off
explanation.

Format the complete correction plan using
`references/correction-plan-template.md`.

### Step 8: Present Correction Plan and Decide Whether to Execute

1. Display the full correction plan inline.
2. If mode = `authorized-to-repair`, treat the current user instruction as
   standing authorization after the plan is echoed, unless the user explicitly
   limited the run to analysis only.
3. If mode = `analysis-only`, wait for explicit user confirmation. Options:
   - **Accept all**: apply all `adopted` and `trellis-native` fixes
   - **Accept partial**: specify which WS-NNN findings to apply
   - **Reject**: do not apply any changes
   - **Modify**: request adjustments to specific proposed fixes
4. If the user chooses **Modify**: adjust the specified fixes and re-present
   the updated plan before proceeding.
5. If continuation mode = `auto-follow-through`, the presented plan must
   explicitly say that a successful run will continue into the current task's
   normal close-out flow, and that auto follow-through will stop and report a
   blocker if close-out cannot proceed safely.
   If the run started as `analysis-only` and later received explicit execution
   approval, ensure that the presented plan still includes the continuation
   mode / blocker disclosure before execution proceeds.

### Step 9: Execute Confirmed Repairs

1. Apply only the fixes the user confirmed.
2. For each fix:
   - Record the before state (key excerpt, not entire file)
   - Apply the change
   - Record the after state
   - Record the root-cause class and recurrence status
   - Record the related variants covered (or `none`)
   - Record the contract surfaces updated and verified
3. Scope enforcement: if a fix would modify a file outside
   `docs/workflows/新项目开发工作流/`, the current repair task directory, or
   `tmp/workflow-issues/`, skip it and record the violation in the repair log.
4. For each applied fix, record it in the per-fix section of the repair log.

### Step 10: Post-Repair Verification

No same-run re-embed is required. Instead, for each applied fix, verify:

1. **Syntax check**: the modified file is syntactically valid (shell/Python
   script parses, markdown is well-formed).
2. **Cross-reference check**: references from the modified file still resolve
   to existing targets.
3. **Workflow-assets consistency**: the change does not contradict declarations
   in `workflow_assets.py` (e.g., `HELPER_SCRIPTS`, `DISTRIBUTED_COMMANDS`,
   `RETIRED_HELPER_SCRIPTS`).
4. **Variant sweep check**: the same-pattern locations that were intentionally
   fixed together now reflect the intended state.
5. **Contract-surface check**: every surface marked `must-update` or
   `must-verify-only` in the plan was actually updated or verified.
6. **Repeat-trigger check**: search the workflow directory for the stale
   marker/path/string/contract symptom that caused the current finding. If the
   same trigger still exists in an in-scope location, mark the fix
   `unverified`.
7. **Task-evidence closure check**: compare the applied fixes against current
   task-local same-version evidence and confirm that clearly similar in-scope
   problems were either fixed together or explicitly recorded as unresolved.
8. **Overall**: if all checks pass, mark as `verified`. If any fails, mark as
   `unverified` and record the failure.

If verification fails for a fix:

- Attempt to revert the change to the before state.
- Record the revert in the repair log.
- Mark the fix status as `failed` or `reverted`.

### Step 10A: Run Bounded Closure Verification

After source-side verification succeeds for the applied fixes:

1. Create a fresh isolated fixture for each required closure scenario.
2. Run the default closure scenario `clean-outsourcing-all-cli`.
3. Expand closure scenarios mechanically only when the touched surface class
   requires it:
   - profile-specific logic → add `clean-personal-all-cli`
   - install / upgrade / cleanup / runtime-patch logic → add
     `existing-trellis-outsourcing-all-cli` and
     `existing-workflow-outsourcing-all-cli`
4. Write one `closure-round-<N>.md` artifact for each closure round.
5. For every closure finding:
   - assign a task-local closure ID such as `CR1-F01`
   - record `issue-family-id`, `scenario-id`, `round`, `in-scope`, and
     `disposition`
6. If closure discovers a new in-scope finding in the same family and same
   contract surface:
   - absorb it only within the bounded same-family closure rules
   - allow at most two closure absorb rounds
7. If closure discovers a new family:
   - stop automatic progression of the current batch
   - return to a planning / decision checkpoint
   - do not close out or bump the workflow version
   - record the round outcome as `needs-audit`
8. If any new in-scope finding remains unresolved at the end of closure:
   - stop the run from close-out
   - do not bump the workflow version
9. If closure-added repairs fail within a round:
   - roll back that round's additions
   - record the rollback in the closure-round artifact and repair log
10. If closure remains non-converged after the allowed same-family absorb
    rounds, stop as broader non-convergence rather than continuing indefinitely
    and record the round outcome as `needs-audit`.

### Step 10B: Bump Workflow Version After Converged Repair

Use this step only when:

- at least one repair item finished as `verified`
- closure converged without unresolved in-scope findings
- repair-side source changes remain in place

Then:

1. Treat the repair run's starting `WORKFLOW_VERSION` as the base version.
2. Bump only the final numeric segment, for example:
   - `0.1.2800 -> 0.1.2801`
   - `0.1.9999 -> 0.1.10000`
3. Use the workflow-local helper when available:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/bump-workflow-version.py \
--expected-current <base-workflow-version> \
--summary "<one-line repair summary>"
```

4. Synchronize all active current-version references in the same change.
5. If the helper reports that the current version no longer matches the base
   version, stop instead of guessing which version to bump from.
6. If the run is no-op, reverted, failed, blocked from convergence, or leaves
   unresolved in-scope closure findings, do not bump the workflow version.

### Step 11: Write Repair Log, Closure Artifacts, and Summarize

1. Write the repair log using `references/repair-log-template.md`.
   - If continuation mode = `auto-follow-through`, set
     `Auto Follow-Through Outcome` to `pending` at this stage because Step 12
     has not finished yet.
   - Record `total-attempted` as every repair item that actually entered
     execution, regardless of whether it later succeeded, failed, or was
     reverted.
2. Save the repair log to the current repair task directory.
3. Ensure each closure round has a corresponding `closure-round-<N>.md`
   artifact in the current repair task directory.
4. Optionally write one `tmp/workflow-issues/{NNNN}.md` shadow file only as an
   auxiliary audit artifact; do not use it as the `v4` repair decision
   surface.
   If no shadow file is written, record `issue-history-file: none` in the
   repair log instead of implying that a file exists.
5. Echo the summary:
   - report path consumed
   - repair task path
   - base workflow version
   - bumped workflow version, when Step 10B ran
   - adopted / ignored / blocked / manual-decision / trellis-native counts
   - succeeded / failed / skipped counts
   - continuation mode
   - repair log path
   - closure-round artifact paths
   - optional issue-history shadow path, if written
6. Optional next steps:
   - later re-run `workflow-scan` on a fresh temp project to verify the broader
     workflow behavior
   - or run `workflow-audit` for comprehensive validation
7. Do not delete task files or closure-round artifacts.

### Step 12: Optional `--auto` Task Wrap-Up

Use this step only when continuation mode = `auto-follow-through`.

This step has two sub-phases:

- **Phase A — Evaluate And Decide**: determine whether close-out may continue,
  or whether the close-out flow must stop with a blocker reason.
- **Phase B — Record And Report**: always update the repair log with the final
  continuation outcome and echo that outcome, even when Phase A blocked the
  close-out flow.

1. **Phase A**: confirm that the repair run is actually ready to continue:
   - every attempted fix has a terminal recorded status:
     `verified`, `failed`, or `reverted`
   - no `blocked` or `manual-decision` item remains unresolved in a way that
     would make task close-out misleading or unsafe
   - treat a `blocked` or `manual-decision` item as sufficiently resolved for
     close-out only when its reason is recorded in the repair log/correction
     plan and it does not represent an incomplete repair that would make the
     commit misleading
   - when `total-blocked + total-manual-decision > 0` but
     `total-succeeded > 0`, auto follow-through may still continue only if the
     unresolved items are recorded clearly enough that the resulting commit will
     not misrepresent the repair as fully complete
   - the working tree is in the state required by the normal Trellis close-out
     flow for this task
2. If `total-succeeded = 0` and `total-attempted > 0`, stop the close-out flow
   and record/report that no effective repair was made. Do not continue to
   commit confirmation or finish-work.
3. If authorization mode = `analysis-only` and execution never actually ran,
   stop the close-out flow. `--auto` does not override the lack of repair
   execution.
   This rule applies only when the authorization state never transitioned past
   `analysis-only`.
4. If `total-attempted = 0`, or if no code changes were made during the repair
   run, stop the close-out flow and report that there is no repair-side work to
   commit or close out automatically.
5. Continue into the current task's remaining required close-out flow instead
   of stopping at the repair summary. Start that re-entry with the available
   Trellis `continue` surface for the current platform/session.
6. Resolve the `continue` surface in this priority order:
   - callable platform command surface for the current session
   - same-session `trellis-continue` skill surface available in the current
     project/runtime
   If neither exists, stop the close-out flow and report the blocker. Do not
   simulate or replace `continue`.
7. Each time `continue` is invoked, inspect the resulting state before
   deciding the next move:
   - if it surfaces what appears to be the current repair task's one-shot
     commit confirmation or explicit current-task commit-plan/scope
     confirmation, route that prompt through Step 12.8 instead of treating it
     as ordinary loop progress
   - if it recommends or routes to `finish-work`, transition to the
     `finish-work` surface-resolution step below
   - if it clearly indicates the current repair task is already closed,
     completed, archived, or otherwise no longer has remaining close-out work,
     stop the loop and treat auto follow-through as complete with outcome
     `reached-task-close` without another `continue`
   - if it keeps the task in a current-task close-out stage that still needs
     another normal Trellis re-entry, invoke `continue` again
   - if the same repair task reaches 5 consecutive `continue` re-entries in
     this auto-follow-through run without ending at `finish-work`,
     `reached-task-close`, or a clearly new close-out checkpoint, stop and
     report a blocker instead of risking an infinite loop. For this rule, a
     "clearly new close-out checkpoint" means a state transition that is
     explicit in the current task's close-out flow, such as:
     from "awaiting commit confirmation" to "commit completed", from
     "commit completed" to "finish-work recommended", or another clearly named
     close-out milestone that shows the task progressed rather than merely
     re-printing the same non-terminal state
   - if it cannot be determined whether the task advanced, closed, or changed
     stages safely, stop and report the blocker instead of looping blindly
8. If the prompt routed here from Step 12.7 asks for the current repair task's
   one-shot commit confirmation or commit-plan/scope confirmation, reply `ok`
   exactly once. Treat a prompt as that confirmation only when it is clearly
   about committing the current repair task and explicitly asks for a
   yes/confirm style response.
   A prompt still qualifies when it enumerates proposed commits, unrecognized
   working-tree files that the prompt explicitly frames as part of the current repair
   task's commit scope, or current repair-task artifacts as part of that
   current-task commit scope, as long as it keeps the decision scoped to the
   current repair task and asks for a one-shot approval such as `ok`.
   Evaluate the prompt in this order: explicit current-task scoping first, then
   file-scope proof, then repair-result honesty, then repeated-confirmation
   checks.
   Use the definitions and independently provable output-set rules from
   `Auto Follow-Through Mode` above when judging these paths.
   Current repair-task artifacts qualify by task-directory membership plus
   explicit current-task scoping alone.
   If the prompt includes any working-tree file outside the current repair task's
   commit scope, or cannot prove that every enumerated working-tree file belongs
   inside that scope through that independently provable output set, treat it
   as a case where commit-confirmation
   identification is unreliable.
   If the prompt's commit-scope description or repair-result wording would
   materially misstate what this run actually succeeded, reverted, left
   unresolved, or left outside `target_focus`, treat it as a case where
   commit-confirmation identification is unreliable.
   Wording such as `all fixes verified` or `commit these verified fixes`
   counts as materially misstating the result whenever any attempted fix was
   reverted, failed, unresolved, or left outside `target_focus`.
   If the same close-out run surfaces a second otherwise-qualifying commit
   confirmation after this step has already auto-replied once, treat that as a
   close-out flow change and stop instead of auto-confirming again.
   When stopping for any of the blocker cases above, the Phase B blocker reason
   must state explicitly whether the stop happened because of mixed scope,
   misleading repair-result wording, insufficient explicitness / independent
   proof, or repeated confirmation inside the same close-out run.
   If multiple blocker causes trigger at once, report all triggered causes in
   the blocker reason rather than collapsing them to a single label.
   Here `reply ok exactly once` means once for this qualifying one-shot prompt;
   it does not forbid replying `ok` to a later distinct qualifying prompt in a
   different close-out run.
   If the prompt does not make that current-task scope or one-shot approval
   request explicit enough, treat it as a case where commit-confirmation
   identification is unreliable.
   If the close-out flow changes in a way that makes that one-shot
   identification unreliable, stop the close-out flow instead of risking
   over-confirmation.
9. After a successful commit for the current repair task, return to the
   `continue` loop instead of jumping directly to `finish-work`. The loop ends
   only when `continue` recommends `finish-work`, or when `continue` itself
   makes it clear that the current repair task has already been closed.
10. If any other interactive prompt appears, stop the close-out flow and report
   the blocker. Do not guess, auto-answer, or reinterpret it as commit
   confirmation.
11. Do not auto-answer unrelated prompts or broaden the commit scope beyond the
   current task.
12. Resolve the `finish-work` surface in this priority order:
    - callable platform command surface for the current session
    - same-session `trellis-finish-work` skill surface available in the
      current project/runtime
    If neither exists, stop the close-out flow and report the blocker. Do not
    simulate or replace `finish-work`.
13. After the `continue` loop indicates that the current repair task's work is
    committed and the task is otherwise ready, invoke the available
    `finish-work` surface for the current platform/session.
14. If commit or finish-work cannot safely proceed, stop the close-out flow and
    report the blocker instead of forcing completion.
    If `git commit` itself fails mechanically (for example hook rejection,
    conflict, or another commit-time error), leave the repair changes in place,
    record/report the blocker, and do not pretend the task was closed out.
15. **Phase B**: update the repair log with the final
    `Auto Follow-Through Outcome` value:
    - `reached-finish-work`, or
    - `reached-task-close`, or
    - `stopped-with-blocker: <brief reason>`
    If the blocker happened after commit but before task wrap-up completed,
    record that fact in the blocker reason rather than introducing a separate
    outcome enum.
16. If this run resumed after an older repair log for the same task was left at
    `pending`, update that older continuation result to
    `interrupted: session-did-not-complete` before recording the new final
    outcome.
    Treat a resumed run as detected when the current repair task's latest
    repair log still shows `Auto Follow-Through Outcome: pending`.
    Determine that latest repair log from the greatest `repair-timestamp`
    value, not from filename ordering alone.
    If the current process itself is interrupted before Phase B runs, the log
    may remain at `pending` until a later run performs this recovery step.
17. Echo whether auto follow-through reached finish-work, reached normal task
    closure, or stopped with a blocker.

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
| Repair task setup failure | Stop as **Blocked / Repair Task Setup Failed**. Do not continue without a dedicated repair task. |
| Protocol version mismatch | Stop as **Blocked / Protocol Version Mismatch**. The report was produced by a different protocol version. |
| Temp project mismatch | Stop as **Blocked / Temp Project Mismatch**. The report and the live temp project do not line up. |
| Repeated finding with no broader safe fix | Stop as **Blocked / Repeated Finding Needs Broader Closure**. Do not repeat a previously narrow patch without a stronger closure plan. |
| Stale scan report | Stop as **Blocked / Stale Scan Report**. Tell the user to re-embed and re-run `workflow-scan`. |
| Invalid embedded state | Stop as **Blocked / Invalid Embedded State**. The version/schema evidence does not represent a valid same-version embedded target. |
| Closure does not converge within bounded rounds | Stop as broader non-convergence and require audit or a new explicit decision. |
| Issue-history shadow write failure | Record that the optional audit shadow could not be written, but do not let that override the primary task-local repair/closure artifacts. |
| No findings in report | Write the repair log with `total-attempted: 0` and all counts at 0. |
| Fix scope violation | Skip the fix, record the violation in the repair log. Do not modify files outside the allowed three locations. |
| Post-repair verification failure | Revert the change, record the failure and revert in the repair log. |
| `--auto` requested but commit-confirmation identification is unreliable | Stop the close-out flow, report the blocker, and do not risk over-confirmation. This row covers residual insufficient explicitness or failed independent proof, including reverted-file exclusion cases, that do not already fall into the more specific mixed-scope, misleading-result, or repeated-confirmation rows below. The blocker reason must still state the underlying cause explicitly. |
| `--auto` requested but the commit-scope prompt includes non-task working-tree files or otherwise mixes scopes | Stop the close-out flow, report the blocker, and do not auto-confirm a mixed-scope commit range. |
| `--auto` requested but the commit-scope or repair-result wording would misstate the actual repair outcome | Stop the close-out flow, report the blocker, and do not auto-confirm a misleading commit description. |
| `--auto` requested but the same close-out run surfaces a second qualifying commit confirmation | Stop the close-out flow, report the blocker, and do not auto-confirm again inside the same close-out run. |
| `--auto` requested and a non-commit interactive prompt appears | Stop after the repair summary or current close-out point, report the blocker, and do not guess a reply. |
| `--auto` requested but no continue surface is available | Stop after the repair summary or current close-out point, report the blocker, and do not simulate continue. |
| `--auto` requested but no finish-work surface is available | Stop after the repair summary or current close-out point, report the blocker, and do not simulate finish-work. |
| `--auto` requested but no effective repair succeeded | Stop after the repair summary, record that no effective repair was made, and do not continue to commit confirmation or finish-work. |
| `--auto` requested but findings exist and all of them resolve to `ignored` | Stop after the repair summary, record that no repair-side work was produced, and do not continue to commit confirmation or finish-work. |
| `--auto` requested but no repair-side code changes exist | Stop after the repair summary, record that no repair-side work exists to close out automatically, and do not continue to commit confirmation or finish-work. |
| `--auto` requested but close-out is not ready or not safe | Stop after the repair summary, explain the blocker, and do not auto-confirm commits or invoke finish-work. |
| `--auto` requested but continue cannot prove whether the task advanced or closed | Stop after the current close-out point, report the blocker, and do not keep looping blindly. |
| User rejects all | Write the repair log with all findings as `skipped`. No workflow source files modified. |

## Related Skills

- `workflow-scan`: analyzer/producer pair — produces the
  `WORKFLOW_QUESTIONS.md` this skill consumes
- `workflow-audit`: comprehensive audit with version gates, evidence mainline,
  and runtime validation (complementary, not replacement)
- `workflow-capability-audit`: version-drift audit

## Tests

Required persisted scenario files:

- `tests/08-auto-follow-through-success.md`
- `tests/09-auto-stops-on-zero-success.md`
- `tests/10-auto-no-effect-under-analysis-only.md`
- `tests/11-auto-stops-on-unexpected-prompt.md`
- `tests/12-auto-blocked-without-finish-work-surface.md`
- `tests/13-post-plan-confirmation-mode.md`
- `tests/14-post-plan-confirmation-with-auto.md`
- `tests/15-partial-accept-with-documented-blockers.md`
- `tests/16-interrupted-pending-recovery.md`
- `tests/17-commit-succeeds-but-finish-work-fails.md`
- `tests/18-auto-zero-findings.md`
- `tests/19-git-commit-fails-during-auto.md`
- `tests/20-auto-with-preexisting-active-task.md`
- `tests/21-auto-all-findings-ignored.md`
- `tests/22-authorized-to-repair-partial-accept-with-auto.md`
- `tests/23-target-focus-with-out-of-focus-high-severity.md`
- `tests/24-auto-mixed-success-and-reverted.md`
- `tests/25-auto-falls-back-to-skill-surfaces.md`
- `tests/26-auto-stops-when-continue-surface-missing.md`
- `tests/27-auto-continue-closes-task.md`
- `tests/28-auto-stops-on-continue-loop-limit.md`
- `tests/29-auto-mixed-surface-availability.md`
- `tests/30-auto-stops-on-unreliable-commit-confirmation.md`
- `tests/31-auto-continue-closes-task-before-commit.md`
- `tests/32-auto-mixed-surface-availability-reversed.md`
- `tests/33-auto-close-out-not-ready-or-safe.md`
- `tests/34-auto-handles-current-task-commit-scope-confirmation.md`
- `tests/35-auto-stops-when-commit-scope-includes-non-task-files.md`
- `tests/36-auto-stops-on-misleading-commit-scope-result-claim.md`
- `tests/37-auto-stops-when-framed-working-tree-file-is-outside-task-dir.md`
- `tests/38-auto-allows-provable-write-scope-files-outside-task-dir.md`
- `tests/39-auto-stops-on-target-focus-misleading-all-fixes-verified.md`
- `tests/40-auto-continues-when-commit-scope-wording-is-honest-despite-partial-results.md`
- `tests/41-auto-allows-task-dir-files-without-current-run-proof.md`
- `tests/42-auto-stops-on-previous-run-out-of-directory-file.md`
- `tests/43-auto-stops-on-second-qualifying-confirmation-in-same-run.md`
- `tests/44-auto-stops-when-task-dir-files-lack-explicit-task-scoping.md`
- `tests/45-auto-stops-when-reverted-file-is-still-claimed-in-commit-scope.md`
- `tests/46-auto-continues-on-target-focus-honest-focused-repairs-wording.md`
- `tests/47-auto-continues-on-pure-working-tree-files-when-all-provable.md`
- `tests/48-auto-stops-on-pure-working-tree-files-when-one-is-unprovable.md`
- `tests/49-auto-reports-all-triggered-blocker-causes.md`
- `tests/50-auto-stops-on-target-focus-scope-proof-failure.md`
- `tests/51-auto-reports-misleading-plus-insufficient-explicitness.md`
- `tests/52-auto-stops-on-honest-wording-without-explicit-task-scope.md`
- `tests/53-design-debt-defaults-to-manual-decision.md`
- `tests/54-evidence-gap-defaults-to-blocked.md`
- `tests/55-stale-scan-report-blocked.md`
- `tests/56-invalid-embedded-state-schema-mismatch.md`
- `tests/57-closure-unresolved-in-scope-blocks-closeout.md`
- `tests/58-closure-new-family-stops-auto-progression.md`
- `tests/59-backup-original-restore-surface-defaults-to-ignored.md`

## Examples

### Example 1: Standard Repair Cycle

```text
User: /workflow-repair

AI:
1. Auto-detect report from the current `trellis -v` result: `/tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md`
2. Read the report header and derive short topic `session-start-gate`
3. Create and start a dedicated task `workflow-repair-<date>-session-start-gate`
4. Validate frontmatter: protocol=workflow-scan-repair-v4
5. Resolve temp project root from the report
6. Confirm report version, temp-project version, and source `WORKFLOW_VERSION`
   are all the same
7. Parse 5 findings: P0×1, P1×2, P2×2
8. Verify each against the temp project and source workflow:
   - WS-001 (P0): confirmed → adopted
   - WS-002 (P1): source already fixed → ignored
   - WS-003 (P1): confirmed, but fix risky → manual-decision
   - WS-004 (P2): trellis-native → trellis-native
   - WS-005 (P2): false alarm → ignored
9. Run the same-pattern sweep inside `docs/workflows/新项目开发工作流/`
10. Build the contract-surface coverage map
11. Build correction plan for WS-001, WS-003, WS-004
12. The user already asked to fix real confirmed issues, so the echoed plan counts as authorization
13. Apply WS-001 and WS-004 fixes
14. Post-repair strict review passes without requiring a same-run re-embed
15. Write repair log to the repair task directory
16. Write `closure-round-1.md` after bounded same-version closure verification
17. Echo:
    ✅ Workflow repair complete
    📄 Report consumed: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
    📁 Repair task: .trellis/tasks/{task-id}/
    🔖 Base workflow version: 0.1.2800
    📊 Findings: 5 total (adopted: 1, ignored: 2, blocked: 0, manual: 1, trellis-native: 1)
    🔧 Applied: 2 succeeded, 0 failed, 1 skipped
    📝 Repair log: .trellis/tasks/{task-id}/workflow-repair-log.md
    🔁 Closure: .trellis/tasks/{task-id}/closure-round-1.md
```

### Example 2: No Active Task Yet

```text
User: /workflow-repair

AI:
1. Resolve report from `/tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md`
2. No active task exists
3. Create and start `workflow-repair-<date>-workflow-issues`
4. Continue the repair flow inside that task
```

### Example 3: Report Produced By `workflow-scan --agent`

```text
User: /workflow-repair

AI:
1. Resolve `/tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md`
2. Validate the shared report contract exactly as usual
3. Note that the report may have been produced by `workflow-scan --agent`, but repair-side intake stays execution-mode agnostic
4. Continue verifying findings from the validated report and the temp project
```

### Example 4: Analysis Only, No Auto-Repair

```text
User: /workflow-repair

AI:
1. Create and switch into a dedicated repair task
2. Verify 3 findings against the temp project and source workflow
3. Confirm the report is not stale before any repair planning
4. Build correction plan (2 adopted, 1 ignored)
5. Current user request asks only for judgment, so mode = analysis-only
6. Present plan and stop for confirmation
7. No workflow source files modified yet

   ⏸ Workflow repair paused for confirmation
   📊 Findings: 3 total (adopted: 2, ignored: 1)
   🔧 Applied: 0 so far
   📝 Repair log: not written yet
   🔁 Closure: not written yet
```

If the user had written `/workflow-repair --auto` with the same analysis-only
intent and still declined execution, the result would be the same: `--auto`
would have no effect because no repair run completed.

If the user instead accepted a partial repair run under `analysis-only` and all
confirmed repairs later failed or were reverted, `--auto` would no longer be a
no-op. Step 12.2 would stop follow-through as a blocker because execution did
run, but no effective repair succeeded.

### Example 5: Repair With `--auto` Follow-Through

```text
User: /workflow-repair --auto

AI:
1. Resolve `/tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md`
2. Create and start a dedicated repair task
3. Detect continuation mode = auto-follow-through
4. Authorization Mode: authorized-to-repair
5. Validate the shared report contract and verify findings exactly as usual
6. Present the correction plan, explicitly noting that a successful run will
   continue into the current task's close-out flow
7. Apply the confirmed repairs
8. Complete post-repair strict review
9. Write the repair log and `closure-round-1.md`
10. Re-enter the current repair task through the available `continue` surface
11. The current task reaches its normal commit-plan confirmation prompt
12. Reply `ok`
13. The current task's work commits land
14. Re-enter the current repair task through `continue` again
15. `continue` now recommends `finish-work`
16. Invoke the available `finish-work` surface for this session
    (for example `trellis-finish-work`; some platforms may expose
    `/trellis:finish-work` instead, or expose the same behavior as a
    `trellis-finish-work` skill surface)
17. Echo that the repair task finished end to end
```

### Example 6: `--auto` Stops On Blocker

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Verify the findings and execute the confirmed repairs
3. Post-repair review completes, but `total-succeeded = 0` and
   `total-attempted > 0`
4. Write the repair log and record that no closure round was needed
5. Stop after the repair summary

   ⏸ Auto follow-through stopped
   Reason: no effective repair was made, so commit confirmation and
   finish-work would be misleading
```

### Example 7: `post-plan-confirmation` With `--auto`

```text
User: /workflow-repair --auto

AI:
1. Initial Authorization Mode: analysis-only
2. Present correction plan with continuation mode = auto-follow-through
3. User replies: Accept all
4. Authorization Mode transitions to post-plan-confirmation
5. Execute the confirmed repairs
6. Post-repair checks pass
7. Re-enter the dedicated repair task through the available `continue`
   surface
8. Handle the current task's one-shot commit confirmation or eligible explicit
   current-task commit-plan/scope confirmation only if it appears
9. Continue re-entering through `continue` until the task reaches
   `finish-work` or `reached-task-close`
```

### Example 8: `target_focus` With `--auto`

```text
User: /workflow-repair --auto --target_focus WS-002

AI:
1. Resolve and validate the report as usual
2. Limit execution focus to WS-002
3. Note in the correction plan that out-of-focus findings remain outside the
   auto close-out safety decision
4. If an out-of-focus finding is higher severity, surface that clearly so the
   user sees the repair scope is narrowed rather than fully clean
5. Execute the focused repair work only
6. If auto follow-through proceeds, re-enter the current task through
   `continue` and apply the same focused-scope safety rules before any later
   `finish-work` step
7. Continue or stop auto follow-through based on the focused scope rules
```

### Example 9: Command Surface Missing, Skill Surface Available

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Current platform/session does not expose callable `/trellis:continue` or
   `/trellis:finish-work` command surfaces
4. Detect same-session skill surfaces `trellis-continue` and
   `trellis-finish-work` in the current project/runtime
5. Re-enter close-out through `trellis-continue`
6. Reply `ok` to the repair task's one-shot commit confirmation or eligible
   explicit current-task commit-plan/scope confirmation
7. Re-enter `trellis-continue` after commit until it recommends finish-work
8. Invoke `trellis-finish-work`
9. Report successful end-to-end follow-through instead of stopping on a false
   "missing command surface" blocker
```

### Example 10: `continue` Closes The Task Before `finish-work`

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Re-enter the repair task through the available `continue` surface
4. Reply `ok` to the current repair task's eligible commit confirmation or
   explicit current-task commit-plan/scope confirmation
5. Re-enter the repair task through `continue` again
6. `continue` now reports that the current repair task has already completed /
   closed and there is no further close-out work for this task
7. Stop the loop without another `continue`
8. Report successful auto follow-through with final outcome
   `reached-task-close`
```

### Example 11: Current-Task Commit-Scope Confirmation With Task Artifacts

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Re-enter the repair task through the available `continue` surface
4. The close-out prompt lists proposed commits plus current repair task
   artifacts such as `check.jsonl`, `implement.jsonl`, or `task.json`
5. The same prompt explicitly says those artifacts are being treated as part of
   the current repair task's commit scope, and any listed unrecognized working-tree
   files are framed as belonging to that same current-task scope, and every
   listed path can also be independently proved as part of this run's allowed
   write-scope outputs, and asks for a one-shot `ok`
6. Because the prompt is still clearly about committing the current repair
   task, reply `ok`
7. Continue the normal close-out loop after commit instead of stopping on a
   false ambiguity blocker
```

### Example 12: Mixed-Scope Commit Prompt Stops Auto Follow-Through

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Re-enter the repair task through the available `continue` surface
4. The close-out prompt lists current repair-task artifacts together with dirty
   working-tree files that are not framed as belonging to the current repair task's commit
   scope
5. Because the commit range is now mixed-scope, treat the prompt as unreliable
   and stop with a blocker instead of replying `ok`
```

### Example 13: Misleading Result Claim Stops Auto Follow-Through

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Some attempted fixes succeed, but another attempted fix is reverted
4. A later close-out prompt says "reply ok to commit these verified fixes" in a
   way that would imply every attempted repair passed
5. Because the prompt would materially misstate the actual repair outcome,
   treat commit-confirmation identification as unreliable and stop with a
   blocker instead of replying `ok`
```

### Example 14: Provable Workflow File Outside Task Directory Still Qualifies

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. The current run records a repaired workflow source file under
   `docs/workflows/新项目开发工作流/` plus the current task log outputs
4. A later close-out prompt enumerates that workflow source file together with
   current task artifacts and asks for `ok`
5. Because every listed path is independently provable as part of this run's
   allowed write-scope outputs, reply `ok` and continue instead of stopping on
   a false blocker
```

### Example 15: Older Task-Directory Files Still Qualify

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. The current repair task directory already contains an older repair log from
   a previous run, and the current close-out prompt enumerates it together with
   this run's task artifacts as part of the current task commit scope
4. Because those paths are still current repair-task artifacts inside the task
   directory, treat them as eligible without requiring separate current-run
   output proof
5. Continue evaluating any out-of-directory files under the stricter
   independently provable output-set rule
```

### Example 16: Honest Partial-Result Wording Still Allows Close-Out

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Some attempted fixes succeed, while another attempted fix is reverted
4. A later close-out prompt asks for `ok` while describing the scope honestly
   as the current repair changes, without claiming that all attempted fixes
   were verified
5. Because the wording stays truthful and every enumerated path is otherwise
   eligible, reply `ok` and continue instead of stopping on a false
   misleading-result blocker
```

### Example 17: Same-Run Repeated Confirmation Stops Auto Follow-Through

```text
User: /workflow-repair --auto

AI:
1. Resolve and validate the report as usual
2. Execute the confirmed repairs
3. Re-enter the repair task through the available `continue` surface
4. Reply `ok` to one qualifying current-task commit confirmation
5. Before the close-out run ends, the flow unexpectedly surfaces another
   otherwise-qualifying commit confirmation for the same run
6. Treat that second confirmation as a close-out flow change and stop with a
   blocker instead of auto-confirming again
```

### Example 18: Honest Focused-Repairs Wording Still Allows Continue

```text
User: /workflow-repair --auto --target_focus WS-002

AI:
1. Resolve and validate the report as usual
2. Execute only the focused repair work
3. A later close-out prompt asks for `ok` to commit `the focused repairs`
   without implying that out-of-focus findings were also fixed
4. Because the wording stays explicitly scoped and honest, continue instead of
   treating it as a misleading-result blocker
```

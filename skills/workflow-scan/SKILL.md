---
name: workflow-scan
description: Generate a `WORKFLOW_QUESTIONS.md` report for an embedded Trellis temp project. Use when scanning the full workflow currently in use inside the temp project for problems, gaps, residual issues, or new issues before source-side repair.
compatibility: Requires `trellis` on PATH, access to the temp project fixture, local filesystem access, and either inline CLI execution or an agent-capable session when `--agent` is explicitly requested.
---

# workflow-scan

## Version History

- **v3.4**: Clarified that the complete-catalog rule excludes contradiction-
  free intentionally disabled retained carriers per rule 17, and restored
  design-debt / evidence-gap coverage in the shared output example
- **v3.3**: Clarified that a retained carrier explicitly documented as
  temporarily unavailable or intentionally disabled is omitted from
  `WORKFLOW_QUESTIONS.md` unless another installed surface contradicts that
  disabled contract
- **v3.1**: Clarified that actionable defect judgment in this skill version is
  limited to Claude Code / OpenCode / Codex workflow surfaces; issues seen
  only in other CLI usage stay out of scope unless the managed surface later
  expands
- **v3.2**: Clarified that valid `.backup-original/` carrier trees paired with
  active patched/overlay assets are intentional restore surfaces, not residual
  workflow defects
- **v3.0**: Upgraded the shared contract to `workflow-scan-repair-v4`,
  requires concrete workflow version/schema fields, and aligns scan output with
  same-version stale-report blocking on the repair side

- **v2.8**: Added mandatory repair-classification guardrails so scan findings
  must distinguish `confirmed-defect`, `design-debt`, and `evidence-gap`, and
  upgraded the shared report contract to `workflow-scan-repair-v3`
- **v2.7**: Refined the paired repair-side compatibility note to clarify that
  `workflow-repair --auto` still stays outside the shared scan schema while now
  rejecting mixed-scope or misleading current-task commit confirmations
- **v2.6**: Updated the paired repair-side compatibility note to clarify that
  `workflow-repair --auto` may now accept explicit current-task
  commit-plan/scope confirmations that enumerate proposed commits or task
  artifacts, while scan output and the shared report schema remain unchanged
- **v2.5**: Refined the paired repair-side compatibility note for
  `workflow-repair --auto`, clarifying that scan output remains schema-stable
  while repair-side close-out may now loop through current-task `continue`,
  fall back from command surfaces to same-session skill surfaces, and still
  stay outside the shared scan/report schema
- **v2.4**: Added paired repair-side compatibility note for
  `workflow-repair --auto`, clarifying that scan output stays schema-stable
  while repair-side close-out behavior may optionally continue automatically in
  the source project
- **v2.3**: Added explicit `--agent` opt-in and capability criteria, kept
  inline scan as the default, clarified coordinator-owned report writing plus
  hard-block behavior when agent mode is unsupported, and added helper-failure
  / conflict-compensation rules, a reusable handoff template, and scenario
  tests for agent-assisted success/failure paths
- **v2.1**: Added mandatory read-back validation for generated reports, count
  consistency checks, and explicit contract-drift guards before scan success
- **v2.0**: Re-scoped the skill to analyze only the full workflow content currently present in the temp project; removed source-repo inputs, source-repo evidence layers, and source-location requirements from the scan contract
- **v1.3**: Aligned frontmatter with the latest public skill spec by making the description explicitly cover both purpose and trigger, and by adding compatibility requirements
- **v1.2**: Replaced misleading fixed example paths and version literals with runtime-sensitive placeholders
- **v1.1**: Clarified temp-project provenance, no-agent execution, analysis-summary output, and evidence classification rules
- **v1.0**: Initial release

## Purpose

Scan the embedded workflow currently in use inside a Trellis temp project and
produce a structured `WORKFLOW_QUESTIONS.md` report.

This skill is the **analyzer/producer** half of the `workflow-scan` /
`workflow-repair` coupled pair.

Its target of judgment is the full workflow surface currently present inside the
temp project. It does not compare against the current source repository. It
does not edit workflow source files, installed artifacts, or task state.

## When to Use

Use this skill when any of the following is true:

- you are working in a trellis temp project and need to analyze the workflow
  currently installed there
- you need to inspect the temp project's active workflow surfaces for problems,
  gaps, residual issues, or new issues
- the user asks to "scan the temp project workflow" or "check the embedded
  workflow for issues"
- the user asks to "produce workflow questions" or "generate a workflow scan
  report"
- the user asks to "run workflow-scan"
- a workflow analysis cycle starts and a structured report is needed before
  repair

## When Not to Use

- you need to fix issues: use `workflow-repair` in the source project
- you need a comprehensive audit with version gates and runtime validation: use
  `workflow-audit`
- you need version-drift analysis: use `workflow-capability-audit`
- you are doing a normal implementation task without workflow analysis

## Core Rules

1. **Scan only**: this skill produces a question/evidence document; it never
   edits workflow source files or any code.
2. **Inline default**: without `--agent`, do not use agents, sub-agents, or
   task orchestration. Run the scan directly in the current CLI session.
3. **Explicit agent opt-in only**: use helper agents only when the input
   explicitly includes `--agent`. Do not switch to agent-assisted mode on your
   own.
4. **Coordinator ownership is mandatory**: when `--agent` is present, the
   current CLI session remains the scan coordinator. Multiple helper agents may
   inspect bounded temp-project surfaces and return evidence, but only the
   coordinator may decide final findings, write `WORKFLOW_QUESTIONS.md`, or
   report success.
5. **No silent fallback for `--agent`**: if `--agent` is requested but the
   current platform/session cannot safely run helper agents, stop as
   **Blocked / Agent Mode Unsupported** instead of quietly reverting to inline
   mode.
   This rule applies to mode selection only. Once helper dispatch has already
   started, coordinator-side local compensation for helper failure is still
   allowed and is not considered a forbidden silent fallback.
6. **Bounded agent mode only**: `--agent` is an evidence-gathering aid, not a
   general orchestration mode. Use only a small number of helper agents with
   non-overlapping scopes sized to reduce context pressure rather than maximize
   parallelism.
7. **No task-state side effects**: `--agent` does not authorize task creation,
   task switching, or any file edits by helper agents. Their scope is read-only
   evidence gathering. Execution-mode changes also do not alter repair-side
   intake assumptions; the validated report contract remains the sole basis for
   repair-side processing.
8. **Temp project only**: this skill runs in or targets a Trellis temp project.
   The analysis target is the temp project's currently installed workflow, not
   the current source repository.
9. **Embedded-workflow truth target**: judge whether issues exist from the full
   workflow result under `/tmp/trellis-{VERSION}-2`, not from any external
   source tree.
10. **All active workflow surfaces count**: scan the full workflow content that
   the temp project is currently using, not only
   `.trellis/workflow-installed.json`.
11. **Evidence comes from the temp project only**: every finding must use an
   `Evidence Layer` value grounded in the temp project's actual state.
12. **Conservative severity**: severity estimates are preliminary, set by the
   scan running in isolation before repair. Mark explicitly as estimates.
13. **Complete final finding set**: every anomaly that belongs in the final
   finding set must be recorded. Do not filter that finding set by severity
   during the scan phase. Intentionally disabled retained carriers without
   contradictions may still be inspected during analysis, but rule 17 keeps
   them out of the final finding set.
14. **Origin classification is mandatory**: every finding must classify as
   either `trellis-native` (produced by `trellis init`) or `workflow-source`
   (introduced by the embedded workflow's install/patch layer).
15. **Repair classification is mandatory**: every finding must additionally
    classify as `confirmed-defect`, `design-debt`, or `evidence-gap`.
16. **No complexity-only inflation**: if an observation is only about
    complexity, maintainability, ergonomics, or possible over-design without a
    concrete temp-project contradiction, it must be classified as
    `design-debt`, not `confirmed-defect`.
17. **Intentional gated-carrier observations stay conservative**: if a
    carrier is present on disk but the temp project's installed workflow docs
    or runtime rules explicitly say that the path is intentionally gated off
    for now, kept only as a compatibility carrier, or reserved for possible
    future re-enable after maturity improves, the scan must not emit that
    situation as a finding unless another installed surface contradicts that
    disabled contract.
    This includes retained subagent/helper carriers that the temp project
    explicitly marks as currently unavailable or temporarily disabled.
    - If the installed workflow still behaves consistently with that stated
      contract, omit the item from the final `WORKFLOW_QUESTIONS.md` findings.
      At most, mention it as non-finding context while explaining why it was
      intentionally excluded.
    - Only emit a finding when the temp project shows a real contradiction,
      such as the docs claiming the path is disabled while some installed
      runtime surface still actively routes users into it.
    - Other contradiction examples include installed workflow docs still
      teaching that carrier's usage, hook/config/runtime-control surfaces still
      invoking it, or another installed command/skill/agent surface still
      routing through it as an active entry path.
18. **No evidence-gap inflation**: if the temp-project evidence is still
    insufficient to confirm a real defect or source-owned root cause, the item
    must be classified as `evidence-gap`, not `confirmed-defect`.
19. **Contract format**: the output must use the `WORKFLOW_QUESTIONS.md` format
    exactly as defined in `references/scan-output-template.md`.
20. **Read-back validation is mandatory**: after writing
    `WORKFLOW_QUESTIONS.md`, the skill must read the file back and verify the
    required frontmatter keys, summary sections, and finding schema before it
    may report success. This validation also serves as the shared contract gate
    ensuring the emitted report satisfies `workflow-repair` intake
    assumptions.
21. **Concrete workflow version fields are mandatory**: successful scan output
    must include real `workflow-version` and `workflow-schema-version` values
    from the embedded target. If either field is missing or unresolved, stop as
    **Blocked / Invalid Embedded State** instead of emitting a repair-usable
    report.
22. **Supported CLI defect scope is fixed for this skill version**: actionable
    findings may concern only the current workflow's Claude Code / OpenCode /
    Codex managed surfaces. If a symptom appears only when using some other CLI
    and does not break these three supported surfaces, record it at most as
    out-of-scope context and do not emit it as a workflow defect.
23. **Preserved restore surfaces are not residual defects by default**:
    `.backup-original/` trees under managed command/skill carriers must not be
    reported as workflow defects when temp-project evidence shows they are
    backup copies paired with active patched/overlay assets recorded in
    `.trellis/workflow-installed.json` (for example `patched_baseline_commands`
    or `patched_codex_skills`).

## Inputs

| Input | Required | Default | Meaning |
|-------|----------|---------|---------|
| `temp_project_path` | No | auto-detect | Absolute path to temp project root |
| `candidate_focus` | No | empty | Supplementary focus areas to prioritize |
| `--agent` | No | off | Mode-switch flag. When present, the coordinator may use multiple helper agents for bounded read-only evidence gathering. Without it, the scan must stay inline in the current CLI session. |

### Execution Mode Resolution

1. Treat execution mode as `agent-assisted` only when the user explicitly asks
   for helper-agent use, either by:
   - including the literal `--agent` token in the request, or
   - using equivalent natural language such as "use multiple agents",
     "scan this with helper agents", or "do the scan with multi-agent help"
2. If the user does not explicitly request helper-agent use, execution mode is
   `inline`.
   Requests such as "scan deeper", "scan faster", or "do a more thorough scan"
   do not by themselves enable helper-agent mode.
3. In `agent-assisted` mode, the current CLI session remains the coordinator:
   - helper agents may take only concrete, non-overlapping evidence-gathering
     slices
   - helper agents must not write files, answer overwrite prompts, or finalize
     findings/severity
4. If `--agent` is present but the current platform/session cannot safely run
   multiple helper agents with explicit ownership boundaries, stop as
   **Blocked / Agent Mode Unsupported**.
5. Treat the current platform/session as agent-capable only when all of the
   following are true:
   - helper agents can actually be invoked in this environment rather than only
     being theoretically supported by the product family
   - the coordinator can pass explicit scope boundaries and receive a distinct
     handoff back from each helper
   - helper execution does not violate a stronger repo-local or session-local
     rule such as Codex inline main-session constraints
6. If any capability criterion above is uncertain, prefer the conservative
   result: stop as **Blocked / Agent Mode Unsupported** instead of guessing.
7. Execution mode must not change the output file location, frontmatter, or
   finding schema. Inline and `--agent` runs emit the same
   `WORKFLOW_QUESTIONS.md` contract.
8. This skill defines behavior only. The concrete helper-dispatch mechanism is
   platform-specific and may differ across executors; do not assume a single
   universal Agent tool or API binding from this contract alone.
9. Repair-side `--auto` follow-through is outside scan execution mode. If the
   user later runs `workflow-repair --auto` in the source project, that changes
   only post-repair close-out behavior, including repair-side handling of
   explicit current-task commit-plan/scope confirmations. Those repair-side
   prompts may still be rejected when they mix non-task files into the commit
   scope or would misstate the actual repair result, and none of that may
   change scan output, overwrite handling, or the shared report schema.

### Temp Project Path Resolution

1. If `temp_project_path` is explicitly provided, use it.
2. Otherwise: run `trellis -v` to get VERSION, construct path
   `/tmp/trellis-{VERSION}-2/`.
3. Validate: the directory must exist and contain `.trellis/`.
4. If not found: stop as **Blocked / Temp Project Not Found**.

## Output

Single file: `WORKFLOW_QUESTIONS.md` at the temp project root.

Format specification: see `references/scan-output-template.md`.

## Workflow

### Step 0: Environment and Mode Preflight

1. Resolve the temp project path and execution mode (see the Inputs and
   Resolution sections above).
2. Verify the temp project is a valid Trellis-initialized project:
   - `.trellis/` directory exists
   - `.trellis/.version` exists and is readable
3. Verify the temp project also looks workflow-embedded:
   - `.trellis/workflow-installed.json` exists, or
   - `.trellis/scripts/workflow/` exists, or
   - `.trellis/workflow.md` exists and clearly represents an embedded workflow,
     not only a baseline Trellis workflow
4. Read runtime version/context fields from the temp project where available:
   - `trellis -v` → live trellis version
   - `.trellis/.version` → temp project's trellis version
   - `.trellis/workflow-installed.json` → `workflow_version`,
     `workflow_schema_version`, `critical_runtime_patches`, `commands`,
     `scripts`, `cli_types`, and other install-record fields if present
5. Require both `workflow_version` and `workflow_schema_version` to be present
   in successful scan output:
   - if either field is absent, empty, or effectively `unknown`, stop as
     **Blocked / Invalid Embedded State**
6. If the temp project is not fully initialized (no `.trellis/` or no
   `.version`): stop as **Blocked / Invalid Temp Project**.
7. If the temp project is not workflow-embedded: stop as
   **Blocked / Workflow Not Embedded**.
8. If `WORKFLOW_QUESTIONS.md` already exists at the temp project root: stop and
   ask whether to overwrite or append.
9. If execution mode is `agent-assisted`, do not dispatch helper agents until
   Steps 0.1-0.7 have passed and any overwrite decision has been resolved.

### Step 1: Workflow Surface Inventory

1. Catalog the workflow surfaces currently present in the temp project.
2. At minimum inspect these paths when they exist:
   - `.trellis/workflow.md`
   - `.trellis/workflow-installed.json`
   - `.trellis/scripts/workflow/`
   - `.trellis/workflow-docs/`
   - `.agents/skills/`
   - `.codex/`
   - `.claude/commands/trellis/`
   - `.opencode/commands/trellis/`
   - `AGENTS.md` and other installed runtime control files whose current
     content affects workflow behavior
3. For each observed artifact, classify the strongest supported evidence layer:
   - `generated-target-baseline` — observed in a Trellis baseline surface that
     exists in the temp project
   - `generated-target-installed` — observed in a workflow-installed or
     workflow-patched surface in the temp project
   - `generated-target-runtime` — observed in a temp-project runtime/control
     surface whose current behavior matters but is not well-explained by the
     install record alone
4. If an origin or evidence-layer classification is inferred rather than
   directly obvious, state that inference explicitly inside the finding
   evidence.
5. Build an artifact inventory that later steps reference.

### Step 1A: Optional `--agent` Work Split

Use this step only when execution mode is `agent-assisted`.

1. The coordinator defines concrete, non-overlapping helper scopes before any
   delegation. Good examples:
   - scripts and commands
   - CLI adaptation carriers
   - workflow documents and cross-references
   - runtime-control surfaces
   - recommended helper-count ceiling: 3 by default, 4 only when the workflow
     surface split is still clearly non-overlapping and the coordinator can
     justify the extra handoff cost
2. Each helper agent must receive:
   - explicit read-only scope boundaries
   - the exact temp-project paths or artifact class it owns
   - a required handoff format from
     `references/helper-handoff-template.md`, containing confirmed facts,
     candidate issues, open questions, and relative paths
3. Helper agents must not:
   - write `WORKFLOW_QUESTIONS.md`
   - edit any file
   - invent evidence outside the temp project
   - decide final severity or deduplicate findings across helpers
4. The coordinator must review every helper handoff. If a helper result is
   incomplete, ambiguous, malformed, timed out, or fails outright, the
   coordinator treats that helper as non-authoritative, fills the evidence gap
   locally, and may skip the slice rather than failing the whole scan.
   Partial helper output may still be used as a lead for local re-check, but it
   must not be promoted directly into final findings without coordinator
   confirmation from temp-project evidence.
5. If two helper handoffs conflict, the coordinator must resolve the conflict
   in the main session using temp-project evidence before carrying either claim
   into final findings. Do not average, merge, or silently pick one helper's
   claim without local verification. If the conflict remains unresolved after
   local re-check, drop the disputed claim from final findings rather than
   guessing. The unresolved conflict itself is not a workflow finding unless
   separate temp-project evidence independently supports one.
6. Keep helper-agent resource usage intentionally small:
   - use only the minimum number of helper agents needed for concrete
     non-overlapping slices
   - avoid delegating tiny or tightly coupled checks whose coordination cost
     exceeds their context-saving benefit
   - if agent coordination stops being net-beneficial, continue inline instead
     of widening the agent fan-out
7. Delegation is optional per step. Keep tightly coupled blocking decisions in
   the coordinator session instead of forcing them through helper agents.

### Step 2: Script, Command, Skill, Hook, and Agent Verification

For every workflow-related executable or control surface found in the temp
project:

1. **Existence**: verify the file exists at the expected path implied by the
   temp project's own workflow surfaces.
2. **Executability / syntax shape**: for shell/Python scripts, verify the file
   is executable or has a valid shebang; for config/markdown carriers, verify
   the file is structurally readable.
3. **Cross-surface consistency**: compare what the file claims against the temp
   project's own other workflow surfaces:
   - install record vs actual scripts/commands/skills/hooks
   - workflow docs vs actual installed helper paths
   - AGENTS/hook/config guidance vs actual installed runtime surfaces
4. **Exit-code or gate contracts**: where the temp project documents a command
   or validation contract, check whether the installed surface appears to match
   that contract.
5. Note any missing files, wrong paths, broken references, contradictory
   install-record entries, or mismatched runtime surfaces.

### Step 3: CLI Adaptation Surface Scan

For each CLI carrier in the temp project:

1. **Skills**: catalog installed skills and check for:
   - missing workflow skills referenced elsewhere in the temp project
   - duplicate or contradictory skill carriers
   - stale instructions that reference absent runtime surfaces
2. **Commands**: catalog installed commands and check for:
   - missing command surfaces referenced by docs, hooks, or installed routing
   - stale references or broken paths
3. **Agents**: catalog installed agents and check for:
   - legacy names that conflict with the current installed workflow behavior
   - missing routing or context-loading guidance where the temp project expects
     it
4. **Hooks / runtime controls**: catalog hook configurations and check for:
   - missing patch markers or strong-gate markers referenced by the temp
     project's own workflow files
   - hook scripts that reference wrong or missing paths
   - runtime-control drift between installed docs/config and actual patched
     files

### Step 4: Document and Reference Integrity

For every installed workflow document or installed runtime-control document:

1. Check that internal cross-references resolve to existing temp-project files.
2. Check that helper-script references use the installed temp-project paths
   actually present in the temp project.
3. Check that execution-card references resolve when such cards are installed.
4. Flag any broken, stale, contradictory, or misleading references.

### Step 5: Residual and New Issue Detection

1. **Residual artifacts**: flag any workflow-related file, directory, or
   reference that appears retired, stale, or contradictory within the temp
   project's own current workflow surfaces.
2. **Install/runtime drift**: compare `.trellis/workflow-installed.json`
   against the actual installed state when the record exists. Flag
   inconsistencies.
3. **Missing surfaces**: flag workflow surfaces referenced by temp-project docs,
   configs, or records that are absent from the actual temp project.
4. **New issues**: flag anomalies not covered above — wrong permissions,
   encoding issues, broken assumptions, unexpected files, or contradictory
   routing/runtime behavior.

### Step 6: Compile WORKFLOW_QUESTIONS.md

1. Assign unique IDs to each finding: `WS-001`, `WS-002`, etc. (sequential,
   zero-padded to 3 digits).
2. For each finding, include all required fields per the finding entry schema:
   - Category (from the 6 allowed values)
   - Severity Estimate (P0/P1/P2, preliminary)
   - Repair Classification (`confirmed-defect`, `design-debt`, or
     `evidence-gap`)
   - Origin (`trellis-native` or `workflow-source`)
   - Evidence Layer (`generated-target-baseline`,
     `generated-target-installed`, or `generated-target-runtime`)
   - Evidence (list of observations)
   - Temp Project Location (relative path within temp project, or a concise
     multi-path description when more than one surface is involved)
   - Description (what is wrong and why)
   - Suggested Investigation (what `workflow-repair` should verify in the temp
     project before deciding the source-side repair)
3. Write the required `Analysis Summary` section so the report explicitly
   includes:
   - overall problem analysis
   - gap / missing-surface analysis
   - residual issue summary
   - new issue summary
   - confirmed-defect summary
   - design-debt summary
   - evidence-gap summary
4. Write the document using the format from
   `references/scan-output-template.md`. In particular, the frontmatter must
   contain these exact keys and spellings:
   - `document-type: workflow-questions`
   - `protocol: workflow-scan-repair-v4`
   - `trellis-version`
   - `workflow-version`
   - `workflow-schema-version`
   - `scan-timestamp`
   - `temp-project-root`
   - `total-findings`
   - `p0-count`
   - `p1-count`
   - `p2-count`
5. Only the coordinator writes to the temp project root as
   `WORKFLOW_QUESTIONS.md`, even in `--agent` mode.
6. Immediately read the file back and verify all of the following before
   declaring success:
   - the frontmatter contains every required key above using the exact
     kebab-case spellings from the shared template
   - the report contains `## Scan Summary`
   - the report contains `## Analysis Summary`
   - the report contains a `### WS-NNN` heading for every finding
   - the `total-findings`, `p0-count`, `p1-count`, and `p2-count` values match
     the actual finding count and per-severity counts in the document body
   - the analysis summary includes Confirmed Defects, Design-Debt Items, and
     Evidence-Gap Items
   - each finding block includes Category, Severity Estimate, Repair
     Classification, Origin, Evidence Layer, Evidence, Temp Project Location,
     Description, and Suggested Investigation
7. If any required key or section is missing, or if snake_case replacements
   or alternate names such as `generated_at`, `trellis_version`,
   `temp_project_path`, or `total_findings` appear instead of the shared
   contract fields, treat the run as failed and correct the document before
   proceeding.
8. If `workflow-version` or `workflow-schema-version` resolves to `unknown`,
   empty, or any other placeholder rather than a concrete embedded value, stop
   as **Blocked / Invalid Embedded State** instead of reporting success.

### Step 7: Echo and Stop

1. Echo the output summary only after the read-back validation in Step 6
   passes:
   - temp project path
   - output file path
   - total findings, P0/P1/P2 counts
2. Suggest the next step: run `workflow-repair` in the source project to
   consume the report.
3. Do not attempt any fixes, aggregation, or workflow state changes.

## Error Handling

| Case | Behavior |
|------|----------|
| Temp project not found | Stop as **Blocked / Temp Project Not Found**. Suggest creating or locating the temp project first. |
| Temp project not fully initialized | Stop as **Blocked / Invalid Temp Project**. Verify `.trellis/` and `.version` exist. |
| Temp project not workflow-embedded | Stop as **Blocked / Workflow Not Embedded**. Verify the temp project really contains an embedded workflow instead of only the Trellis baseline. |
| `--agent` requested but unsupported | Stop as **Blocked / Agent Mode Unsupported**. Explain that the current platform/session cannot safely run the required helper agents. Do not silently fall back to inline mode. |
| Helper handoffs all fail or time out for a delegated slice | Keep coordinator ownership. Re-check the slice locally when safe, or skip that slice conservatively instead of treating helper failure itself as a workflow finding. |
| Helper claims conflict and local re-check cannot resolve the dispute | Drop the disputed claim from final findings rather than guessing. Continue the scan if the remaining evidence still supports a valid report. |
| `WORKFLOW_QUESTIONS.md` already exists | Stop and ask whether to overwrite or append. |
| No findings | Write `WORKFLOW_QUESTIONS.md` with `total-findings: 0` and all counts at 0, then still perform the Step 6 read-back validation before reporting success. |

## Related Skills

- `workflow-repair`: consumer/fixer pair — consumes the
  `WORKFLOW_QUESTIONS.md` this skill produces
- `workflow-audit`: comprehensive audit with version gates, evidence mainline,
  and runtime validation (complementary, not replacement)
- `workflow-capability-audit`: version-drift audit

## References

- paired repair-side compatibility note:
  - `workflow-repair --auto` is allowed later in the source project, but it
    must not change scan output generation, overwrite handling, or the shared
    `WORKFLOW_QUESTIONS.md` schema
  - any scan-side change to shared protocol, field, role boundary, or repair-
    relevant assumption must ship with the matching `workflow-repair`
    adaptation in the same change
- `references/scan-output-template.md`
- `references/helper-handoff-template.md`

## Tests

Required persisted scenario files:

- `tests/01-inline-default-no-agents.md`
- `tests/02-agent-assisted-supported.md`
- `tests/03-agent-mode-unsupported.md`
- `tests/04-helper-failure-local-compensation.md`
- `tests/05-unresolved-helper-conflict-dropped.md`
- `tests/06-partial-helper-output-local-followup.md`
- `tests/07-inline-when-speed-or-depth-only.md`
- `tests/08-classifies-repair-eligibility-before-emitting-findings.md`
- `tests/09-backup-original-preservation-is-not-defect.md`

Every test file must use the same structure:

- `Purpose`
- `Input`
- `Expected Mode`
- `Expected Key Behaviors`
- `Must Not`

## Examples

### Example 1: Standard Scan in Temp Project

```text
User: /workflow-scan

AI:
1. Auto-detect temp project: run `trellis -v`, read the live version, then resolve `/tmp/trellis-{LIVE_VERSION}-2/`
2. Validate: `.trellis/` exists, `.version` matches, workflow embed markers exist
3. Inventory the workflow surfaces currently present in the temp project
4. Execute script/command/CLI/reference/residual checks using only temp-project evidence
5. Compile findings and analysis summary into `WORKFLOW_QUESTIONS.md`
6. Echo:
   ✅ Workflow scan complete
   📁 Temp Project: /tmp/trellis-{LIVE_VERSION}-2
   📄 Report: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   📊 Findings: 5 total (P0: 1, P1: 2, P2: 2)
   ➡️ Next: run /workflow-repair in the source project
      Optional: use `/workflow-repair --auto` only if you want the later
      source-project repair run to continue into its normal close-out flow
      Note: that auto close-out applies to the dedicated repair task that
      `workflow-repair` creates or switches to, not to any unrelated
      pre-existing task
```

### Example 2: Agent-Assisted Scan

```text
User: /workflow-scan --agent

AI:
1. Resolve the temp project path and confirm that the current session can use helper agents safely
2. Keep coordinator ownership in the current session for overwrite prompts, final finding judgment, report writing, and read-back validation
3. Split independent scan slices across multiple helper agents:
   - helper A: scripts and commands
   - helper B: CLI adaptation surfaces
   - helper C: workflow documents and runtime-control references
4. Review each helper handoff, fill any evidence gaps locally, and compile one shared `WORKFLOW_QUESTIONS.md`
5. Read the report back and verify the required frontmatter keys, summary sections, and count consistency
6. Echo:
   ✅ Workflow scan complete
   📁 Temp Project: /tmp/trellis-{LIVE_VERSION}-2
   📄 Report: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   📊 Findings: 4 total (P0: 1, P1: 1, P2: 2)
   ➡️ Next: run /workflow-repair in the source project
      Optional: use `/workflow-repair --auto` only if you want the later
      source-project repair run to continue into its normal close-out flow
      Note: that auto close-out applies to the dedicated repair task that
      `workflow-repair` creates or switches to, not to any unrelated
      pre-existing task
```

### Example 3: Agent Mode Unsupported

```text
User: /workflow-scan --agent

AI:
❌ Blocked / Agent Mode Unsupported
   The current platform/session cannot safely run helper agents with explicit ownership boundaries.
   Reason: helper invocation is unavailable here, or a stronger session rule still requires inline execution.
   Next: re-run `/workflow-scan` inline, or move to an agent-capable main session that allows bounded helper delegation.
```

### Example 4: Temp Project Not Found

```text
User: /workflow-scan

AI:
❌ Blocked / Temp Project Not Found
   Expected: /tmp/trellis-{LIVE_VERSION}-2/
   The directory does not exist or is not a valid trellis project.
   Suggestion: create or locate the temp project first, then re-run /workflow-scan.
```

### Example 5: Clean Install With No Issues

```text
User: /workflow-scan

AI:
1. Auto-detect temp project from the current `trellis -v` result
2. Execute all scan steps against the temp project's installed workflow
3. No anomalies found
4. Write WORKFLOW_QUESTIONS.md with total-findings: 0

   ✅ Workflow scan complete — no issues found
   📁 Temp Project: /tmp/trellis-{LIVE_VERSION}-2
   📄 Report: /tmp/trellis-{LIVE_VERSION}-2/WORKFLOW_QUESTIONS.md
   📊 Findings: 0 total (P0: 0, P1: 0, P2: 0)
```

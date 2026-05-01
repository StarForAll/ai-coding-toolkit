---
name: workflow-audit
description: Audit workflow definitions under `docs/workflows/*`, including workflow source assets, embed/install flows, CLI-native adaptation, and post-install verification boundaries. Use this whenever the user wants to inspect, validate, or challenge a workflow itself before editing source files, especially when `/tmp + trellis init` validation, Codex handoff boundaries, or Claude Code / OpenCode / Codex adaptation checks are involved. Do not use this for ordinary business code, application features, or generic implementation review.
---

# workflow-audit

`workflow-audit` is the maintainer-side audit entry point for workflows in this repository. It verifies whether workflow problems are real before any source edits, then produces evidence-based conclusions, repair directions, and controlled next-step recommendations.

If this file conflicts with `.trellis/spec/skills/workflow-audit.md`, treat the spec file as the behavioral source of truth.

## Purpose

Use this skill to:

- audit workflow source assets under `docs/workflows/*`
- audit workflow install / embed / post-install verification flows
- audit Claude Code / OpenCode / Codex carrier and adaptation boundaries
- verify whether candidate workflow issues are real rather than assuming they already are

Do not use this skill to:

- review ordinary business code
- review application feature implementation quality
- review product requirements or PRD content
- perform generic code review unrelated to workflows

## Trigger Conditions

This skill should trigger proactively when the user intends to:

- "audit this workflow"
- "confirm whether this workflow really has a problem before changing it"
- "check whether `docs/workflows/*` has defects"
- "validate this workflow's embed / install / post-install behavior"
- "check whether Codex / Claude Code / OpenCode adaptation is correct"
- "validate the Codex handoff boundary and stop condition"
- "verify whether these workflow optimization points are real issues"
- "create a temporary project under `/tmp` to validate a workflow"

## Input

Natural-language input is allowed, but prefer the recommended field contract. A short copyable template lives in `references/input-template.md`.

Key fields:

- `workflow_path`
  - default: `docs/workflows/新项目开发工作流/`
- `candidate_issues`
  - default: empty, meaning the skill must discover issues proactively
- `need_runtime_validation`
  - default: `auto`
- `force_full_brainstorm`
  - default: `no`
- `current_cli`
  - default: infer from the runtime environment first
  - ask the user only if a CLI-sensitive path is reached and the CLI still cannot be determined safely

Constraints:

- exactly one `workflow_path` per run
- if multiple workflow targets appear in the input, stop and require the user to choose one explicit target
- do not expose a dedicated `preferred_handoff_cli` field; default handoff order is `Claude Code -> OpenCode`

## Output

Two output modes exist:

- lightweight mode: use the simplified chat structure from `references/lightweight-output-template.md`
- non-trivial audit mode: incrementally maintain `audit-report.md` in the task, using `references/audit-report-template.md`

Both modes must:

- distinguish confirmed issues, unconfirmed items, false alarms, and blocked states
- conclude only from evidence
- stop with a controlled next-step recommendation

Each confirmed issue must include at least:

- `priority`
- `conclusion`
- `evidence source`
- `validation action`
- `impact scope`
- `fix direction`

## Workflow

### Step 1: Resolve target and mode

1. Resolve exactly one `workflow_path`.
2. Decide whether this is a lightweight static audit or a non-trivial audit.
3. Escalate into the non-trivial path when any of the following is true:
   - a temporary project under `/tmp` is required
   - `trellis init` is required
   - embed / install / post-install behavior must be validated
   - CLI handoff may be triggered
   - the user explicitly requires the full `brainstorm` mainline

If lightweight mode needs to escalate, explain why lightweight mode is no longer sufficient before switching contexts.

### Step 2: Use the correct control path

- Lightweight mode:
  reuse `trellis:brainstorm` discipline for evidence-first work, action-before-asking, and one-question-at-a-time clarification, but do not create a task, do not create `prd.md`, and do not create `audit-report.md`
- Non-trivial mode:
  explicitly invoke `trellis:brainstorm`

`grill-me` is not a post-audit recommendation. Use it only as a conditional clarification submode inside the current audit context when key branches remain unresolved after evidence gathering and continuing would require guessing.

### Step 3: Build the task context

- If a non-audit active task already exists:
  create a child audit task and switch into it immediately
- If no active task exists:
  create a top-level audit task
- Default task title:
  `workflow-audit: <workflow-name>`

Child-audit-task return rules:

- do not return to the parent merely because an audit report exists
- `workflow-audit` itself only advances the audit task to the "audit conclusion produced and waiting for confirmation" stop point
- once the user confirms the conclusion, remediation is handled by later normal phases/skills inside the same audit task
- return to the parent only after remediation is complete and the human confirms the audit task is done

### Step 4: Gather evidence

Read local repo / docs / specs first, then decide whether runtime validation is needed.

Always separate evidence into:

- source-maintenance context
- `/tmp` target-project validation context

If the user supplied `candidate_issues`, always treat them as hypotheses to validate, never as established defects.

### Step 5: Handle the Codex boundary

If the audit reaches the formal temporary-project embed step and the current main executor is Codex:

- stop the formal embed execution immediately
- emit a handoff block
- use default handoff order `Claude Code -> OpenCode`
- require the handoff sequence to include:
  - `detect-embed-state.py`
  - `install-workflow.py --dry-run`
  - formal `install-workflow.py` with explicit non-Codex executor confirmation
  - post-install `upgrade-compat.py --check`

Use `references/codex-handoff-template.md` for the handoff content.

Additional constraints:

- the takeover CLI may perform runtime validation only during the audit stage
- the takeover CLI must not modify workflow source files
- returned handoff evidence must be merged back into the current audit report

### Step 6: Report and stop

After finishing the audit:

- output or update the current report
- recommend the next step, but do not execute it
- allowed recommendation targets are only:
  - `trellis:brainstorm`
  - `trellis:start`
  - `trellis:check`
  - `trellis:update-spec`
  - if none fit, give a plain-language next action instead

Each recommendation must say:

- why it is recommended
- what trigger condition makes it the right choice now
- why stronger alternatives were not selected

Then stop and wait for user confirmation.

## References

Read these only when needed:

- `references/input-template.md`
  when the input field template or a full input example is needed
- `references/lightweight-output-template.md`
  when lightweight-mode output is needed
- `references/audit-report-template.md`
  when a non-trivial audit report must be maintained
- `references/codex-handoff-template.md`
  when Codex must stop and hand off the formal embed step

## Tests

Use these files to validate the first-version behavior boundaries:

- `tests/01-lightweight-static.md`
- `tests/02-nontrivial-full-audit.md`
- `tests/03-codex-handoff.md`

Every test file must use the same structure:

- `Purpose`
- `Input`
- `Expected Mode`
- `Expected Key Behaviors`
- `Must Not`

## Examples

### Example 1: Lightweight static audit

Input:
Check whether `docs/workflows/新项目开发工作流/` has obvious structural or rule-propagation issues. Do not perform `/tmp` validation yet.

Output:
Remain in lightweight mode, perform static inspection only, produce the simplified structured result, and do not create a task.

### Example 2: Non-trivial embed audit

Input:
Audit the embed flow of `docs/workflows/新项目开发工作流/`. Create a temporary project under `/tmp`, run `trellis init`, and verify the stop-and-handoff behavior when Codex reaches the formal embed step.

Output:
Enter the non-trivial path, create an audit task, invoke `trellis:brainstorm`, emit a Codex handoff block when required, and maintain `audit-report.md` inside the task.

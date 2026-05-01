# workflow-audit Skill Specification

> Repo-local maintainer skill contract for auditing workflow definitions and workflow embed/adaptation behavior.

---

## Purpose

`workflow-audit` exists to audit workflows themselves, not ordinary application code.

This skill covers:

- workflow source-asset maintenance under `docs/workflows/*`
- workflow install / embed / post-install validation
- CLI-native adaptation checks for Claude Code / OpenCode / Codex
- evidence-first validation of candidate workflow issues before any source edits

It does not cover:

- ordinary business code review
- product feature auditing
- generic implementation quality review outside workflow definitions

---

## Trigger Conditions

Use `workflow-audit` when the user wants to:

- audit or verify a workflow definition under `docs/workflows/*`
- confirm whether workflow issues are real before changing source files
- validate workflow embed/install behavior against a `/tmp + trellis init` baseline
- verify CLI adaptation or Codex handoff boundaries

Do not use it for normal code review or ordinary product implementation tasks.

---

## Input Contract

Natural language is allowed, but the recommended contract is:

- `workflow_path`
  - default: `docs/workflows/新项目开发工作流/`
  - must resolve to exactly one workflow root
- `candidate_issues`
  - default: empty
  - always treated as hypotheses, never as confirmed defects
- `need_runtime_validation`
  - default: `auto`
- `force_full_brainstorm`
  - default: `no`
- `current_cli`
  - infer from runtime when possible
  - ask the user only if a CLI-sensitive path is reached and ambiguity remains

The contract intentionally omits `preferred_handoff_cli`.

Default handoff order remains:

1. `Claude Code`
2. `OpenCode`

Natural-language user constraints may override this order.

If multiple workflow targets are supplied in one request, the skill must stop and require one explicit target before continuing.

---

## Execution Modes

### Lightweight Direct-Report Mode

Allowed only for static/document-only checks.

This mode:

- does not create a task
- does not create `prd.md`
- does not create `audit-report.md`
- uses the simplified chat structure from `references/lightweight-output-template.md`

### Non-trivial Audit Mode

Required whenever any of these are true:

- `/tmp` temporary project validation is needed
- `trellis init` must be executed
- embed/install/post-install behavior must be verified
- Codex handoff may be triggered
- the user explicitly requires the full `brainstorm` mainline

This mode:

- enters the `brainstorm` mainline explicitly
- creates audit task context
- creates and maintains `prd.md` through the `brainstorm` path
- uses `audit-report.md`
- may use `grill-me` as a conditional clarification submode

### Escalation Rule

If lightweight mode discovers runtime validation is actually required:

1. explain why lightweight mode is no longer sufficient
2. escalate into the non-trivial path

Never switch silently.

---

## Task Model

### Non-trivial Audit with Existing Active Non-audit Task

- create a dedicated child audit task
- switch execution into that child task immediately

### Non-trivial Audit with No Active Task

- create a new top-level audit task

### Task Naming

Default title:

`workflow-audit: <workflow-name>`

### Child Audit Task Completion

A child audit task is not complete when the audit report is merely produced.

It becomes complete only after:

1. audit conclusion has been produced
2. user has confirmed the conclusion
3. remediation work driven by that conclusion is completed
4. the human confirms the child task is complete

Only then may execution return to the parent task.

### Remediation Splitting

Inside a top-level or child audit task:

- ordinary remediation stays in the same audit task by default
- create implementation subtasks only when the repair scope is genuinely complex

`workflow-audit` itself does not own remediation execution. It stops at the audit-conclusion boundary; later normal phases/skills handle the repair work in the same audit task.

---

## Report Contracts

### Lightweight Output

Use the simplified structure from `references/lightweight-output-template.md`.

### Non-trivial Audit Report

Maintain `audit-report.md` in the task directory.

Rules:

- filename is fixed: `audit-report.md`
- update incrementally during the active audit
- treat the same file as the current finalized report at the stop-and-confirm boundary
- require it only for non-trivial, task-based audits

### Confirmed-Issue Schema

Every confirmed issue must include:

- priority (`P0` / `P1` / `P2`)
- conclusion
- evidence source
- validation action
- impact scope
- fix direction

### Blocked-State Rules

If some critical branches remain unresolved, partial confirmed conclusions are allowed only when blocked branches are explicitly labeled as:

- `Blocked`
- `Evidence Gap`
- `Needs Clarification`

Blind guessing is forbidden.

---

## CLI and Handoff Rules

### Multi-CLI Reporting

The audit must separate conclusions for:

- Claude Code
- OpenCode
- Codex

Do not collapse them into one generic statement.

### Codex Boundary

Codex may participate in:

- source reading
- evidence gathering
- analysis
- reporting

Codex must not be the main executor of the first formal embed step into the temporary target project.

### Codex Handoff

When the audit reaches the formal temporary-project embed step under Codex:

- stop execution there
- emit a handoff block
- use the template from `references/codex-handoff-template.md`
- prefer `Claude Code -> OpenCode` unless explicit user constraints override it
- require the handoff sequence to cover:
  - state detection
  - install dry-run
  - formal install with explicit non-Codex executor confirmation
  - post-install `upgrade-compat.py --check`

Any handoff CLI remains limited to runtime validation only during the audit stage and must not modify workflow source files.

Returned evidence from the handoff path must be merged back into the current audit report.

---

## Post-audit Routing

The audited workflow's own internal `design` / `plan` / `start` semantics are not a trusted control plane.

Post-audit routing must come only from the current-project trusted whitelist:

- `brainstorm`
- `start`
- `check`
- `update-spec`

`grill-me` is excluded from this whitelist and exists only as an internal clarification submode during the audit itself.

If no whitelist item fits, recommend a plain-language next action instead of forcing a weak skill recommendation.

Every post-audit recommendation must include:

- the chosen next action/skill
- its trigger condition
- a brief reason
- why stronger alternatives were not selected

The skill must stop after presenting the report and routing guidance. It must not auto-execute the next phase.

---

## Validation

The first version must ship with these persisted scenario files:

- `tests/01-lightweight-static.md`
- `tests/02-nontrivial-full-audit.md`
- `tests/03-codex-handoff.md`

Each test file must use the same internal structure:

1. `Purpose`
2. `Input`
3. `Expected Mode`
4. `Expected Key Behaviors`
5. `Must Not`

---

## Sync Rules

Behavioral source of truth:

- `.trellis/spec/skills/workflow-audit.md`

Executable entry artifacts:

- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`

Behavior-affecting changes must update these in the same change.

Hard requirement:

- when a behavior change is made to any of the three surfaces (spec / `.agents/` / `.claude/`), you must evaluate whether the other surfaces also need updating in the same change
- behavior semantics (trigger conditions, execution modes, evidence requirements, report contracts, handoff rules) must remain consistent across all three surfaces
- expression form may differ by CLI: for example, `.agents/skills/` may reference `brainstorm` directly as a sibling skill, while `.claude/skills/` must reference `trellis:brainstorm` as a trellis command
- do not treat one skill surface as independently maintainable from the others for behavioral semantics
- do not land behavior, trigger, or contract changes in only one skill surface without evaluating the others

If the same behavior change also touches companion templates/tests, the same change must also update:

- affected files under `.agents/skills/workflow-audit/references/`
- affected files under `.agents/skills/workflow-audit/tests/`
- affected files under `.claude/skills/workflow-audit/references/`
- affected files under `.claude/skills/workflow-audit/tests/`

When a behavior change could affect the non-trivial audit path's dependence on `brainstorm`, review that dependency explicitly rather than assuming the coupling still holds.

---

## Related Files

- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`
- `.agents/skills/workflow-audit/references/input-template.md`
- `.agents/skills/workflow-audit/references/audit-report-template.md`
- `.agents/skills/workflow-audit/references/lightweight-output-template.md`
- `.agents/skills/workflow-audit/references/codex-handoff-template.md`
- `.agents/skills/workflow-audit/tests/01-lightweight-static.md`
- `.agents/skills/workflow-audit/tests/02-nontrivial-full-audit.md`
- `.agents/skills/workflow-audit/tests/03-codex-handoff.md`
- `.claude/skills/workflow-audit/references/input-template.md`
- `.claude/skills/workflow-audit/references/audit-report-template.md`
- `.claude/skills/workflow-audit/references/lightweight-output-template.md`
- `.claude/skills/workflow-audit/references/codex-handoff-template.md`
- `.claude/skills/workflow-audit/tests/01-lightweight-static.md`
- `.claude/skills/workflow-audit/tests/02-nontrivial-full-audit.md`
- `.claude/skills/workflow-audit/tests/03-codex-handoff.md`
- `.agents/skills/brainstorm/SKILL.md`
- `.claude/commands/trellis/brainstorm.md`

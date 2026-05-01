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
  - default: empty, meaning the skill discovers issues proactively through the full evidence mainline
  - when supplied: supplementary focus points injected into each evidence step; the evidence mainline still executes in full regardless
  - always treated as hypotheses, never as confirmed defects
  - does not switch execution paths
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

## Evidence Mainline

A, B, C always execute in order, regardless of whether `candidate_issues` are supplied. `candidate_issues` serve as supplementary focus points referenced within each step — they do not change the mainline.

D (Runtime Validation) is conditional, determined by findings from A/B/C and input parameters.
E (Output Findings) always executes as the final report step.

Three execution modes determine which evidence steps run and how findings are delivered:

| Mode | Steps | Task | brainstorm | prd.md | audit-report.md |
|------|-------|------|------------|--------|-----------------|
| Lightweight static | A, B, C, E | N | N | N | N |
| Task-based static | A, B, C, E (D skipped) | Y | Y | Y | Y |
| Task-based runtime | A, B, C, D, E | Y | Y | Y | Y |

Mode selection is described in the Execution Modes section below.

Every piece of evidence collected throughout the mainline must be tagged with its source layer:

- `source repo` — files, documents, scripts within the workflow directory under `docs/workflows/`
- `generated target project` — files produced by `trellis init` or `install-workflow.py` in the `/tmp` target project
- `runtime command output` — stdout/stderr/exit code from executed commands

This labeling is mandatory because the core audit operation (gap analysis) compares what the source repo declares against what the target project actually contains. Without source-layer tags, the two are easily conflated.

### A. Understand Target System Mechanics

Before auditing the workflow, understand the system it operates within:

- trellis `init` 产物模型: `.trellis/`, `.claude/`, `.opencode/`, `.agents/skills/`, `.codex/`
- 各 CLI 的原生承载方式（commands / skills / agents / hooks 的目录约定）
- workflow 自身的 install / upgrade / uninstall 脚本实际行为
- 工作流嵌入执行规范中的状态机与前置条件

### B. Static Evidence Gathering

Read authoritative entry documents and indexes first, then trace references outward:

- catalog every claim the workflow makes: steps, artifacts, boundaries, contracts
- note every referenced file path, script, template
- identify every cross-reference dependency
- cross-check referenced paths against actual filesystem

### C. Structured Gap Analysis

Compare document claims against actual definition completeness:

- 文档声明了某步骤 / 产物 / 边界，但对应定义文件缺失或不完整 → 确认为 gap
- 流程层面"有"但执行闭环层面"没做完"的内容 → 记录为 incomplete closure
- 跨文档引用的一致性：是否引用了不存在的文件、旧路径、或已过时的路径名
- 各 CLI 适配层之间是否存在行为漂移（同一语义在不同 CLI 下实现不一致）
- 隐藏目录托管边界：安装后产物是否与 trellis 基线 + workflow 声明的托管范围一致

### D. Runtime Validation

Required when embed / install / post-install behavior must be verified:

- 在 `/tmp` 创建纯净 Git 项目，满足安装前置条件后执行 `trellis init`
- 执行标准嵌入链: `detect-embed-state.py` → `install-workflow.py --dry-run` → `install-workflow.py` → `upgrade-compat.py --check`
- 检查安装后隐藏目录（`.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`）与 trellis 基线 + workflow 托管声明是否一致
- 比较文档声明的安装产物与实际落盘产物
- 当 Codex 为主执行器时，触发 Codex handoff（见 CLI and Handoff Rules）

### E. Output Findings

Classify every finding:

- confirmed issues: P0 / P1 / P2 with full confirmed-issue schema
- unconfirmed items / false alarms
- blocked items: Blocked / Evidence Gap / Needs Clarification

Blind guessing is forbidden. If critical branches remain unresolved, partial conclusions are allowed only when blocked branches are explicitly labeled.

---

## Execution Modes

Mode is not a pre-decision made at input time. It is the outcome of evidence mainline steps A, B, and C. Steps A, B, and C always execute regardless of mode.

After step C, two independent judgments determine the execution mode:

**Judgment 1 — Taskify?** Should the audit create a task, enter brainstorm, and maintain `prd.md` + `audit-report.md`?

- `force_full_brainstorm: yes` → yes: enter task-based path
- `need_runtime_validation: yes` → yes: enter task-based path (D needed, which always requires task context)
- `need_runtime_validation: auto` AND Step 2 findings indicate D trigger conditions are met → yes
- Otherwise → no: lightweight static mode (skip to step E directly)

**Judgment 2 — Execute D?** (Only meaningful if the answer to Judgment 1 is "yes")

Step D is required when any of these are true:

- `/tmp` temporary project validation is needed
- `trellis init` must be executed
- embed/install/post-install behavior must be verified
- Codex handoff may be triggered
- `need_runtime_validation` is `yes`

`force_full_brainstorm: yes` does NOT by itself force Step D. D must be justified by one of the conditions above.

When neither Judgment 1's conditions nor D-trigger conditions are met: lightweight static mode.
When Judgment 1 is "yes" but D is not needed: task-based static mode (create task, enter brainstorm, maintain `prd.md` and `audit-report.md`, then skip D and go to E).
When both judgments are "yes": task-based runtime mode (create task, enter brainstorm, maintain `prd.md` and `audit-report.md`, execute D, then output E).

### Lightweight static mode

- does not create a task
- does not create `prd.md`
- does not create `audit-report.md`
- outputs using the simplified chat structure from `references/lightweight-output-template.md`

### Task-based static mode

When the skill determines task context is warranted but runtime validation is not required:

- create audit task context (child task if another non-audit task is active, otherwise top-level)
- enter the `brainstorm` mainline explicitly as the control container
- create and maintain `prd.md` through the `brainstorm` path
- maintain `audit-report.md` using `references/audit-report-template.md`
- seed `audit-report.md` with findings from steps A/B/C already collected
- skip step D → proceed to step E (report via `audit-report.md`)
- may use `grill-me` as a conditional clarification submode
- stop with a controlled next-step recommendation

### Task-based runtime mode

When the skill determines both task context and runtime validation are required:

- all task-based static mode behaviors above, plus:
- execute step D within CLI-allowed boundaries: `/tmp` project, `trellis init`, embed chain, post-install verification (Codex must stop and hand off before formal embed)
- merge runtime evidence into `audit-report.md`
- when D reaches Codex boundary: emit handoff block (see CLI and Handoff Rules)
- output step E via `audit-report.md`
- stop with a controlled next-step recommendation

### Mode transition boundary

When transitioning from step C to a task-based mode:

1. explain the rationale for the chosen mode
2. if entering task-based static: explain why task context is warranted and why D is not needed
3. if entering task-based runtime: explain why runtime validation is necessary
4. proceed to create task context and enter brainstorm
5. seed `audit-report.md` with already-collected evidence from steps A/B/C

Never switch modes silently. Never discard A/B/C findings when entering a task-based mode.

### User-set `need_runtime_validation: no` conflict

When the user explicitly set `need_runtime_validation: no` but step C findings conclusively demonstrate that runtime validation is necessary (D trigger conditions are met):

- do NOT silently skip D
- output a Needs Confirmation block using `references/needs-confirmation-template.md`
- let the user decide whether to override their original setting
- do not proceed to D without explicit user confirmation

---

## Task Model

### Task-based Audit with Existing Active Non-audit Task

- create a dedicated child audit task
- switch execution into that child task immediately

### Task-based Audit with No Active Task

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

### Lightweight Static Output

Use the simplified structure from `references/lightweight-output-template.md`.

### Task-based Audit Report

Maintain `audit-report.md` in the task directory. This applies to both task-based static and task-based runtime modes.

Rules:

- filename is fixed: `audit-report.md`
- update incrementally during the active audit
- treat the same file as the current finalized report at the stop-and-confirm boundary
- require it only for task-based audits

### Confirmed-Issue Schema

Every confirmed issue must include:

- priority (`P0` / `P1` / `P2`)
- conclusion
- evidence source (with source layer tag: `source repo` / `generated target project` / `runtime command output`)
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
- `tests/04-task-based-static.md`
- `tests/05-need-runtime-validation-no-escalation.md`

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

When a behavior change could affect the task-based audit path's dependence on `brainstorm`, review that dependency explicitly rather than assuming the coupling still holds.

---

## Related Files

- `.agents/skills/workflow-audit/SKILL.md`
- `.claude/skills/workflow-audit/SKILL.md`
- `.agents/skills/workflow-audit/references/input-template.md`
- `.agents/skills/workflow-audit/references/audit-report-template.md`
- `.agents/skills/workflow-audit/references/lightweight-output-template.md`
- `.agents/skills/workflow-audit/references/codex-handoff-template.md`
- `.agents/skills/workflow-audit/references/needs-confirmation-template.md`
- `.agents/skills/workflow-audit/tests/01-lightweight-static.md`
- `.agents/skills/workflow-audit/tests/02-nontrivial-full-audit.md`
- `.agents/skills/workflow-audit/tests/03-codex-handoff.md`
- `.agents/skills/workflow-audit/tests/04-task-based-static.md`
- `.agents/skills/workflow-audit/tests/05-need-runtime-validation-no-escalation.md`
- `.claude/skills/workflow-audit/references/input-template.md`
- `.claude/skills/workflow-audit/references/audit-report-template.md`
- `.claude/skills/workflow-audit/references/lightweight-output-template.md`
- `.claude/skills/workflow-audit/references/codex-handoff-template.md`
- `.claude/skills/workflow-audit/references/needs-confirmation-template.md`
- `.claude/skills/workflow-audit/tests/01-lightweight-static.md`
- `.claude/skills/workflow-audit/tests/02-nontrivial-full-audit.md`
- `.claude/skills/workflow-audit/tests/03-codex-handoff.md`
- `.claude/skills/workflow-audit/tests/04-task-based-static.md`
- `.claude/skills/workflow-audit/tests/05-need-runtime-validation-no-escalation.md`
- `.agents/skills/brainstorm/SKILL.md`
- `.claude/commands/trellis/brainstorm.md`

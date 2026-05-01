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
  - default: empty, meaning the skill discovers issues proactively through the full evidence mainline
  - when supplied: supplementary focus points injected into each evidence step; the mainline still executes in full
  - always treated as hypotheses, never as confirmed defects
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

Two output formats exist, serving three execution modes (see Workflow below for mode selection):

- Lightweight static mode: use the simplified chat structure from `references/lightweight-output-template.md`
- Task-based mode (static or runtime): incrementally maintain `audit-report.md` in the task, using `references/audit-report-template.md`

Both formats must:

- distinguish confirmed issues, unconfirmed items, false alarms, and blocked states
- conclude only from evidence
- stop with a controlled next-step recommendation

Each confirmed issue must include at least:

- `priority`
- `conclusion`
- `evidence source` (tagged with source layer: `source repo` / `generated target project` / `runtime command output`)
- `validation action`
- `impact scope`
- `fix direction`

## Workflow

### Step 1: Resolve target and parse input

1. Resolve exactly one `workflow_path`.
2. Parse input parameters: `candidate_issues`, `need_runtime_validation`, `force_full_brainstorm`, `current_cli`.
3. Mode is NOT decided here — proceed to Step 2 regardless.

### Step 2: Execute evidence mainline A → B → C

The following three sub-steps always execute. If `candidate_issues` were supplied, reference them as supplementary focus points within each sub-step. The mainline is the same whether mode ends up lightweight static or task-based.

`grill-me` may be used as a clarification submode during gap analysis (step 2c) when key branches remain unresolved and continuing would require guessing. It is not a post-audit recommendation.

#### 2a. Understand target system mechanics

Before auditing the workflow, understand the system it operates within:

- trellis `init` 产物模型: `.trellis/`, `.claude/`, `.opencode/`, `.agents/skills/`, `.codex/`
- 各 CLI 原生承载方式（commands / skills / agents / hooks 的目录约定）
- workflow 自身 install / upgrade / uninstall 脚本的实际行为
- 工作流嵌入执行规范中的状态机与前置条件

#### 2b. Static evidence gathering

Read authoritative entry documents and indexes first, then trace references outward:

- catalog every claim the workflow makes: steps, artifacts, boundaries, contracts
- note every referenced file path, script, template
- identify every cross-reference dependency
- cross-check referenced paths against actual filesystem

#### 2c. Structured gap analysis

Compare document claims against actual definition completeness:

- 文档声明了某步骤 / 产物 / 边界，但对应定义文件缺失或不完整 → 确认为 gap
- 流程层面"有"但执行闭环"没做完"的内容 → 记录为 incomplete closure
- 跨文档引用一致性：是否引用了不存在的文件、旧路径、过时路径名
- 各 CLI 适配层之间是否存在行为漂移（同一语义在不同 CLI 下实现不一致）
- 隐藏目录托管边界：安装后产物是否与 trellis 基线 + workflow 声明的托管范围一致

### Step 3: Judge execution mode

Based on input parameters and Step 2 findings, determine whether the audit runs in lightweight static or task-based mode.

**Task-based mode** (proceed to Step 4) when:
- `need_runtime_validation: yes`
- `need_runtime_validation: auto` AND Step 2 findings indicate:
  - `/tmp` temporary-project validation is needed
  - embed / install / post-install behavior must be verified
  - Codex handoff may be triggered
- `force_full_brainstorm: yes` (enters task + brainstorm mainline; Step D is still judged separately in Step 4)

**Lightweight mode** (skip to Step 6) when:
- `need_runtime_validation: no`, UNLESS Step 2 findings conclusively prove runtime validation is necessary (see escalation rule below)
- `need_runtime_validation: auto` AND none of the Step D trigger conditions are met
- `force_full_brainstorm: no` (default) AND none of the above task-based conditions apply

**Escalation rule for `need_runtime_validation: no`**: If the user explicitly set `no` but Step 2 findings conclusively demonstrate that runtime validation is necessary, do NOT silently skip D. Instead, output a Needs Confirmation block using `references/needs-confirmation-template.md`, then let the user decide whether to proceed.

Lightweight mode: no task, no `prd.md`, no `audit-report.md`. Output using simplified template.
Task-based mode: proceed to Step 4 (task + brainstorm). Whether Step D executes is judged separately after task context is built.

### Step 4: Build task context and enter brainstorm

Only in task-based mode (when proceeding beyond Step 3):

- If a non-audit active task exists: create child audit task and switch into it immediately
- If no active task exists: create top-level audit task
- Default title: `workflow-audit: <workflow-name>`
- Invoke `trellis:brainstorm` as the control container
- Maintain `prd.md` through the `trellis:brainstorm` path
- Initialize `audit-report.md`, seeding it with evidence already collected in Step 2

After task context is built, judge whether Step D (runtime validation) is needed:
- `need_runtime_validation: yes` → proceed to Step 5
- `need_runtime_validation: no` AND Step 2 findings conclusively require runtime validation → output Needs Confirmation (see escalation rule and `references/needs-confirmation-template.md`) and stop; do NOT proceed until user responds
- `need_runtime_validation: auto` AND Step 2 findings met D trigger conditions → proceed to Step 5
- Otherwise → skip to Step 6
- `force_full_brainstorm: yes` does NOT by itself trigger Step D; D still requires one of the conditions above

Child-audit-task return rules:

- do not return to parent merely because an audit report exists
- workflow-audit only advances the task to "audit conclusion produced, waiting for confirmation"
- once user confirms conclusion, remediation is handled by normal phases/skills inside the same task
- return to parent only after remediation is complete and human confirms

### Step 5: Runtime validation (evidence mainline step D)

Only in task-based runtime mode. Execute the validation:

- 在 `/tmp` 创建纯净 Git 项目，满足安装前置条件后执行 `trellis init`
- 执行标准嵌入链: `detect-embed-state.py` → `install-workflow.py --dry-run` → `install-workflow.py` → `upgrade-compat.py --check`
- 检查安装后隐藏目录（`.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`）与 trellis 基线 + workflow 托管声明是否一致
- 对比文档声明的产物与实际落盘产物

#### Codex boundary

If this step reaches the formal temporary-project embed execution and the current main executor is Codex:

- stop the formal embed execution immediately
- emit a handoff block using `references/codex-handoff-template.md`
- default handoff order: `Claude Code -> OpenCode`
- require the handoff sequence to include: `detect-embed-state.py` → `install-workflow.py --dry-run` → formal install with non-Codex executor confirmation → `upgrade-compat.py --check`

Constraints:

- takeover CLI: runtime validation only, no workflow source edits
- returned handoff evidence must be merged into `audit-report.md`

### Step 6: Report and stop (evidence mainline step E)

- Lightweight static mode: output using `references/lightweight-output-template.md`
- Task-based mode (static or runtime): update and present `audit-report.md`

After presenting the report, recommend the next step but do not execute it. Allowed recommendation targets:

- `trellis:brainstorm`
- `trellis:start`
- `trellis:check`
- `trellis:update-spec`
- if none fit, give a plain-language next action

Each recommendation must state:

- why it is recommended
- what trigger condition makes it the right choice now
- why stronger alternatives were not selected

Stop and wait for user confirmation.

## References

Read these only when needed:

- `references/input-template.md`
  when the input field template or a full input example is needed
- `references/lightweight-output-template.md`
  when lightweight-mode output is needed
- `references/audit-report-template.md`
  when a task-based audit report must be maintained
- `references/needs-confirmation-template.md`
  when the escalation rule triggers and a Needs Confirmation block must be output
- `references/codex-handoff-template.md`
  when Codex must stop and hand off the formal embed step

## Tests

Use these files to validate the first-version behavior boundaries:

- `tests/01-lightweight-static.md`
- `tests/02-nontrivial-full-audit.md`
- `tests/03-codex-handoff.md`
- `tests/04-task-based-static.md`
- `tests/05-need-runtime-validation-no-escalation.md`

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
Remain in lightweight static mode, perform static inspection only, produce the simplified structured result, and do not create a task.

### Example 2: Task-based runtime audit

Input:
Audit the embed flow of `docs/workflows/新项目开发工作流/`. Create a temporary project under `/tmp`, run `trellis init`, and verify the stop-and-handoff behavior when Codex reaches the formal embed step.

Output:
Enter the task-based runtime path, create an audit task, invoke `trellis:brainstorm`, emit a Codex handoff block when required, and maintain `audit-report.md` inside the task.

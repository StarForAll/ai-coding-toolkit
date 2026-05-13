# workflow-audit Skill Specification

> Repo-local maintainer skill contract for auditing workflow definitions and workflow embed/adaptation behavior.

---

## Purpose

`workflow-audit` exists to audit workflows themselves, not ordinary application code.

This skill covers:

- workflow source-asset maintenance for the workflow rooted at `docs/workflows/新项目开发工作流/`
- workflow install / embed / post-install validation
- CLI-native adaptation checks for Claude Code / OpenCode / Codex
- evidence-first validation of candidate workflow issues before any source edits

`workflow-audit` is not a generic selector for arbitrary entries under `docs/workflows/`.
Its only supported workflow target is `docs/workflows/新项目开发工作流/`.

It does not cover:

- ordinary business code review
- product feature auditing
- generic implementation quality review outside workflow definitions
- Trellis version-drift or compatibility-upgrade analysis across versions; use `workflow-capability-audit` for that path

## Version Gate and Supported Surface

`workflow-audit` is a same-version workflow-maintenance audit only.

Before any audit step, it must:

1. Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
2. Run `trellis -v`
3. Compare the two versions for exact equality

If the versions differ in any way:

- stop immediately
- classify the stop as `Blocked / Version Drift`
- report both the compatible version and the actual version
- direct the user to `workflow-capability-audit`
- do **not** continue into target resolution, A/B/C evidence gathering, task creation, `/tmp` project creation, `trellis init`, or embed/post-install validation

Supported workflow audit surface is limited to:

- `Claude Code`
- `OpenCode`
- `Codex`

That support limit applies to:

- per-CLI adaptation conclusions
- temporary target-project artifact checks
- hidden-directory scope during install/post-install verification

Repo-local directories for other CLIs or carriers are out of scope for `workflow-audit` unless the workflow's own managed-surface contract explicitly adds them in the future.

Currently excluded repo-local CLI directories and the reason:

- `.kiro/` — not part of the workflow's managed surface; skill deployment there is handled independently by Trellis, not by the workflow-audit contract
- `.qoder/` — same as above

These exclusions are a design decision, not a coverage gap. Extending the supported surface to include additional platforms requires an explicit update to `workflow_assets.py`'s managed-surface contract first; `workflow-audit` will then incorporate the new platform in the same change.

Note on `.opencode/`, `.codex/`, and `.agents/skills/`: these paths participate in the three-platform managed surface, but not all in the same way. `.agents/skills/` has a dual role: in this source repository it is the shared deployment layer for compatible skill loaders, while in workflow-installed target projects it is also the shared workflow skill carrier visible to Codex and potentially OpenCode. Its presence alone is therefore not a defect. For Codex, `.codex/config.toml` and `.codex/hooks.json` are primary carrier/config surfaces, while `.codex/skills/` remains a conditional secondary carrier rather than the default baseline artifact set. Codex hook activation is also runtime-gated by user-level enablement or approval, so installed carrier shape and live runtime activation must be audited separately. The absence of skill files under `.opencode/skills/workflow-audit/` or `.codex/skills/workflow-audit/` is therefore expected and not a defect.

## Audit Coverage Requirements

This skill **must** fully validate the following aspects for any workflow under audit:

1. **Script-behavior consistency** - For every script referenced in workflow documentation (e.g., `detect-embed-state.py`, `install-workflow.py`, `upgrade-compat.py`), the audit must verify:
   - The script exists at the documented path
   - The script's actual behavior (via static analysis or runtime) matches documented claims
   - Exit codes and output format are machine-parseable if the workflow depends on them
   - Required environment-variable contracts are still honored. In particular, `install-workflow.py` must continue to refuse formal install unless `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` is set, because the Codex handoff boundary depends on it

2. **CLI adaptation completeness** - For each supported CLI (Claude Code, OpenCode, Codex), the audit must confirm:
   - All workflow commands/skills/agents are correctly mapped to the CLI's native location
   - No CLI-specific behavior drifts exist for the same semantic action
   - Missing or incomplete adaptations are flagged as `present-but-incompatible` or `missing-but-valuable`
   - Native-adaptation conclusions must combine:
     - the latest official CLI documentation available at audit time
     - repo-local validated evidence from this workflow authoring repository
     - actual development-use evidence: the real maintainer/operator path, runtime gating behavior, and which carriers are primary vs conditional in day-to-day use
   - The audit must not judge native adaptation from memory alone, or from carrier-file presence/absence alone

3. **Post-install artifact verification** - The audit must compare documented installation artifacts against actual files created in the target project, separating the clean `trellis init` baseline from the workflow-installed state after `install-workflow.py`, including:
   - Hidden directories (`.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`)
   - `.agents/skills/` must be interpreted with its dual role in mind: repo-local shared deployment layer in this source repo, shared workflow skill carrier in target projects
   - Command scripts, skill definitions, agent configurations
   - The audit must report discrepancies as confirmed issues with source-layer tags
   - Generated target-project files may only be attributed to the workflow after that baseline-vs-installed comparison

   Special interpretation rule:
   - install-only low-stakes reminder artifacts such as the workflow-created root `todo.txt` are **not** defects by default
   - if such an artifact is documented as “does not change stage gates / command routing / runtime closure,” the audit must not classify its existence alone as over-management, corruption, or drift without stronger contradictory evidence
   - such artifacts may still be mentioned as contextual outputs, but they are not mandatory managed-surface failures in the same class as hidden-directory carriers, command copies, helper scripts, or routing blocks

4. **Codex handoff boundary** - When Codex is the primary executor and the audit reaches the formal embed step, the skill must:
   - Stop and emit a handoff block using the dedicated template
   - Require handoff to Claude Code or OpenCode for the embed execution
   - Merge back evidence from the handoff into the audit report

5. **Runtime validation triggers** - The audit must automatically escalate to runtime validation (task-based runtime mode) when:
   - Any of the above checks cannot be conclusively resolved via static analysis
   - The workflow documentation or scripts contain conditional logic based on the environment
   - The user explicitly requests `/tmp` validation or Codex handoff testing

6. **Change-worthiness and negative-optimization guardrail** - The audit must separate real defects from non-defect differences:
   - Do not classify a path as change-worthy merely because another arrangement seems cleaner or more uniform
   - Do not recommend optimization when the current state is evidence-backed, intentionally scoped, and does not break behavior, closure, or maintainability
   - If the latest official docs, repo-local evidence, and actual development-use evidence all support the current state, record the item as a false alarm / non-defect rather than manufacturing a fix
   - When a candidate issue turns out to be non-defective, ignore it rather than turning it into a low-value optimization target

Each confirmed issue in the audit report must include, in addition to the schema defined in "Confirmed-Issue Schema", a validation action that describes how the issue was detected (e.g., "Compared script signature against documentation; exit code 0 but missing required JSON output").

---

## Trigger Conditions

Use `workflow-audit` when the user wants to:

- audit or verify the maintained workflow rooted at `docs/workflows/新项目开发工作流/`
- confirm whether workflow issues are real before changing source files
- validate workflow embed/install behavior against a `/tmp + trellis init` baseline
- verify CLI adaptation or Codex handoff boundaries

Do not use it for normal code review or ordinary product implementation tasks.
Do not use it to determine whether a newer or older Trellis version is compatible with the workflow; that is `workflow-capability-audit`.

---

## Input Contract

Natural language is allowed, but the recommended contract is:

- `workflow_path`
  - only supported value: `docs/workflows/新项目开发工作流/`
  - when omitted, resolve it to `docs/workflows/新项目开发工作流/`
  - natural-language requests such as "audit this workflow" or "check the workflow" must bind to the same fixed workflow root
  - must resolve to exactly one workflow root, and that root must be `docs/workflows/新项目开发工作流/`
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
  - if provided explicitly, it must be one of: `claude`, `opencode`, `codex`

The contract intentionally omits `preferred_handoff_cli`.

Default handoff order remains:

1. `Claude Code`
2. `OpenCode`

Natural-language user constraints may override this order.

If multiple workflow targets are supplied in one request, the skill must stop, explain that it supports only `docs/workflows/新项目开发工作流/`, and require the user to continue with that single supported root only.

If the resolved `workflow_path` is anything other than `docs/workflows/新项目开发工作流/`:

- stop immediately
- classify the stop as `Blocked / Invalid Input`
- explain that this skill audits only `docs/workflows/新项目开发工作流/`
- do not silently replace the requested target with the supported root

If the supported `docs/workflows/新项目开发工作流/` root does not exist on disk:

- stop immediately
- classify the stop as `Blocked / Invalid Input`
- explain that the supported workflow root is missing from the repository checkout
- do not continue until the repository state is repaired

---

## Evidence Mainline

A, B, C always execute in order, regardless of whether `candidate_issues` are supplied. `candidate_issues` serve as supplementary focus points referenced within each step — they do not change the mainline.

D (Runtime Validation) is conditional, determined by findings from A/B/C and input parameters.
E (Output Findings) always executes as the final report step.

### Step Naming Map

The workflow may refer to the same control flow with either evidence-step labels or numbered step labels. Treat the following names as equivalent:

- `Target Resolution and Binding` = `Step 1`
- `A. Understand Target System Mechanics` = `Step 2a`
- `B. Static Evidence Gathering` = `Step 2b`
- `C. Structured Gap Analysis` = `Step 2c`
- `D. Runtime Validation` = `Step 5`
- `E. Output Findings` = `Step 6`

`Step 3` and `Step 4` are orchestration stages between `C` and `D`/`E`:

- `Step 3` decides lightweight vs task-based execution mode
- `Step 4` creates task context and enters `trellis-brainstorm` when the task-based path is chosen

They do not replace or rename the evidence-mainline labels above.

Three execution modes determine which evidence steps run and how findings are delivered:

| Mode | Steps | Task | trellis-brainstorm | prd.md | audit-report.md |
|------|-------|------|------------|--------|-----------------|
| Lightweight static | A, B, C, E | N | N | N | N |
| Task-based static | A, B, C, E (D skipped) | Y | Y | Y | Y |
| Task-based runtime | A, B, C, D, E | Y | Y | Y | Y |

Mode selection is described in the Execution Modes section below.

Every piece of evidence collected throughout the mainline must be tagged with its source layer:

- `source repo` — files, documents, scripts within the workflow directory under `docs/workflows/`
- `generated target project` — files inside the `/tmp` target project, including the clean `trellis init` baseline and the workflow-installed state after `install-workflow.py`
- `runtime command output` — stdout/stderr/exit code from executed commands

This labeling is mandatory because the core audit operation (gap analysis) compares what the source repo declares against what the target project actually contains. Without source-layer tags, the two are easily conflated.

Within the `generated target project` layer, the audit must explicitly distinguish whether evidence came from the clean `trellis init` baseline or from the post-install workflow state. The comparison model is:

- `source repo`
- `generated target project` baseline (`trellis init`)
- `generated target project` workflow-installed state (`install-workflow.py`)
- `runtime command output`

Per-CLI adaptation conclusions follow this scope rule:

- the section is in scope when the audit examines CLI-specific carrier mapping, adaptation drift, CLI-specific installed artifacts, or the Codex handoff boundary
- lightweight output should still keep the section even when CLI adaptation is not in scope; in that case, mark each CLI entry as `not-applicable` with a brief reason instead of omitting the section
- if a CLI entry is `not-applicable`, a brief reason is sufficient; do not force the detailed evidence trio fields for that CLI
- when official docs, repo-local evidence, and practical development-use evidence disagree, record the disagreement explicitly instead of silently choosing one source as the winner

### Step 0: Version preflight

Before target resolution or evidence gathering:

- read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- run `trellis -v`
- compare for exact equality

If the versions differ:

- stop as `Blocked / Version Drift`
- report both values explicitly
- recommend `workflow-capability-audit`
- do not proceed to Step 1 or any later step

### Target Resolution and Binding

Before step A begins:

- resolve exactly one workflow target
- if `workflow_path` is omitted, or the user says "this workflow" / "the workflow" without naming another path, bind the target to `docs/workflows/新项目开发工作流/`
- if the resolved target is anything other than `docs/workflows/新项目开发工作流/`, stop as `Blocked / Invalid Input`
- do not treat the current repo root, active task directory, or temporary target-project root as the workflow target
- record the resolved workflow root explicitly in the output/report target section

### A. Understand Target System Mechanics

Before auditing the workflow, understand the system it operates within:

- fixed audit target root: `docs/workflows/新项目开发工作流/`
- current workflow authority for managed surfaces: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- current CLI boundary contract: `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- current hidden-directory / managed-boundary contract: `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- `.trellis/` is the runtime truth layer for workflow, task, and session state
- active-task resolution is session-scoped under `.trellis/.runtime/sessions/`, not a repo-global `.trellis/.current-task`
- hidden platform directories (`.claude/`, `.opencode/`, `.codex/`, `.agents/`) are carrier layers with platform-specific loading models, not equal authorities to `.trellis/`
- when CLI-native adaptation is in scope, the latest official docs for Claude Code / OpenCode / Codex are part of the authoritative mechanics set, not optional background reading
- trellis `init` baseline carrier set: `.trellis/`, `.claude/`, `.opencode/`, `.agents/skills/`, `.codex/`
- `.agents/skills/` 双角色：在当前 source repo 中是 shared deployment layer，在 workflow-installed target project 中是 shared workflow skill carrier；presence alone is not a defect
- OpenCode carrier model: plugin-driven context loading plus native command/agent carriers; adaptation checks must account for both halves
- Codex carrier model: `.codex/config.toml` / `.codex/hooks.json` are primary carrier/config surfaces; `.codex/skills/` is a conditional secondary carrier, not a default baseline artifact
- Codex hook execution is runtime-gated by local enablement or approval, so installed carrier shape and live activation are separate audit questions
- 各 CLI 的原生承载方式（commands / skills / agents / hooks 的目录约定）
- 各 CLI 在实际开发使用中的主路径、条件路径、运行时 gating，以及“目录存在”与“真实可用”之间的区别
- workflow 自身的 install / upgrade / uninstall 脚本实际行为
- 工作流嵌入执行规范中的状态机与前置条件
- current repo root, active task directory, and temporary target-project root are context inputs, not substitute audit targets
- generated target-project evidence is about the temporary target project created for the audit, not this source repository's own hidden directories
- generated target-project evidence must distinguish the clean `trellis init` baseline from the workflow-installed state after `install-workflow.py`

### B. Static Evidence Gathering

Read authoritative entry documents and indexes first, then trace references outward:

- bind default static reading scope to `docs/workflows/新项目开发工作流/` and files it references; do not treat the repo root as the primary audit target
- catalog every claim the workflow makes: steps, artifacts, boundaries, contracts
- note every referenced file path, script, template
- identify every cross-reference dependency
- cross-check referenced paths against actual filesystem
- for scripts that gate later workflow behavior, verify the documented exit-code and output-shape contract from static evidence first
- when per-CLI adaptation is being judged, fetch and compare the latest official docs for Claude Code / OpenCode / Codex against repo-local evidence before concluding compatibility
- capture practical-use evidence for each CLI when needed: which path maintainers actually rely on, which carrier is primary, which carrier is conditional, and which runtime gate decides live behavior
- practical development-use evidence should prefer inspectable artifacts when possible: the CLI boundary matrix, platform READMEs, live carrier/config files, runtime gate definitions, and if Step D runs, command transcripts or runtime observations

### C. Structured Gap Analysis

Compare document claims against actual definition completeness:

- 文档声明了某步骤 / 产物 / 边界，但对应定义文件缺失或不完整 → 确认为 gap
- 流程层面"有"但执行闭环层面"没做完"的内容 → 记录为 incomplete closure
- 跨文档引用的一致性：是否引用了不存在的文件、旧路径、或已过时的路径名
- 各 CLI 适配层之间是否存在行为漂移（同一语义在不同 CLI 下实现不一致）
- CLI 适配缺口必须归类为 `present-but-incompatible` 或 `missing-but-valuable`
- `.agents/skills/` presence alone is not a defect; only contradictory managed-surface behavior or misleading duplicate exposure counts as a workflow issue
- `.codex/skills/` 缺失默认不算 defect，除非当前 managed-surface contract 明确要求这个 secondary carrier
- 结合“最新官方文档 + repo-local 证据 + 实际开发使用视角”判断每个 CLI 的原生适配结论；禁止只凭记忆或静态目录存在性下结论
- 当三源证据冲突时：runtime observation 只决定“当前实际观察到的行为”；repo-local evidence 决定“当前 workflow 的声明/实现”；官方文档决定“当前上游文档契约”
- 若三源冲突仍不能证明真实缺陷，则保守落到 `Evidence Gap` / `Needs Clarification`，而不是直接生成 confirmed issue；若冲突更像上游 CLI capability drift，则提示转到 `workflow-capability-audit`
- 对“看起来可以更统一/更干净”的点，先判断是否真是缺陷；不是缺陷的就忽略，不得做负面优化
- 明确的人类/维护者意图可以作为解释差异为何存在的上下文，但意图本身不会自动把 non-defect 变成 defect；除非用户明确要求设计变更，否则不要把这类差异升级成 confirmed issue 或默认修复方向
- 隐藏目录托管边界：安装后产物是否与 trellis 基线 + workflow 声明的托管范围一致
- `generated target project` 证据必须区分 clean `trellis init` baseline 与 workflow-installed state；不得把 baseline 自带产物直接归因给 workflow
- 不得把 repo-local 的其他平台隐藏目录直接当作当前 workflow 缺失适配的证据；除非 `workflow_assets.py` 明确把它们纳入 managed surface

### D. Runtime Validation

Required when embed / install / post-install behavior must be verified:

- confirm the temporary target project's `.trellis/.version` matches the Step 0 actual `trellis -v` result; otherwise stop as `Blocked / Version Drift`
- 在 `/tmp` 创建纯净 Git 项目，满足安装前置条件后执行 `trellis init`
- 在 `trellis init` 完成后、执行 `install-workflow.py` 前，记录当前文件系统状态作为 clean baseline 快照；后续 post-install 比较与产物归因必须以该快照为基准
- 执行标准嵌入链: `detect-embed-state.py` → `install-workflow.py --dry-run` → `install-workflow.py` → `upgrade-compat.py --check`
- 检查安装后隐藏目录（`.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`）与 baseline 快照 + workflow 托管声明是否一致
- 比较文档声明的安装产物与实际落盘产物
- 如果 Step D 在 baseline 快照已捕获后失败，保留该 baseline 证据，并将后续 installed state 标记为 incomplete / unverified，禁止把未完成安装状态当作完整 workflow-installed 结论
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

**Judgment 1 — Taskify?** Should the audit create a task, enter trellis-brainstorm, and maintain `prd.md` + `audit-report.md`?

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
When Judgment 1 is "yes" but D is not needed: task-based static mode (create task, enter trellis-brainstorm, maintain `prd.md` and `audit-report.md`, then skip D and go to E).
When both judgments are "yes": task-based runtime mode (create task, enter trellis-brainstorm, maintain `prd.md` and `audit-report.md`, execute D, then output E).

### Lightweight static mode

- does not create a task
- does not create `prd.md`
- does not create `audit-report.md`
- outputs using the simplified chat structure from `references/lightweight-output-template.md`

### Task-based static mode

When the skill determines task context is warranted but runtime validation is not required:

- create audit task context (child task if another non-audit task is active, otherwise top-level)
- resolve active-task state from the current session-scoped Trellis runtime; do not assume a repo-global active-task marker
- enter the `trellis-brainstorm` mainline explicitly as the control container
- create and maintain `prd.md` through the `trellis-brainstorm` path
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

If `/tmp` project creation, `trellis init`, or any required runtime-validation command fails before step D completes:

- stop immediately
- classify the stop as `Blocked / Runtime Execution Failure`
- record the failing command, exit status, key stdout/stderr evidence, and what remains unverified

### Mode transition boundary

When transitioning from step C to a task-based mode:

1. explain the rationale for the chosen mode
2. if entering task-based static: explain why task context is warranted and why D is not needed
3. if entering task-based runtime: explain why runtime validation is necessary
4. proceed to create task context and enter trellis-brainstorm
5. seed `audit-report.md` with already-collected evidence from steps A/B/C

Never switch modes silently. Never discard A/B/C findings when entering a task-based mode.

If task-based mode is chosen but the required `trellis-brainstorm` entrypoint for the current CLI is unavailable:

- stop immediately
- classify the stop as `Blocked / Dependency Unavailable`
- preserve the already-collected A/B/C evidence
- do not silently fall back to lightweight mode

### User-set `need_runtime_validation: no` conflict

When the user explicitly set `need_runtime_validation: no` but step C findings conclusively demonstrate that runtime validation is necessary (D trigger conditions are met):

- do NOT silently skip D
- output a Needs Confirmation block using `references/needs-confirmation-template.md`
- let the user decide whether to override their original setting
- do not proceed to D without explicit user confirmation

---

## Task Model

All task references in this section are resolved from the current session-scoped Trellis runtime, not from a repo-global active-task file.

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
- when evidence is tagged as `generated target project`, record whether it came from the clean `trellis init` baseline or the workflow-installed state after `install-workflow.py`
- when per-CLI adaptation is judged, record for each CLI:
  - the official-doc source checked
  - the repo-local evidence checked
  - the practical development-use evidence checked
  - whether these sources agree or where they differ

### Confirmed-Issue Schema

Every confirmed issue must include:

- priority (`P0` / `P1` / `P2`)
- conclusion
- evidence source (with source layer tag: `source repo` / `generated target project` / `runtime command output`)
  - when the layer is `generated target project`, include `Stage` as `baseline after trellis init` or `workflow-installed state after install-workflow.py`
- validation action
- impact scope
- fix direction

The audit must not emit a confirmed issue or fix direction for a non-defect “optimization” idea unless evidence shows real behavioral, closure, or maintainability harm. Evidence-backed non-defects belong in `Unconfirmed Items / False Alarms`, not in `Confirmed Issues`.

#### Priority Rubric

Use the following rubric to assign `P0` / `P1` / `P2` consistently. When in doubt between two levels, pick the more severe one and explain the borderline case in the issue conclusion.

- `P0` — blocks workflow execution, install, or audit itself
  - the workflow cannot finish a documented step under any supported CLI
  - install / embed / upgrade scripts crash, exit with an undocumented non-zero status, or silently corrupt state
  - a security or boundary contract is broken (e.g., `install-workflow.py` no longer enforces `WORKFLOW_EMBED_EXECUTOR_CONFIRMED`, allowing Codex to lead formal embed)
  - documented post-install artifact is entirely missing
- `P1` — drift with real behavioral impact, but a workaround or partial path exists
  - documented behavior diverges from actual script behavior in a way an auditor or operator would notice (exit code shape, output schema, side-effect ordering)
  - one CLI's adaptation is materially incomplete or behaviorally inconsistent with the other CLIs for the same semantic action
  - cross-document references point at moved/renamed files but a manual workaround still works
- `P2` — surface-level inconsistency, no behavioral impact
  - wording, naming, or label drift between docs that does not change runtime behavior
  - non-breaking documentation gaps that do not mislead an auditor about behavior
  - cosmetic or formatting issues in templates that still render and parse correctly

A finding that requires runtime validation to confirm severity must stay in the Blocked / Evidence Gap section until D is run, rather than be guessed into a P-level.

### Blocked-State Rules

If some critical branches remain unresolved, partial confirmed conclusions are allowed only when blocked branches are explicitly labeled as:

- `Blocked`
- `Evidence Gap`
- `Needs Clarification`

Blind guessing is forbidden.

This partial-findings blocked-item set is distinct from hard-stop exit classifications such as:

- `Blocked / Version Drift`
- `Blocked / Invalid Input`
- `Blocked / Dependency Unavailable`
- `Blocked / Runtime Execution Failure`
- `Blocked / No Handoff Target`

Use `Blocked / <subtype>` when the audit itself cannot continue reliably and must stop. Do not treat those hard-stop classifications as ordinary partial blocked-item labels inside an otherwise continuing audit report.

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
  - formal install with explicit non-Codex executor confirmation, performed with `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` set in the environment of the takeover CLI's invocation
  - post-install `upgrade-compat.py --check`

The `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` environment variable is part of the boundary contract: `install-workflow.py` uses it to refuse formal install when the operator has not explicitly acknowledged the takeover, so the audit must not treat the formal install step as covered by handoff evidence unless the env var was actually set in the returned command transcript.

Any handoff CLI remains limited to runtime validation only during the audit stage and must not modify workflow source files.

Returned evidence from the handoff path must be merged back into the current audit report.

If the user constraints or runtime reality rule out all usable non-Codex executors for the formal embed step:

- stop immediately
- classify the stop as `Blocked / No Handoff Target`
- explain that the formal embed step remains unverified because no allowed takeover CLI is available

---

## Post-audit Routing

The audited workflow's own internal `design` / `plan` / `start` semantics are not a trusted control plane.

Post-audit routing must come only from the current-project trusted whitelist:

- `trellis-brainstorm`
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

Suggested fix directions and post-audit recommendations must obey the change-worthiness guardrail:

- do not propose “cleanup” or “optimization” work for evidence-backed non-defects
- do not recommend changes that would remove a currently valid primary/conditional carrier split merely to force cosmetic cross-CLI symmetry
- if the strongest evidence-backed conclusion is “current behavior is acceptable,” say so directly and stop

The skill must stop after presenting the report and routing guidance. It must not auto-execute the next phase.

---

## Validation

Required persisted scenario files:

- `tests/01-lightweight-static.md`
- `tests/02-nontrivial-full-audit.md`
- `tests/03-codex-handoff.md`
- `tests/04-task-based-static.md`
- `tests/05-need-runtime-validation-no-escalation.md`
- `tests/06-multi-target-input-stop.md`
- `tests/07-child-audit-task.md`
- `tests/08-post-audit-routing.md`
- `tests/09-grill-me-gap-clarification.md`
- `tests/10-opencode-priority-handoff.md`
- `tests/11-invalid-workflow-path.md`
- `tests/12-brainstorm-dependency-unavailable.md`
- `tests/13-runtime-execution-failure.md`
- `tests/14-no-handoff-target.md`
- `tests/15-source-layer-tag-compliance.md`
- `tests/16-candidate-issues-supplemental-focus.md`
- `tests/17-per-cli-not-applicable-section.md`
- `tests/18-confirmed-issue-minimum-schema.md`
- `tests/19-current-cli-inference-failure.md`
- `tests/20-script-behavior-mismatch.md`
- `tests/21-version-drift-stop.md`
- `tests/22-implicit-default-workflow-root.md`
- `tests/23-unsupported-explicit-workflow-root.md`
- `tests/24-active-task-not-audit-target.md`
- `tests/25-temp-project-not-workflow-source.md`
- `tests/26-ambiguous-natural-language-target.md`
- `tests/27-baseline-installed-no-diff.md`
- `tests/28-trellis-init-partial-baseline-failure.md`
- `tests/29-native-cli-doc-and-practical-evidence.md`
- `tests/30-non-defect-no-negative-optimization.md`
- `tests/31-todo-reminder-non-defect.md`

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
- expression form may differ by CLI: for example, `.agents/skills/` may reference `trellis-brainstorm` directly as a sibling skill, while `.claude/skills/` may also reference `trellis-brainstorm` as a skill via the Skill tool
- do not treat one skill surface as independently maintainable from the others for behavioral semantics
- do not land behavior, trigger, or contract changes in only one skill surface without evaluating the others

If the same behavior change also touches companion templates/tests, the same change must also update:

- affected files under `.agents/skills/workflow-audit/references/`
- affected files under `.agents/skills/workflow-audit/tests/`
- affected files under `.claude/skills/workflow-audit/references/`
- affected files under `.claude/skills/workflow-audit/tests/`

When a behavior change could affect the task-based audit path's dependence on `trellis-brainstorm`, review that dependency explicitly rather than assuming the coupling still holds.

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
- `.agents/skills/workflow-audit/tests/06-multi-target-input-stop.md`
- `.agents/skills/workflow-audit/tests/07-child-audit-task.md`
- `.agents/skills/workflow-audit/tests/08-post-audit-routing.md`
- `.agents/skills/workflow-audit/tests/09-grill-me-gap-clarification.md`
- `.agents/skills/workflow-audit/tests/10-opencode-priority-handoff.md`
- `.agents/skills/workflow-audit/tests/11-invalid-workflow-path.md`
- `.agents/skills/workflow-audit/tests/12-brainstorm-dependency-unavailable.md`
- `.agents/skills/workflow-audit/tests/13-runtime-execution-failure.md`
- `.agents/skills/workflow-audit/tests/14-no-handoff-target.md`
- `.agents/skills/workflow-audit/tests/15-source-layer-tag-compliance.md`
- `.agents/skills/workflow-audit/tests/16-candidate-issues-supplemental-focus.md`
- `.agents/skills/workflow-audit/tests/17-per-cli-not-applicable-section.md`
- `.agents/skills/workflow-audit/tests/18-confirmed-issue-minimum-schema.md`
- `.agents/skills/workflow-audit/tests/19-current-cli-inference-failure.md`
- `.agents/skills/workflow-audit/tests/20-script-behavior-mismatch.md`
- `.agents/skills/workflow-audit/tests/21-version-drift-stop.md`
- `.agents/skills/workflow-audit/tests/22-implicit-default-workflow-root.md`
- `.agents/skills/workflow-audit/tests/23-unsupported-explicit-workflow-root.md`
- `.agents/skills/workflow-audit/tests/24-active-task-not-audit-target.md`
- `.agents/skills/workflow-audit/tests/25-temp-project-not-workflow-source.md`
- `.agents/skills/workflow-audit/tests/26-ambiguous-natural-language-target.md`
- `.agents/skills/workflow-audit/tests/27-baseline-installed-no-diff.md`
- `.agents/skills/workflow-audit/tests/28-trellis-init-partial-baseline-failure.md`
- `.agents/skills/workflow-audit/tests/29-native-cli-doc-and-practical-evidence.md`
- `.agents/skills/workflow-audit/tests/30-non-defect-no-negative-optimization.md`
- `.agents/skills/workflow-audit/tests/31-todo-reminder-non-defect.md`
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
- `.claude/skills/workflow-audit/tests/06-multi-target-input-stop.md`
- `.claude/skills/workflow-audit/tests/07-child-audit-task.md`
- `.claude/skills/workflow-audit/tests/08-post-audit-routing.md`
- `.claude/skills/workflow-audit/tests/09-grill-me-gap-clarification.md`
- `.claude/skills/workflow-audit/tests/10-opencode-priority-handoff.md`
- `.claude/skills/workflow-audit/tests/11-invalid-workflow-path.md`
- `.claude/skills/workflow-audit/tests/12-brainstorm-dependency-unavailable.md`
- `.claude/skills/workflow-audit/tests/13-runtime-execution-failure.md`
- `.claude/skills/workflow-audit/tests/14-no-handoff-target.md`
- `.claude/skills/workflow-audit/tests/15-source-layer-tag-compliance.md`
- `.claude/skills/workflow-audit/tests/16-candidate-issues-supplemental-focus.md`
- `.claude/skills/workflow-audit/tests/17-per-cli-not-applicable-section.md`
- `.claude/skills/workflow-audit/tests/18-confirmed-issue-minimum-schema.md`
- `.claude/skills/workflow-audit/tests/19-current-cli-inference-failure.md`
- `.claude/skills/workflow-audit/tests/20-script-behavior-mismatch.md`
- `.claude/skills/workflow-audit/tests/21-version-drift-stop.md`
- `.claude/skills/workflow-audit/tests/22-implicit-default-workflow-root.md`
- `.claude/skills/workflow-audit/tests/23-unsupported-explicit-workflow-root.md`
- `.claude/skills/workflow-audit/tests/24-active-task-not-audit-target.md`
- `.claude/skills/workflow-audit/tests/25-temp-project-not-workflow-source.md`
- `.claude/skills/workflow-audit/tests/26-ambiguous-natural-language-target.md`
- `.claude/skills/workflow-audit/tests/27-baseline-installed-no-diff.md`
- `.claude/skills/workflow-audit/tests/28-trellis-init-partial-baseline-failure.md`
- `.claude/skills/workflow-audit/tests/29-native-cli-doc-and-practical-evidence.md`
- `.claude/skills/workflow-audit/tests/30-non-defect-no-negative-optimization.md`
- `.claude/skills/workflow-audit/tests/31-todo-reminder-non-defect.md`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `.agents/skills/workflow-capability-audit/SKILL.md`
- `.claude/skills/workflow-capability-audit/SKILL.md`
- `.agents/skills/trellis-brainstorm/SKILL.md`
- `.claude/skills/trellis-brainstorm/SKILL.md`

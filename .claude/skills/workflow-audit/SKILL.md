---
name: workflow-audit
description: Audit the repo-local workflow rooted at `docs/workflows/新项目开发工作流/`, including workflow source assets, embed/install flows, CLI-native adaptation, and post-install verification boundaries. Use this for same-version workflow maintenance, or for a user-approved patch-only stable mismatch in the current run; route other version drift to `workflow-capability-audit`. Do not use this for ordinary business code, application features, or generic implementation review.
---

# workflow-audit

`workflow-audit` is the maintainer-side audit entry point for workflows in this repository. It verifies whether workflow problems are real before any source edits, then produces evidence-based conclusions, repair directions, and controlled next-step recommendations.

If this file conflicts with `.trellis/spec/skills/workflow-audit.md`, treat the spec file as the behavioral source of truth.

## Purpose

Use this skill to:

- audit workflow source assets under `docs/workflows/新项目开发工作流/`
- audit workflow install / embed / post-install verification flows
- audit Claude Code / OpenCode / Codex carrier and adaptation boundaries
- verify whether candidate workflow issues are real rather than assuming they already are

`workflow-audit` is not a generic selector for arbitrary entries under `docs/workflows/`.
Its only supported workflow target is `docs/workflows/新项目开发工作流/`.

Do not use this skill to:

- review ordinary business code
- review application feature implementation quality
- review product requirements or PRD content
- perform generic code review unrelated to workflows
- analyze Trellis version compatibility or upgrade drift; route that to `workflow-capability-audit`

## Version Gate and Supported Surface

`workflow-audit` is a same-version maintenance audit only, with one narrow user-approved exception for a patch-only stable mismatch.

Before any audit step, it must:

1. Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
2. Run `trellis -v`
3. Classify the version relationship using the rules below

For this contract, a `minor version mismatch` means all of the following:

- same `major`
- same `minor`
- different `patch`
- neither version carries a prerelease label such as `-rc` or `-beta`

Examples:

- `0.5.0` vs `0.5.5` = contract-defined `minor version mismatch`
- `0.5.0-rc.1` vs `0.5.0` = not a `minor version mismatch`
- `0.5.0-beta.1` vs `0.5.0` = not a `minor version mismatch`
- `0.5.0-rc.1` vs `0.5.0-rc.3` = not a `minor version mismatch`

Despite the field name, this contract term does **not** mean semver minor-number drift such as `0.5.x` vs `0.6.x`. It refers only to a same-`major.minor` stable `patch` difference.

Equivalent natural-language instructions are allowed only when they unambiguously limit the bypass to that same-`major.minor` stable `patch` difference. If the wording is ambiguous, treat it as `allow_minor_version_mismatch: no`.

If the versions match exactly:

- continue normally

If the versions are a `minor version mismatch` and the user explicitly set `allow_minor_version_mismatch: yes` or gave an equivalent natural-language instruction:

- continue normally
- report both versions and the user-approved gate bypass explicitly
- treat the bypass as run-local only; do not reinterpret it as compatibility approval
- do not continue by rewriting `COMPATIBLE_TRELLIS_VERSION`

If the versions differ in any other way, or the `minor version mismatch` was not explicitly allowed:

- stop immediately as `Blocked / Version Drift`
- report both the compatible version and the actual version
- if the mismatch is the contract-defined `minor version mismatch`, also explain that the user may rerun with `allow_minor_version_mismatch: yes` for this audit run only
- otherwise tell the user to use `workflow-capability-audit`
- do not continue into target resolution, evidence gathering, task creation, `/tmp` project creation, or runtime validation

Supported audit surface is limited to:

- `Claude Code`
- `OpenCode`
- `Codex`

Other repo-local platform directories are out of scope unless the workflow's own managed-surface contract later adds them.

Currently excluded repo-local CLI directories and the reason:

- `.kiro/` — not part of the workflow's managed surface; skill deployment there is handled independently by Trellis, not by the workflow-audit contract
- `.qoder/` — same as above

These exclusions are a design decision, not a coverage gap. Extending the supported surface to include additional platforms requires an explicit update to `workflow_assets.py`'s managed-surface contract first; `workflow-audit` will then incorporate the new platform in the same change.

Note on `.opencode/`, `.codex/`, and `.agents/skills/`: these paths participate in the three-platform managed surface, but not all in the same way. `.agents/skills/` has a dual role: in this source repository it is the shared deployment layer for compatible skill loaders, while in workflow-installed target projects it is also the shared workflow skill carrier visible to Codex and potentially OpenCode. Its presence alone is therefore not a defect. For Codex, `.codex/config.toml` and `.codex/hooks.json` are primary carrier/config surfaces, while `.codex/skills/` remains a conditional secondary carrier rather than the default baseline artifact set. Codex hook activation is also runtime-gated by user-level enablement or approval, so installed carrier shape and live runtime activation must be audited separately. The absence of skill files under `.opencode/skills/workflow-audit/` or `.codex/skills/workflow-audit/` is therefore expected and not a defect.

## Audit Coverage Requirements

This skill must fully validate the following aspects for any workflow under audit:

1. **Script-behavior consistency**
   - verify every referenced script exists at the documented path
   - verify documented behavior matches the script's actual static or runtime behavior
   - verify exit codes and output formats are machine-parseable when later workflow steps depend on them
   - verify required environment-variable contracts are still honored; in particular, `install-workflow.py` must continue to refuse formal install unless `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` is set, because the Codex handoff boundary depends on it

2. **CLI adaptation completeness**
   - confirm workflow commands, skills, and agents are correctly mapped to each supported CLI's native carrier surface
   - detect behavior drift when the same semantic action differs across CLIs
   - classify missing or incomplete adaptations as `present-but-incompatible` or `missing-but-valuable`
   - combine the latest official CLI documentation available at audit time, repo-local validated evidence, and actual development-use evidence before concluding native compatibility
   - do not judge native adaptation from memory alone, or from carrier-file presence/absence alone

3. **Post-install artifact verification**
   - compare documented install artifacts against actual installed files, separating the clean `trellis init` baseline from the workflow-installed state after `install-workflow.py`
   - include hidden directories in scope: `.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`
   - `.agents/skills/` must be interpreted with its dual role in mind: repo-local shared deployment layer in this source repo, shared workflow skill carrier in target projects
   - report artifact mismatches as confirmed issues with source-layer-tagged evidence
   - generated target-project files may only be attributed to the workflow after that baseline-vs-installed comparison
   - install-only low-stakes reminder artifacts such as the workflow-created root `todo.txt` are not defects by default; if documented as non-gating reminders, they may be contextual outputs rather than managed-surface failures

4. **Codex handoff boundary**
   - stop and emit the dedicated handoff block when Codex reaches the formal embed step
   - require handoff to Claude Code or OpenCode for the formal embed execution
   - require returned handoff evidence to be merged back into `audit-report.md`

5. **Runtime validation triggers**
   - escalate to task-based runtime validation when any coverage requirement above cannot be resolved conclusively via static analysis
   - escalate when workflow docs or scripts contain environment-conditional behavior
   - escalate when the user explicitly requests `/tmp` validation or Codex handoff testing

6. **Change-worthiness and negative-optimization guardrail**
   - do not classify a path as change-worthy merely because another arrangement seems cleaner or more uniform
   - do not recommend optimization when the current state is evidence-backed, intentionally scoped, and does not break behavior, closure, or maintainability
   - if the latest official docs, repo-local evidence, and actual development-use evidence all support the current state, record the item as a false alarm / non-defect rather than manufacturing a fix
   - when a candidate issue turns out to be non-defective, ignore it rather than turning it into a low-value optimization target

Each confirmed issue must include a `validation action` describing exactly how the issue was detected.

## Trigger Conditions

This skill should trigger proactively when the user intends to:

- "audit this workflow"
- "confirm whether `docs/workflows/新项目开发工作流/` really has a problem before changing it"
- "check whether `docs/workflows/新项目开发工作流/` has defects"
- "validate the embed / install / post-install behavior of `docs/workflows/新项目开发工作流/`"
- "check whether Codex / Claude Code / OpenCode adaptation is correct"
- "validate the Codex handoff boundary and stop condition"
- "verify whether these workflow optimization points are real issues"
- "create a temporary project under `/tmp` to validate `docs/workflows/新项目开发工作流/`"

Do not use this skill when the real problem is whether the workflow remains compatible after Trellis changed versions.

## Input

Natural-language input is allowed, but prefer the recommended field contract. A short copyable template lives in `references/input-template.md`.

Key fields:

- `workflow_path`
  - only supported value: `docs/workflows/新项目开发工作流/`
  - when omitted, resolve it to `docs/workflows/新项目开发工作流/`
  - natural-language requests such as "audit this workflow" or "check the workflow" must bind to the same fixed workflow root
  - do not infer the target from repo root, current working directory, active task, or sibling workflow directories
- `candidate_issues`
  - default: empty, meaning the skill discovers issues proactively through the full evidence mainline
  - when supplied: supplementary focus points injected into each evidence step; the mainline still executes in full
  - always treated as hypotheses, never as confirmed defects
  - does not switch execution paths
- `need_runtime_validation`
  - default: `auto`
- `force_full_brainstorm`
  - default: `no`
- `allow_minor_version_mismatch`
  - default: `no`
  - `yes` allows Step 0 to continue only for the contract-defined `minor version mismatch` above
  - it never allows prerelease-related mismatches or broader version drift
  - despite the name, it does **not** mean semver minor-number drift
  - if the field form is not used and the wording is ambiguous about the patch-only stable scope, treat it as `no`
- `current_cli`
  - default: infer from the runtime environment first
  - ask the user only if a CLI-sensitive path is reached and the CLI still cannot be determined safely
  - if provided explicitly, it must be one of `claude`, `opencode`, `codex`

Constraints:

- exactly one `workflow_path` per run
- do not expose a dedicated `preferred_handoff_cli` field; default handoff order is `Claude Code -> OpenCode`
- if the resolved `workflow_path` is anything other than `docs/workflows/新项目开发工作流/`, stop as `Blocked / Invalid Input`, explain that this skill audits only that root, and do not silently replace the requested target
- if multiple workflow targets appear in the input, explain that this skill supports only `docs/workflows/新项目开发工作流/` and require the user to continue with that single supported root only
- if the supported `docs/workflows/新项目开发工作流/` root does not exist on disk, stop as `Blocked / Invalid Input`, explain that the supported workflow root is missing from the repository checkout, and do not continue until the repository state is repaired

## Output

Two output formats exist, serving three execution modes (see Workflow below for mode selection):

- Lightweight static mode: use the simplified chat structure from `references/lightweight-output-template.md`
- Task-based mode (static or runtime): incrementally maintain `audit-report.md` in the task, using `references/audit-report-template.md`

Both formats must:

- distinguish confirmed issues, unconfirmed items, false alarms, and blocked states
- conclude only from evidence
- stop with a controlled next-step recommendation
- record `Compatible Anchor Version`, `Current Trellis Version`, and `Version Gate` (`passed` or `bypassed`) in the audit boundary section
- when `Version Gate` is `bypassed`, also record `Bypass Detail` with the user-approved reason and the run-local-only disclaimer

Blind guessing is forbidden.

Every evidence item must retain one of these source-layer tags:

- `source repo`
- `generated target project`
- `runtime command output`

This is mandatory because gap analysis compares source-repo declarations against generated target-project state and runtime outputs. Conclusions without source-layer tags are invalid.

Within the `generated target project` layer, explicitly distinguish whether the evidence came from the clean `trellis init` baseline or from the post-install workflow state. The comparison model is:

- `source repo`
- `generated target project` baseline (`trellis init`)
- `generated target project` workflow-installed state (`install-workflow.py`)
- `runtime command output`

Per-CLI adaptation conclusions follow this scope rule:

- keep the section in scope when the audit examined carrier mapping, CLI drift, CLI-specific installed artifacts, or the Codex handoff boundary
- keep the section in lightweight output even when CLI adaptation is not in scope; mark each CLI entry as `not-applicable` with a brief reason instead of omitting the section
- when CLI adaptation is examined, include for each CLI the official-doc source checked, the repo-local evidence checked, the practical development-use evidence checked, and whether those sources agree or differ
- if a CLI entry is `not-applicable`, a brief reason is sufficient; do not force the detailed evidence trio fields for that CLI
- when official docs, repo-local evidence, and practical development-use evidence disagree, record the disagreement explicitly instead of silently choosing one source as the winner

Use blocked states in two distinct contexts:

- partial unresolved branches inside an otherwise continuing audit report: `Blocked`, `Evidence Gap`, `Needs Clarification`
- hard-stop exit classifications that terminate the audit: `Blocked / Version Drift`, `Blocked / Invalid Input`, `Blocked / Dependency Unavailable`, `Blocked / Runtime Execution Failure`, `Blocked / No Handoff Target`

Do not mix these two contexts.

Each confirmed issue must include at least:

- `priority`
- `conclusion`
- `evidence source` (tagged with source layer: `source repo` / `generated target project` / `runtime command output`)
- `validation action`
  - example granularity: `Compared script signature against documentation; exit code 0 but missing required JSON output`
- `impact scope`
- `fix direction`

The audit must not emit a confirmed issue or fix direction for a non-defect “optimization” idea unless evidence shows real behavioral, closure, or maintainability harm. Evidence-backed non-defects belong in `Unconfirmed Items / False Alarms`, not in `Confirmed Issues`.

Priority rubric (apply consistently; pick the more severe level when borderline):

- `P0` — blocks workflow execution, install, or audit itself
  - workflow cannot finish a documented step under any supported CLI
  - install / embed / upgrade scripts crash, exit with an undocumented non-zero status, or silently corrupt state
  - a security or boundary contract is broken (e.g., `install-workflow.py` no longer enforces `WORKFLOW_EMBED_EXECUTOR_CONFIRMED`, allowing Codex to lead formal embed)
  - documented post-install artifact is entirely missing
- `P1` — drift with real behavioral impact, but a workaround or partial path exists
  - documented behavior diverges from actual script behavior in a way an auditor or operator would notice (exit code shape, output schema, side-effect ordering)
  - one CLI's adaptation is materially incomplete or behaviorally inconsistent with the other CLIs for the same semantic action
  - cross-document references point at moved/renamed files but a manual workaround still works
- `P2` — surface-level inconsistency, no behavioral impact
  - wording, naming, or label drift that does not change runtime behavior
  - non-breaking documentation gaps that do not mislead an auditor about behavior
  - cosmetic or formatting issues in templates that still render and parse correctly

A finding that needs runtime validation to determine severity must stay in Blocked / Evidence Gap until D is run, rather than be guessed into a P-level.

## Workflow

### Step naming map

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

### Step 0: Version preflight

Before target resolution or evidence gathering:

- read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- run `trellis -v`
- classify the version relationship:
  - exact match -> continue
  - contract-defined `minor version mismatch` + explicit `allow_minor_version_mismatch: yes` (or equivalent, unambiguous natural-language instruction) -> continue and record the bypass explicitly
  - anything else -> stop as `Blocked / Version Drift`
- if the field form is not used and the wording is ambiguous about the patch-only stable scope, treat it as `allow_minor_version_mismatch: no`

If the audit stops for version drift:

- report both values explicitly
- if the mismatch is the contract-defined `minor version mismatch`, explain that the user may rerun with `allow_minor_version_mismatch: yes` for this run only
- otherwise recommend `workflow-capability-audit`
- do not proceed to Step 1 or any later step

### Step 1: Resolve target and parse input

1. Resolve exactly one workflow target.
2. If `workflow_path` is omitted, or the user says "this workflow" / "the workflow" without naming another path, bind the target to `docs/workflows/新项目开发工作流/`.
3. If the resolved target is anything other than `docs/workflows/新项目开发工作流/`, stop as `Blocked / Invalid Input`.
4. Do not treat the current repo root, active task directory, or temporary target-project root as the workflow target.
5. Parse input parameters: `candidate_issues`, `need_runtime_validation`, `force_full_brainstorm`, `current_cli`.
6. Record the resolved workflow root explicitly in the output/report target section.
7. Mode is NOT decided here — proceed to Step 2 regardless.

### Step 2: Execute evidence mainline A → B → C

The following three sub-steps always execute. If `candidate_issues` were supplied, reference them as supplementary focus points within each sub-step. The mainline is the same whether mode ends up lightweight static or task-based.

`grill-me` may be used as a clarification submode during gap analysis (step 2c) when key branches remain unresolved and continuing would require guessing. It is not a post-audit recommendation.

#### 2a. Understand target system mechanics

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
- 各 CLI 原生承载方式（commands / skills / agents / hooks 的目录约定）
- 各 CLI 在实际开发使用中的主路径、条件路径、运行时 gating，以及“目录存在”与“真实可用”之间的区别
- workflow 自身 install / upgrade / uninstall 脚本的实际行为
- 工作流嵌入执行规范中的状态机与前置条件
- current repo root, active task directory, and temporary target-project root are context inputs, not substitute audit targets
- generated target-project evidence is about the temporary target project created for the audit, not this source repository's own hidden directories
- generated target-project evidence must distinguish the clean `trellis init` baseline from the workflow-installed state after `install-workflow.py`

#### 2b. Static evidence gathering

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

#### 2c. Structured gap analysis

Compare document claims against actual definition completeness:

- 文档声明了某步骤 / 产物 / 边界，但对应定义文件缺失或不完整 → 确认为 gap
- 流程层面"有"但执行闭环"没做完"的内容 → 记录为 incomplete closure
- 跨文档引用一致性：是否引用了不存在的文件、旧路径、过时路径名
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

### Step 3: Judge execution mode

Based on input parameters and Step 2 findings, determine whether the audit runs in lightweight static or task-based mode.

**Task-based mode** (proceed to Step 4) when:
- `need_runtime_validation: yes`
- `need_runtime_validation: auto` AND Step 2 findings indicate:
  - any audit-coverage requirement remains inconclusive after static analysis
  - workflow scripts or docs contain environment-conditional behavior that can only be resolved at runtime
  - `/tmp` temporary-project validation is needed
  - embed / install / post-install behavior must be verified
  - Codex handoff may be triggered
- `force_full_brainstorm: yes` (enters task + trellis-brainstorm mainline; Step D is still judged separately in Step 4)

**Lightweight mode** (skip to Step 6) when:
- `need_runtime_validation: no`, UNLESS Step 2 findings conclusively prove runtime validation is necessary (see escalation rule below)
- `need_runtime_validation: auto` AND none of the Step D trigger conditions are met
- `force_full_brainstorm: no` (default) AND none of the above task-based conditions apply

**Escalation rule for `need_runtime_validation: no`**: If the user explicitly set `no` but Step 2 findings conclusively demonstrate that runtime validation is necessary, do NOT silently skip D. Instead, output a Needs Confirmation block using `references/needs-confirmation-template.md`, then let the user decide whether to proceed.

Lightweight mode: no task, no `prd.md`, no `audit-report.md`. Output using simplified template.
Task-based mode: proceed to Step 4 (task + trellis-brainstorm). Whether Step D executes is judged separately after task context is built.

### Mode transition boundary

When transitioning from Step 3 into any task-based mode:

- explain the rationale for the chosen mode before creating task context
- if entering task-based static, explain why task context is warranted and why Step D is not needed
- if entering task-based runtime, explain why runtime validation is necessary
- carry forward the Step 2 A/B/C evidence and seed `audit-report.md` with it
- never switch modes silently
- never discard A/B/C findings during the transition

If task-based mode is chosen but the required `trellis-brainstorm` entrypoint is unavailable:

- stop immediately
- classify the stop as `Blocked / Dependency Unavailable`
- preserve the already-collected A/B/C evidence
- do not silently fall back to lightweight mode

### Step 4: Build task context and enter trellis-brainstorm

Only in task-based mode (when proceeding beyond Step 3):

- resolve active-task state from the current session-scoped Trellis runtime; do not assume a repo-global active-task marker
- If a non-audit active task exists: create child audit task and switch into it immediately
- If no active task exists: create top-level audit task
- Default title: `workflow-audit: <workflow-name>`
- Enter the `trellis-brainstorm` mainline as the control container
- Maintain `prd.md` through the `trellis-brainstorm` path
- Initialize `audit-report.md`, seeding it with evidence already collected in Step 2

After task context is built, judge whether Step D (runtime validation) is needed:
- `need_runtime_validation: yes` → proceed to Step 5
- `need_runtime_validation: no` AND Step 2 findings conclusively require runtime validation → output Needs Confirmation (see escalation rule and `references/needs-confirmation-template.md`) and stop; do NOT proceed until user responds
- `need_runtime_validation: auto` AND Step 2 findings met D trigger conditions → proceed to Step 5
- Otherwise → skip to Step 6
- `force_full_brainstorm: yes` does NOT by itself trigger Step D; D still requires one of the conditions above

### Step 5: Runtime validation (evidence mainline step D)

Only in task-based runtime mode. Execute the validation:

- confirm the temporary target project's `.trellis/.version` matches the Step 0 actual `trellis -v` result; otherwise stop as `Blocked / Version Drift`
- this runtime check is independent from the Step 0 `COMPATIBLE_TRELLIS_VERSION` gate; it verifies that the temporary baseline project was initialized by the same current runtime version, even if Step 0 used an allowed bypass
- 在 `/tmp` 创建纯净 Git 项目，满足安装前置条件后执行 `trellis init`
- 在 `trellis init` 完成后、执行 `install-workflow.py` 前，记录当前文件系统状态作为 clean baseline 快照；后续 post-install 比较与产物归因必须以该快照为基准
- 执行标准嵌入链: `detect-embed-state.py` → `install-workflow.py --dry-run` → `install-workflow.py` → `upgrade-compat.py --check`
- 检查安装后隐藏目录（`.trellis/`, `.claude/`, `.opencode/`, `.agents/`, `.codex/`）与 baseline 快照 + workflow 托管声明是否一致
- 对比文档声明的产物与实际落盘产物
- 如果 Step D 在 baseline 快照已捕获后失败，保留该 baseline 证据，并将后续 installed state 标记为 incomplete / unverified，禁止把未完成安装状态当作完整 workflow-installed 结论

If `/tmp` project creation, `trellis init`, or any required runtime-validation command fails before Step D completes:

- stop immediately
- classify the stop as `Blocked / Runtime Execution Failure`
- record the failing command, exit status, key stdout/stderr evidence, and what remains unverified

#### Codex boundary

If this step reaches the formal temporary-project embed execution and the current main executor is Codex:

- stop the formal embed execution immediately
- emit a handoff block using `references/codex-handoff-template.md`
- default handoff order: `Claude Code -> OpenCode`
- if the user already established that Claude Code is unavailable or OpenCode is the only usable non-Codex CLI, override the default order and explain why
- require the handoff sequence to include: `detect-embed-state.py` → `install-workflow.py --dry-run` → formal install with non-Codex executor confirmation (`WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` set in the takeover CLI's invocation environment) → `upgrade-compat.py --check`

The `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` env var is part of the boundary contract: `install-workflow.py` refuses formal install when it is unset. The audit must not treat the formal install step as covered by handoff evidence unless the env var was actually set in the returned command transcript.

Constraints:

- takeover CLI: runtime validation only, no workflow source edits
- returned handoff evidence must be merged into `audit-report.md`
- if no usable non-Codex executor is available for the formal embed step, stop as `Blocked / No Handoff Target` and explain that the formal embed remains unverified

### Step 6: Report and stop (evidence mainline step E)

- Lightweight static mode: output using `references/lightweight-output-template.md`
- Task-based mode (static or runtime): update and present `audit-report.md`

After presenting the report, recommend the next step but do not execute it. Allowed recommendation targets:

- `trellis-brainstorm`
- `start`
- `check`
- `update-spec`
- if none fit, give a plain-language next action

Each recommendation must state:

- why it is recommended
- what trigger condition makes it the right choice now
- why stronger alternatives were not selected

Suggested fix directions and post-audit recommendations must obey the change-worthiness guardrail:

- do not propose “cleanup” or “optimization” work for evidence-backed non-defects
- do not recommend changes that would remove a currently valid primary/conditional carrier split merely to force cosmetic cross-CLI symmetry
- if the strongest evidence-backed conclusion is “current behavior is acceptable,” say so directly and stop

Stop and wait for user confirmation.

### Child Audit Task Completion (return-to-parent rules)

These rules apply only after Step 6 has produced an audit conclusion inside a child audit task — they govern when the child task may close and execution may return to the parent task. They are not Step 4 task-creation rules.

- do not return to parent merely because an audit report exists
- workflow-audit only advances the task to "audit conclusion produced, waiting for confirmation"
- once the user confirms the conclusion, remediation is handled by normal phases/skills inside the same child audit task
- return to parent only after remediation is complete and the human confirms

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
- `tests/32-allowed-minor-version-mismatch.md`
- `tests/33-prerelease-drift-ignores-bypass.md`
- `tests/34-wider-drift-ignores-bypass.md`

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
Enter the task-based runtime path, create an audit task, enter the `trellis-brainstorm` mainline as the control container, emit a Codex handoff block when required, and maintain `audit-report.md` inside the task.

### Example 3: Version drift stop

Input:
Audit `docs/workflows/新项目开发工作流/`, but the current local `trellis -v` no longer matches the workflow's declared compatible version and no explicit `allow_minor_version_mismatch: yes` bypass applies.

Output:
Stop immediately as `Blocked / Version Drift`, report both version values, and either point to `allow_minor_version_mismatch: yes` for a contract-defined `minor version mismatch` or tell the user to use `workflow-capability-audit` for all other drift. Do not create a task or continue the audit.

### Example 4: Explicitly allowed minor version mismatch

Input:
Audit `docs/workflows/新项目开发工作流/` for static rule-propagation issues only. The declared compatible version is `0.5.0`, the current `trellis -v` is `0.5.5`, and the user explicitly set `allow_minor_version_mismatch: yes`.

Output:
Continue the audit, record both version values and the user-approved gate bypass explicitly, and keep treating the run as a same-maintenance workflow audit rather than as compatibility approval.

# workflow-audit: 历史修复点满足性审计

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - `工作流历史修复点.txt` 中 25 条历史修复点是否在当前工作流 source contract 与嵌入结果中都得到满足
- Generated Target Project Root: `/tmp/trellis-workflow-audit-history-fixpoints`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Compared `docs/workflows/新项目开发工作流/commands/workflow_assets.py` `COMPATIBLE_TRELLIS_VERSION` with local `trellis -v` and confirmed exact equality `0.5.9` — Layer: `source repo`
- Read `.trellis/spec/skills/workflow-audit.md` and `.agents/skills/workflow-audit/SKILL.md` to confirm version gate, supported CLI surface, runtime escalation rule, and Codex handoff boundary — Layer: `source repo`
- Read `工作流历史修复点.txt` as the audit input baseline and extracted 25 historical items that must be mapped into current workflow contracts — Layer: `source repo`
- Read `工作流嵌入执行规范.md`, `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`, `工作流总纲.md`, and `阶段状态机与强门禁协议.md` to separate install contract, CLI carrier boundaries, hidden-directory checks, and stage/runtime semantics — Layer: `source repo`
- Located direct implementation evidence in `install-workflow.py`, `detect-embed-state.py`, `upgrade-compat.py`, `workflow-state.py`, `feasibility-check.py`, and `ownership-proof-validate.py` for bootstrap cleanup, remote checks, branch gate, README bilingual governance, legal-risk gate, source watermark, estimate requirement, phase confirmation, plan/task split, and native-agent routing — Layer: `source repo`
- Created `/tmp/trellis-workflow-audit-history-fixpoints`, initialized Git `main`, configured `origin` with 2 push URLs, and ran `trellis init --claude --opencode --codex -y -u xzc` successfully — Layer: `runtime command output`
- Recorded clean baseline hidden-directory state after `trellis init`; observed `.trellis/tasks/00-bootstrap-guidelines` present, `.agents/skills/trellis-*` baseline skills present, `.codex/skills/` directory present but empty, and all three `trellis-research / trellis-implement / trellis-check` agents provided by Trellis baseline — Layer: `generated target project` — Stage: `baseline after trellis init`
- Ran `detect-embed-state.py --project-root /tmp/trellis-workflow-audit-history-fixpoints --json` and confirmed `INITIAL_BASELINE_READY` with no traces or blockers — Layer: `runtime command output`
- Ran `install-workflow.py --project-root /tmp/trellis-workflow-audit-history-fixpoints --dry-run` and confirmed planned deployment of phase commands / shared skills / helper scripts / execution cards / workflow patch / NL routing / requirements pack import / bootstrap cleanup / post-install `upgrade-compat.py --check` — Layer: `runtime command output`
- Ran formal `install-workflow.py` without `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` and confirmed the Codex formal-install gate blocks execution before install begins — Layer: `runtime command output`

## Confirmed Issues

### [P1] “Brainstorm 完成后立即生成两份完全可用项目级需求文档” 与当前强门禁文档合同不一致
- Conclusion: 历史点 4 与当前合同不完全一致；当前 workflow 只要求 `customer-facing-prd.md` 在进入 design 前存在，而 `developer-facing-prd.md` 必须在技术架构确认后才正式生成。
- Evidence Source:
  - Layer: `source repo`
  - `工作流历史修复点.txt:10`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:454`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:469`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:1299`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md:174`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md:186`
- Validation Action:
  - Compared the historical requirement against the current design-stage document contract and stage-state validation rules.
- Impact Scope:
  - Brainstorm/design handoff semantics, PRD generation timing, target-project documentation expectations
- Suggested Fix Direction:
  - Either revise the historical fixpoint interpretation to align with the newer strong-gate model, or explicitly restore a brainstorm-stage requirement for both documents if that is still intended.

### [P1] “Brainstorm 结束后强制补充 sonar-scanner” 未被当前合同作为固定命令要求落地
- Conclusion: 历史点 6 只被当前 workflow 以“项目必须定义真实自动化检查矩阵；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因”收敛，未再保留“所有项目都补充 sonar-scanner”这一固定要求。
- Evidence Source:
  - Layer: `source repo`
  - `工作流历史修复点.txt:14`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:1620`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:1624`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:1647`
- Validation Action:
  - Searched the authoritative workflow documents and finish-work baseline for `sonar` / `sonar-scanner` and compared that to the generalized automation-matrix contract.
- Impact Scope:
  - Design-phase spec alignment, finish-work baseline adaptation, quality gate expectations in target projects
- Suggested Fix Direction:
  - If Sonar is still mandatory across all target projects, encode that as a fixed rule in the automation-matrix contract; otherwise mark the historical point as superseded by the project-specific matrix model.

### [P1→Resolved] “目标项目中的 `trellis-research` 需要与当前项目的加强版 `trellis-research` 保持同等级能力”
- Conclusion: 第 21 点原本是有效缺口；现已通过 source-level remediation 修复，并在新的真实目标项目 `/tmp/trellis-0.5.9-2` 上验证通过。
- Evidence Source:
  - Layer: `source repo`
  - `工作流历史修复点.txt:45`
  - `.claude/agents/trellis-research.md:5`
  - `.claude/agents/trellis-research.md:21`
  - `.claude/agents/trellis-research.md:48`
  - `.trellis/spec/agents/index.md:247`
  - `.trellis/spec/agents/index.md:256`
  - `.trellis/spec/agents/index.md:331`
  - `.trellis/spec/agents/index.md:358`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:28`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:41`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:45`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.9-2/.claude/agents/trellis-research.md:5`
  - `/tmp/trellis-0.5.9-2/.opencode/agents/trellis-research.md:1`
  - `/tmp/trellis-0.5.9-2/.codex/agents/trellis-research.toml:1`
  - `/tmp/trellis-0.5.9-2/.trellis/workflow-installed.json:48`
- Validation Action:
  - Compared the current source-repo live deployment agent body against the installed target-project agent files under `/tmp/trellis-0.5.9-2`; `diff -u` for Claude / OpenCode / Codex research agents returned no differences.
  - Ran `detect-embed-state.py --project-root /tmp/trellis-0.5.9-2 --json` and confirmed `ALREADY_VALID_EMBEDDED`.
  - Ran `upgrade-compat.py --check --project-root /tmp/trellis-0.5.9-2` and confirmed `总冲突: 0`.
- Impact Scope:
  - Workflow installer contract, target-project agent capability parity, upgrade/uninstall behavior, and historical fixpoint interpretation
- Suggested Fix Direction:
  - Resolved by changing the workflow contract so target projects receive an equivalently enhanced `trellis-research` surface instead of the Trellis baseline body.

## Unconfirmed Items / False Alarms
- “只靠 source repo 文档静态阅读即可判断嵌入后满足全部历史点” -> false alarm
- “`.current-task` 仍是当前 active task 真源” -> false alarm
  - `工作流历史修复点.txt` 自带注记已说明当前主机制改为 session-scoped runtime
- “workflow 仍应无条件向目标项目 overlay 全套 `trellis-research` / `trellis-implement` / `trellis-check` agents” -> false alarm
  - 当前合同明确依赖 Trellis 原生 agents，只做 legacy bare-name 迁移；第 21 点暴露的是 `trellis-research` 能力对齐缺口，不等于全量 overlay 三个 native agents 的要求
- “finish-work 仍硬编码 `pnpm` 校验” -> false alarm
  - searched current `trellis-finish-work` / platform finish-work surfaces and found no `pnpm` hard-coded requirement
- “新建仓库嵌入后 `.current-task` 应为空” -> false alarm as a direct fresh-baseline install requirement
  - clean `trellis init` baseline in `/tmp` had no `.trellis/.current-task`; current contract only promises cleanup when `.current-task` still points at `00-bootstrap-guidelines` during install

## Post-Install Evidence (OpenCode Handoff — 2026-05-09)

- Executor: OpenCode
- `detect-embed-state.py` (pre-install): `INITIAL_BASELINE_READY`, 0 blockers, 0 traces
- `install-workflow.py --dry-run`: Claude 9 commands + 2 patches, OpenCode 9 commands + 2 patches, Codex 9 skills + 3 patches, 7 helper scripts, 2 execution cards
- `install-workflow.py` (formal, `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1`): all deployments succeeded, no errors
- `upgrade-compat.py --check`: version 0.5.9 consistent, 18 checks all ✅, 0 conflicts
- `detect-embed-state.py` (post-install): `ALREADY_VALID_EMBEDDED`, 0 blockers
- Anomalies / failures: **none**
- Post-install hidden-directory verification:
  - `.claude/commands/trellis/`: 9 phase commands + finish-work patch + Phase Router in continue.md ✅
  - `.opencode/commands/trellis/`: 9 phase commands + finish-work patch + Phase Router in continue.md ✅
  - `.agents/skills/`: 9 workflow skills + trellis-continue patch + trellis-finish-work patch ✅
  - `.codex/hooks.json` + `session-start.py`: present ✅
  - `.trellis/scripts/workflow/`: 7 helper scripts, content consistent ✅
  - `.trellis/workflow-docs/`: 2 execution cards ✅
  - `.trellis/workflow.md`: project-local patch injected ✅
  - `AGENTS.md`: NL routing table injected ✅
  - `workflow-installed.json`: schema complete (Trellis 0.5.9, CLI: claude, opencode, codex) ✅
  - Spec baseline imported: `pack.requirements-discovery-foundation` ✅
  - Bootstrap cleanup: `00-bootstrap-guidelines` deleted ✅

## Blocked Items (Resolved)
- ~~25 条历史修复点的最终满足性结论~~ → **Resolved**: post-install evidence now available
- ~~formal install 与 post-install hidden-directory verification~~ → **Resolved**: OpenCode completed formal install and all post-install checks

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model: `.claude/commands/trellis/*.md` + shared helper scripts + workflow patch + AGENTS routing, while `trellis-*` agents stay Trellis-native
- Does the current implementation match: **yes** — post-install confirms 9 commands, finish-work patch, Phase Router, helper scripts, NL routing all deployed correctly
- If not, what is wrong: n/a

### OpenCode
- Expected carrier model: `.opencode/commands/trellis/*.md` is the formal phase-entry surface; `.agents/skills/` may still be scanned as shared carrier but should not replace the command boundary
- Does the current implementation match: **yes** — post-install confirms 9 commands, finish-work patch, Phase Router deployed; command boundary distinct from `.agents/skills/`
- If not, what is wrong: n/a

### Codex
- Expected carrier model: `.agents/skills/*/SKILL.md` is the shared workflow skills carrier; `.codex/config.toml` and hooks remain project-owned; `trellis-*` agents stay Trellis-native
- Does the current implementation match: **yes** — post-install confirms 9 skills, trellis-continue patch, trellis-finish-work patch, hooks.json, session-start.py all present
- If not, what is wrong: n/a

## Suggested Fix Directions
- Post-install evidence collected; no deployment defects found
- Two confirmed P1 issues remain as contract-level decisions:
  1. PRD timing: brainstorm 只要求 `customer-facing-prd.md`，不要求同时生成 `developer-facing-prd.md`
  2. sonar-scanner: 已收敛为项目自定义自动化检查矩阵，不再保留固定 sonar-scanner 要求
- If these remaining historical fixpoints are still intended as mandatory, source-level contract changes are needed; otherwise mark as superseded

## Follow-up Remediation (2026-05-09)

- Confirmed and fixed a route-level gap where `continue` reentry relied too heavily on `workflow-state.json` stage/status and did not front-load several readiness gates already described elsewhere in the workflow contract.
- Implemented route-time blockers in `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` for:
  - missing / non-allowing `assessment.md` when reentering `brainstorm`
  - missing leaf-task `prd.md` / task explanation card minimum when reentering `plan` or execution stages
  - unfinished `meta.depends_on` task dependencies before execution-stage reentry
  - missing `README.en.md` reminder when `plan` reenters after `design/` has already landed but design block-C English doc output is still absent
- Verification:
  - `test_cmd_route_blocks_brainstorm_without_assessment_even_when_customer_prd_missing` ✅
  - `test_cmd_route_blocks_plan_when_recommended_task_prd_missing` ✅
  - `test_cmd_route_blocks_execution_when_task_json_declares_unfinished_dependencies` ✅
  - `test_cmd_route_plan_prompts_english_readme_requirement_when_design_docs_missing` ✅
  - existing route/validate regression subset still passing ✅

## Propagation Scope and Synchronized Update Range
- Potentially affected layers if defects are later confirmed:
  - `docs/workflows/新项目开发工作流/*.md`
  - `docs/workflows/新项目开发工作流/commands/*.py`
  - `.trellis/spec/skills/workflow-audit.md`
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  - workflow-audit tests and references
- Propagation risk notes:
  - If any historical fixpoint is found to drift, docs, scripts, checks, and audit skill wording must be updated atomically

## Recommended Next Step
- Recommended action: finalize the 25-item satisfaction matrix and decide disposition for the 3 confirmed P1 items
- Trigger condition: post-install evidence is now complete
- Recommendation reason: all 4 evidence layers (baseline, dry-run, formal install, post-install) are collected; no deployment defects found; remaining questions are contract-level decisions
- Stronger alternatives not selected: source-file remediation deferred until P1 dispositions are decided

## Stop Point and Pending Confirmations
- Auto-continue allowed: Yes (evidence collection complete)
- User confirmation required for:
  - whether to mark the 2 confirmed P1 items as "superseded by contract" or "needs source fix"
  - whether to finalize and archive this audit task

## Codex Handoff (Completed)

### Why execution stops here
- The audit has reached the formal temporary-project embed step
- By workflow contract, Codex must not lead the first formal embed execution

### Default takeover order
1. Claude Code
2. OpenCode

### Execution context for the takeover CLI
- Run all commands below from the workflow source repo's working directory, not from inside `/tmp/trellis-workflow-audit-history-fixpoints`
- Workflow Root Dir: `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流`
- Temporary Target Project Root: `/tmp/trellis-workflow-audit-history-fixpoints`

### Handoff result
- Taken over by: **OpenCode** (2025-05-09)
- All 4 commands executed successfully
- All evidence collected (see Post-Install Evidence section above)
- Handoff closed — no further CLI handoff needed

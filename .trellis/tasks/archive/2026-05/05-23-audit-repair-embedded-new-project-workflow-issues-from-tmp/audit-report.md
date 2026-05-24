# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - 阶段状态机与路由层问题（1-4）
  - 命令文档与脚本契约不一致（5-7）
  - 执行卡与阶段命令集成缺口（8-9）
  - CLI 原生适配边界问题（10-11）
  - 文档一致性与可维护性问题（12-13）
  - 残留旧版本兼容性问题（14-15）
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model:
  - `source repo`
  - `generated target project` baseline (`trellis init`) if reconstructed in this run
  - `generated target project` workflow-installed state (`install-workflow.py`)
  - `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and extracted the compatible-version gate and managed-surface contract. — Layer: `source repo`
- Ran `trellis -v` and verified the current runtime is `0.5.17`. — Layer: `runtime command output`
- Read `.trellis/workflow.md`, `.trellis/spec/docs/index.md`, `.trellis/spec/guides/index.md`, and `.trellis/spec/skills/workflow-audit.md` to bind repo-local maintenance rules and audit mode. — Layer: `source repo`
- Ran semantic retrieval for `workflow-state.py`, stage commands, install records, execution cards, and CLI patch files to locate authoritative workflow assets before targeted reads. — Layer: `source repo`
- Read `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json`, `.trellis/workflow.md`, installed `trellis-{start,continue,finish-work}` skills, and OpenCode plugin carriers to compare installed target-project state with source expectations. — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Ran `workflow-state.py route --project-root /tmp/trellis-0.5.17-2` and confirmed the installed outsourcing-profile fixture routes first-entry to `feasibility`, not to personal `brainstorm`. — Layer: `runtime command output`
- Created synthetic Codex drift fixture under `/tmp/workflow-codex-drift-*` with patch markers present but hidden stale `planning / in progress` routing text in `trellis-continue`; `workflow-state.py route --project-root <fixture>` still returned `entry_choice_required`, not `embed_invalid`. — Layer: `runtime command output`
- Created synthetic OpenCode drift fixture under `/tmp/workflow-opencode-drift3-*` with marker-only `inject-subagent-context.js`; `workflow-state.py route --project-root <fixture>` still returned `entry_choice_required`, not `embed_invalid`. — Layer: `runtime command output`
- Checked official CLI docs for Codex instruction/config surfaces and OpenCode command/skill discovery before classifying CLI adaptation defects. — Layer: `runtime command output`

## Confirmed Issues

### [P1] `check -> delivery` 未重新核验 `review-gate` 硬条件
- Conclusion: 当前 `workflow-state.py` 在 `check -> delivery` 转换时只校验 `check.md` 结构与验证结论，没有把 `review-gate` 的 `required` 硬条件重新判定一次，确实存在高风险任务被直接放行到 `delivery` 的缺口。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/review-gate.md:64-138`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:506-537`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:753-771`
- Validation Action:
  - Cross-compared the documented `review-gate` hard-condition contract with the actual transition validator used for `check -> delivery`.
  - Verified that the transition path only calls `validate_check_gate()` and never derives or checks a `review_gate_decision`.
- Impact Scope:
  - Stage routing for `check -> delivery`
  - Any task whose risk profile should have forced `review-gate`
- Suggested Fix Direction:
  - Introduce a structured `review-gate` decision artifact or checkpoint produced by `check`, and make `workflow-state.py` require an explicit `skip`-class result before allowing `check -> delivery`.

### [P1] Codex patched skill 漂移检测过松，能放过 marker 存在但语义已回退的 `trellis-continue`
- Conclusion: 当前 Codex patched skill 检测只做少量 `must_contain` / `must_not_contain` 片段匹配；只要保留 patch marker，但混入不同措辞的旧 status 路由，`workflow-state.py route` 仍会放行。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:144-170`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:2018-2055`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py:2539-2777`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - Synthetic fixture run on `/tmp/workflow-codex-drift-*` returned `{"action":"entry_choice_required"}` instead of `embed_invalid` even though the skill still contained hidden stale `planning / in progress` routing semantics.
- Validation Action:
  - Read the current validator logic to see what fragments it actually enforces.
  - Built a temporary target-project fixture with all required markers plus a semantically stale `trellis-continue`, then ran `workflow-state.py route`.
- Impact Scope:
  - Codex installed target projects
  - Drift detection for `trellis-continue` and likely related entry skills
- Suggested Fix Direction:
  - Strengthen skill validation from marker-level checks to contract-level checks, at least detecting status-routing branches and required routing-table sections for `trellis-continue` / `trellis-start`.

### [P1] OpenCode `inject-subagent-context` 运行时补丁只验 marker，不验强门禁语义
- Conclusion: `workflow-state.py` 会把 OpenCode 的 `inject-subagent-context.js` 当作 critical runtime patch，但当前检查只看文件存在与 marker；即使 route gating 逻辑完全缺失，只要 marker 在，路由也会放行。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1788-1790`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1912-1927`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1989-2015`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - Synthetic fixture run on `/tmp/workflow-opencode-drift3-*` returned `{"action":"entry_choice_required"}` instead of `embed_invalid` even though `inject-subagent-context.js` only kept the patch marker and no route guard functions.
- Validation Action:
  - Compared the patch script's intended runtime semantics with the actual critical-patch checker.
  - Built a temporary target-project fixture with marker-only OpenCode subagent plugin and ran `workflow-state.py route`.
- Impact Scope:
  - OpenCode installed target projects
  - Runtime safety of subagent context injection under strong-gate routing
- Suggested Fix Direction:
  - Add OpenCode-specific semantic checks for `inject-subagent-context.js`, at least verifying route loader and stage-permission guard functions are present when the patch is declared installed.

### [P1] `check.md` 的下一步推荐表仍把默认收尾写成 `finish-work`，与主状态机链路冲突
- Conclusion: 当前 `check.md` 仍把“基本合规”默认推荐到 `finish-work`，而安装后的权威工作流主链是 `check -> delivery -> native finish-work`；这会误导用户或 AI 跳过 `delivery`。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/check.md:197-219`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md:239-246`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md:239-246`
- Validation Action:
  - Compared `check.md` next-step table with the installed target project's authoritative `.trellis/workflow.md` close-out order.
- Impact Scope:
  - `check` stage guidance across Claude/OpenCode/Codex
  - Risk of skipping `delivery` artifacts and acceptance closure
- Suggested Fix Direction:
  - Change the `check.md` default next-step recommendations to `delivery`, and move `native finish-work` to the post-delivery explanation only.

### [P2] `brainstorm -> implementation` 的 `L0` 直达门禁已在脚本里实现，但阶段转换表没有把它写明
- Conclusion: 当前 source workflow 的转换表只展示了 `--execution-authorized true`，没有明确说明 `brainstorm` 直达 `implementation` 还要求 `complexity_decision = L0`；脚本和命令文档存在可误读的不对齐。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md:345-352`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md:135-143`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1438-1450`
- Validation Action:
  - Compared the stage-transition quick reference against the actual `validate_brainstorm_exit_gate()` logic.
- Impact Scope:
  - Maintainer/operator understanding of `brainstorm -> implementation` gate
  - Downstream docs derived from the transition table
- Suggested Fix Direction:
  - Make the transition table explicitly say that direct entry to `implementation` is limited to `L0`, with the validator enforcing it from `prd.md`.

### [P2] 源码水印保持门禁写在 design/README 里，但公共 implementation 入口没有把它前置出来
- Conclusion: 设计文档和 Codex 平台 README 都要求“后续实现/修复触碰受保护片段前先跑 `source-watermark-guard.py`”，但真正的 implementation 公共入口说明只要求 `before-dev`，没有把该 guard 作为进入实现前的必检步骤显式前置。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/design.md:429-433`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md:144-149`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md:66-86`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md:380-385`
- Validation Action:
  - Compared the ownership-proof execution contract with the actual implementation-entry guidance used by the phase router.
- Impact Scope:
  - Implementation re-entry guidance across CLIs
  - Tasks with `Protected Watermark Snippets`
- Suggested Fix Direction:
  - Add an implementation-entry precheck that explicitly runs `source-watermark-guard.py --mode check` when ownership proof is enabled and protected snippets exist.

### [P2] `brainstorm` 阶段出口快照的 5 个字段只验“字段名存在”，不验是否填写了有效结论
- Conclusion: 当前 validator 只检查 `ui_lane_decision / cross_platform_scope / estimate_refresh_result / kill_criteria / open_items` 这些字段是否出现，没有检查是否仍是占位符或空洞值；这和文档里“至少写清”的要求不一致。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md:345-352`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py:1438-1450`
- Validation Action:
  - Compared the documented exit-snapshot requirement with the actual validator implementation for brainstorm exit.
- Impact Scope:
  - `brainstorm` exit readiness
  - Later manual review quality for scope/estimate/open-items context
- Suggested Fix Direction:
  - Promote these snapshot fields from marker-only presence checks to placeholder-aware validation, similar to `context7-review.md` field validation.

## Unconfirmed Items / False Alarms

- 候选 1（personal `no_task -> brainstorm` assessment 基线缺失） -> `false alarm`
  - `workflow-patch-projectization.md:136` 已写明“离开 brainstorm 前必须补齐 assessment 最低基线”。
  - `workflow-state.py route --project-root /tmp/trellis-0.5.17-2` 对 outsourcing fixture 正常返回 `entry_choice_required -> feasibility`，没有误走 personal 首入口。
- 候选 4（`project-audit` 正式/预审边界完全缺失） -> `false alarm`
  - `project-audit.md:45-83, 242-249` 已区分正式模式/预审模式、回流路径和 `PROJECT-AUDIT` 是否可标记完成。
  - 当前缺的是更强结构化留痕，不是“模式边界不存在”。
- 候选 5（brainstorm 项目级粗估门禁完全未被脚本覆盖） -> `false alarm`
  - `workflow-state.py:733-744` 与 `validate_project_doc_boundary()` 会在从 brainstorm 进入 design/plan/implementation 时检查 task-local 项目级粗估。
- 候选 6（Context7 复核门禁无脚本支持） -> `false alarm`
  - `workflow-state.py:1465-1518` 已对 `design/context7-review.md` 和 `checkpoints.context7_review_completed` 做硬校验。
- 候选 7（`finish-work` 项目化适配完全没有产物落点） -> `false alarm`
  - `工作流总纲.md:1284-1289` 已把任务 4/5 的最小产物落点写到 `finish-work-checklist.md` 与 close-out 基线说明中。
- 候选 14（installed `trellis-continue` 仍保留旧 status 路由） -> `false alarm`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-continue/SKILL.md` 已被 phase-router patch 替换。
  - 当前 repo 根 `.agents/skills/trellis-continue/SKILL.md` 的旧内容属于作者仓库自用 Trellis skill，不是本次目标工作流的 installed target-project surface。
- 候选 15（`task.json.status` 双轨真相未解决） -> `false alarm`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md:76` 与 `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` 已明确 `task.json.status` 仅为 bookkeeping，`workflow-state.py route` 才是强门禁真相源。

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

- 冻结后需求变更执行卡是否应有自动前置检测
  - Type: `Evidence Gap`
  - Cause: 当前 workflow 没有稳定的机器可读“新需求/变更请求”信号源；仅凭代码或文档静态状态无法可靠判断一次会话中的新增/修改/删除需求是否已经发生。
  - Impact: 候选 8 目前更像人工流程约束未自动化，而不是可直接证明的脚本 defect。
  - What is needed to continue: 如果要把它升级为强门禁，需要先定义标准化变更记录产物或 checkpoint，再决定是否接入 `workflow-state.py`。

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable for this round's defect set
- Repo-local evidence checked: `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`
- Practical development-use evidence checked: installed target-project `.claude` artifacts were not the focus of the confirmed defects above
- Agreement / discrepancy: no confirmed Claude-specific carrier defect in this round
- Expected carrier model: command + hook carrier
- Does the current implementation match: not fully re-audited in this round
- If not, what is wrong: none confirmed here

### OpenCode
- Official docs checked: `https://opencode.ai/docs/skills/`, `https://opencode.ai/docs/commands/`
- Repo-local evidence checked: `commands/opencode/README.md`, `CLI原生适配边界矩阵.md`, `patch-opencode-inject-subagent-context.py`, `workflow-state.py`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.opencode/commands/trellis/*`, `.opencode/plugins/*`
- Agreement / discrepancy: official docs support `.opencode/commands/` as formal command carrier and `.agents/skills/` as discoverable shared carrier; the confirmed defect is in patch validation strength, not in carrier-model selection
- Expected carrier model: `.opencode/commands/trellis/*.md` formal entry + plugin carriers + discoverable `.agents/skills/*`
- Does the current implementation match: mostly yes
- If not, what is wrong: `inject-subagent-context.js` semantic validation is too weak when the patch is declared installed

### Codex
- Official docs checked: `https://developers.openai.com/codex/guides/agents-md`, `https://developers.openai.com/codex/concepts/customization`, `https://developers.openai.com/codex/config-reference`
- Repo-local evidence checked: `commands/codex/README.md`, `CLI原生适配边界矩阵.md`, `workflow-state.py`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.agents/skills/*`, `.codex/hooks/*`, installed `trellis-{start,continue,finish-work}` skills
- Agreement / discrepancy: official docs support `AGENTS.md`, project `.codex/config.toml`, and shared `.agents/skills` usage; the confirmed defect is not the carrier split itself, but the looseness of drift validation for patched Codex skills
- Expected carrier model: `AGENTS.md` + `.codex/config.toml` / hooks + shared `.agents/skills`
- Does the current implementation match: mostly yes
- If not, what is wrong: marker-level validation can miss semantically stale patched skills

## Suggested Fix Directions

- Align `check`-stage outputs and transition gates around an explicit `review-gate` decision record so `check -> delivery` can be validated instead of inferred.
- Strengthen runtime drift detection for Codex patched skills and OpenCode subagent patch files from marker checks to semantic-contract checks.
- Repair command-doc/state-machine drift: `check` default next step, `brainstorm -> implementation` L0 note, and brainstorm exit snapshot validation.
- Surface ownership-proof guard obligations in the public implementation-entry path, not only in design/platform README text.

## Propagation Scope and Synchronized Update Range

- Likely affected source layers:
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/check.md`
  - `docs/workflows/新项目开发工作流/commands/review-gate.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - Possibly `commands/install-workflow.py` and `commands/shell/test_workflow_state.py` / installer tests
- Propagation risk notes:
  - Any change to route/runtime validation must be synchronized with installer tests and generated carrier expectations.
  - Any change to command next-step tables must be propagated to walkthrough/overview docs if they repeat the same rule.

## Recommended Next Step

- Recommended action: `trellis-brainstorm`
- Trigger condition: the audit has enough confirmed defects to draft a repair set, but the user explicitly required “先分析判断，再给出修正方案，用户同意后继续”。
- Recommendation reason: stop at the audit-conclusion boundary and present the repair set for confirmation.
- Stronger alternatives not selected: direct source edits would violate the user's confirmation gate.

## Stop Point and Pending Confirmations

- Auto-continue allowed: `No`
- User confirmation required for:
  - executing any source change under `docs/workflows/新项目开发工作流/`
  - whether to include the P2 doc/validator-alignment fixes together with the P1 gate/runtime fixes in the same patch set
  - whether the unresolved requirement-change-card automation branch should stay as manual-policy-only for this round

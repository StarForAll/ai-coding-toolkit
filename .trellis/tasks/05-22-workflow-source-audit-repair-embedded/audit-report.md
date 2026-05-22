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
  - `workflow-state.json` / `task.json.status` 双状态系统是否引入真实运行缺陷或维护漂移
  - `OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]` 是否构成不必要限制或能力退化
  - 六个 `CRITICAL_RUNTIME_PATCHES` 与多 helper 脚本是否产生真实破坏、漂移或高风险维护负担
  - “防止 AI 自动跨阶段推进”“严格阶段序列”是否被错误实现为超出需求的运行时强改造
  - 工作流文档、安装器、升级检查、目标项目嵌入结果之间是否存在同类不同步问题
  - 用户指控的“过度修改 / 目标偏移 / 庞杂混乱”中哪些属于真实缺陷，哪些只是设计取舍
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` workflow-installed state (`/tmp/trellis-0.5.17-2`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and extracted compatibility anchor plus managed patch/script declarations — Layer: `source repo`
- Ran `trellis -v` and confirmed current version equals `0.5.17` — Layer: `runtime command output`
- Searched workflow source/spec surface for `workflow-state`, `parallel`, `patch`, and strong-gate references to locate likely defect surfaces — Layer: `source repo`
- Read `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` and confirmed the generated target project is currently installed with `profile = outsourcing`, `disabled_commands = ["parallel"]`, and the six declared runtime patch capabilities — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Measured `commands/shell/workflow-state.py` and `工作流总纲.md` to verify the user's size claims instead of inferring them — Layer: `source repo`
- Ran `/ops/softwares/python/bin/python3 /tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py route --project-root /tmp/trellis-0.5.17-2` and captured the installed target project's first-entry routing output — Layer: `runtime command output`
- Compared personal-profile first-entry wording across `workflow-state.py`, `start-patch-phase-router.md`, `start-skill-patch-phase-router.md`, `workflow-patch-projectization.md`, `brainstorm.md`, and the deployed `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md` — Layer: `source repo` + `generated target project`
- Compared `/tmp/trellis-0.5.17-2/.claude/commands/trellis/feasibility.md`, `/tmp/trellis-0.5.17-2/.agents/skills/feasibility/SKILL.md`, `/tmp/trellis-0.5.17-2/.claude/skills/trellis-brainstorm/SKILL.md`, `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-brainstorm/SKILL.md`, and target-project `AGENTS.md` against the repaired personal-profile entry contract — Layer: `generated target project`
- Compared `/tmp/trellis-0.5.17-2/.agents/skills/trellis-brainstorm/SKILL.md` with the workflow-specific Claude/OpenCode brainstorm helper patches and confirmed the shared helper skill still carried legacy start semantics without the workflow note — Layer: `generated target project`
- Verified `context_needed` route branch source and current test file coverage, then added direct coverage plus personal bootstrap lifecycle coverage — Layer: `source repo`
- Ran `docs.workflows.新项目开发工作流.commands.shell.test_workflow_state.WorkflowStateScriptTests.test_cmd_route_prefers_keyed_degraded_hint_over_shared_file` directly and confirmed it currently passes — Layer: `runtime command output`
- Added non-blocking personal-bootstrap warnings to `route` / `validate`, documented assessment-vs-install-record precedence in the generated workflow guide, and extended shared helper drift detection for `trellis-brainstorm` when that carrier exists — Layer: `source repo`
- Ran `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state` — Layer: `runtime command output` — Result: `pass (129 tests)`
- Ran `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers` — Layer: `runtime command output` — Result: `pass (124 tests)`

## Confirmed Issues

### [P1] Personal Profile 首次入口合同漂移
- Conclusion: workflow 源文档一部分明确允许 personal profile 首次入口直接进入 `brainstorm` 并在阶段内补齐 `assessment.md` 基线，但 `workflow-state.py route`、phase-router 文档和生成到目标项目的入口文案仍把这条分支收窄成“无 assessment 就先去 feasibility”，导致安装后行为比文档承诺更严格。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
- Validation Action:
  - 对照 `brainstorm.md` / `workflow-patch-projectization.md` 中“personal profile 首次入口可在 brainstorm 内补 assessment”的合同，与 `workflow-state.py route` 的 no-task 分支、`start*phase-router` 文案和部署后的 `trellis-start` skill 做逐项比对
  - 复核旧测试名 `test_cmd_route_no_task_personal_profile_without_assessment_still_targets_feasibility`，确认此前回归测试本身就在锁定错误的更严格行为
- Impact Scope:
  - `workflow-state.py` 的首次入口决策
  - Claude / OpenCode 的 phase-router 文档补丁面
  - Codex `trellis-start` skill 生成内容
  - 目标项目 `.trellis/workflow.md` 中的 no-task 快速参考
  - 相关路由与安装器回归测试
- Suggested Fix Direction:
  - personal profile 且缺少 assessment 的 no-task 首次入口应路由到 `brainstorm`
  - 所有 phase-router / workflow patch 文档应显式保留 `outsourcing -> feasibility` 与 `personal first-entry -> brainstorm` 两条分支
  - 用安装器和 `workflow-state.py` 回归测试锁住该合同

### Applied Fix Summary
- Updated `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` so `route` now sends `profile=personal` first-entry/no-assessment cases to `brainstorm` and explains the assessment bootstrap requirement.
- Updated `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` and `commands/start-skill-patch-phase-router.md` so entry-choice guidance matches the real personal-vs-outsourcing split.
- Updated `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md` so the generated target-project workflow guide now includes both `no_task → feasibility` and `no_task → brainstorm` first-entry branches.
- Updated `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` and `commands/test_workflow_installers.py` to cover the repaired contract.

### [P2] Coverage and Entry-Surface Drift Around Personal Bootstrap
- Conclusion: after repairing the core `personal -> brainstorm` route, several adjacent workflow surfaces were still incomplete: `context_needed` had no direct route coverage, `feasibility` assets did not tell personal-profile users they could skip to `brainstorm`, the installer-managed `AGENTS.md` routing block still claimed brainstorm required a pre-existing assessment, helper docs still had blanket “all projects first go through feasibility” wording, the session-start no-task guidance still hardcoded `personal -> trellis-brainstorm` without asking the router first, and the auxiliary Claude/OpenCode `trellis-brainstorm` skills lacked the workflow-specific personal bootstrap note that the installer already treats as a maintained patch surface.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/feasibility.md`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/AGENTS.md`
  - `/tmp/trellis-0.5.17-2/.claude/commands/trellis/feasibility.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/feasibility/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.claude/skills/trellis-brainstorm/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-brainstorm/SKILL.md`
- Validation Action:
  - Counted route-action coverage and confirmed `context_needed` had no direct assertion while the source branch, breadcrumb block, and router tables all existed.
  - Compared source docs and generated target-project carriers for personal-profile first-entry wording, then confirmed AGENTS/feasibility/auxiliary brainstorm surfaces still lagged behind the repaired router contract.
  - Added lifecycle tests covering personal bootstrap allow-path, bootstrap-expiry after `assessment.md` appears, and blocked transition out of `brainstorm` without a completed assessment baseline.
- Impact Scope:
  - `workflow-state.py` direct route coverage
  - installer-generated target-project `AGENTS.md`
  - generated feasibility command/skill content
  - auxiliary Claude/OpenCode brainstorm skills patched by `install-workflow.py`
  - high-level workflow overview / walkthrough docs in the workflow source
- Suggested Fix Direction:
  - Add explicit `context_needed` coverage for a leaf-required stage with children.
  - Add personal-profile skip/exception wording to `feasibility` and AGENTS NL routing.
  - Make session-start no-task guidance run `workflow-state.py route` first for personal profile too, keeping route as the single source of truth.
  - Keep shared stage skills and auxiliary platform-local brainstorm skills aligned at least on the minimal personal-bootstrap rule.
  - Update overview/walkthrough docs that still claim every project must first enter feasibility.

### [P2] Personal Bootstrap Soft-Warning Gap
- Conclusion: the strict gate behavior for personal bootstrap is acceptable, but before this round the `brainstorm` `in_progress` reentry path gave no signal at all when `assessment.md` was still missing. That meant users could continue iterating for a long time without any reminder until they hit `awaiting_user_confirmation` or a stage transition gate.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- Validation Action:
  - Confirmed `is_personal_brainstorm_bootstrap_allowed()` returned `True` for `brainstorm + in_progress + no assessment`, which bypassed hard blockers.
  - Verified `route` already had a `warnings` channel and deployed hooks / session-start carriers already surfaced `Warnings:` lines.
  - Added non-blocking warnings for the allowed personal-bootstrap path and locked them with route/validate regression tests.
- Impact Scope:
  - `route` JSON output during personal bootstrap reentry
  - `validate` human-readable output for the same path
  - hook/session-start surfaces that display `Warnings:`
- Suggested Fix Direction:
  - Keep the path non-blocking, but emit explicit warnings that the minimum `assessment.md` baseline is still missing and must be completed before leaving `brainstorm`.

### [P2] Shared `trellis-brainstorm` Helper Patch Gap
- Conclusion: `patch_platform_brainstorm_skills()` previously patched only `.claude/skills/trellis-brainstorm` and `.opencode/skills/trellis-brainstorm`. The shared `.agents/skills/trellis-brainstorm/SKILL.md` carrier still kept legacy “Triggered from start” semantics and lacked the workflow-specific personal bootstrap note, even though `.agents/skills/brainstorm/SKILL.md` already contained the full workflow stage logic.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-brainstorm/SKILL.md`
- Validation Action:
  - Compared the installed shared helper skill with the already-patched Claude/OpenCode helper skills and confirmed the shared carrier still exposed legacy `start` wording.
  - Extended the installer patch function and regression test to cover both the platform-local stale pattern and the shared generic stale pattern.
- Impact Scope:
  - shared helper skill carrier used by Codex and other `.agents/skills/` consumers
  - installer patching logic and regression fixtures
- Suggested Fix Direction:
  - Patch `.agents/skills/trellis-brainstorm/SKILL.md` in the same installer phase as the existing Claude/OpenCode helper-skill cleanup, with wording appropriate for shared skill carriers rather than slash-command-only carriers.
  - If the shared helper skill exists in a target project, include it in route-time drift detection even though it is not part of the baseline `patched_codex_skills` install-record contract.

### [P2] Unknown-Profile Hint/Target Mismatch
- Conclusion: when `workflow-installed.json["profile"]` was present but neither `outsourcing` nor `personal`, `cmd_route` previously emitted `profile_hint="personal"` while still routing `target="feasibility"`, which was a semantic contradiction.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- Validation Action:
  - Read the no-task route branch for install-record-driven profile inference and confirmed the fallback branch hardcoded `profile_hint = "personal"` without updating `target`.
  - Added a regression test for `profile = legacy-unknown` and verified the repaired behavior now stays on `feasibility` with `profile_hint = "unknown"`.
- Impact Scope:
  - no-task first-entry route JSON contract
  - any phase-router / hook / skill surface that reads `profile_hint`
- Suggested Fix Direction:
  - Preserve the safer fallback target (`feasibility`) for unknown profiles, but stop claiming the project is personal; emit `profile_hint = "unknown"` instead.
  - Surface the same conservative behavior in route-consumer text: if `profile_hint=unknown`, ask the user whether the project should be treated as personal or outsourcing before skipping feasibility.

### [P2] Personal Bootstrap Exit Messaging Drift
- Conclusion: the stricter exit gate for personal bootstrap is correct, but the old blocker/error text was misleading: once `brainstorm` moved toward exit or transition, missing `assessment.md` was still reported as if every project had to “go back and complete feasibility,” even though the supported fix for a personal-profile first entry is to finish the minimum assessment baseline inside the current `brainstorm` stage.
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- Validation Action:
  - Reviewed `collect_route_readiness_blockers()` and `validate_external_project_controls()` and confirmed the gate already blocks exit/transition correctly.
  - Reproduced personal bootstrap exit/transition paths and verified the old messages instructed users toward feasibility instead of telling them to finish the bootstrap fields inside `brainstorm`.
  - Added tests for `awaiting_user_confirmation` with no assessment and for transition-to-design with no assessment to lock the corrected wording.
- Impact Scope:
  - `route` blocker text
  - `validate` / stage-transition error text
  - generated `.trellis/workflow.md` breadcrumb guidance
- Suggested Fix Direction:
  - Keep the gate strict, but change the error text to “finish the minimum assessment baseline in the current brainstorm stage first” for personal-profile bootstrap scenarios, instead of implying feasibility is the only recovery path.

## Unconfirmed Items / False Alarms
- `OPTIONAL_DISABLED_BASELINE_COMMANDS = ["parallel"]` -> false alarm in this round. The installed target project's workflow record explicitly marks `parallel` as an intentionally disabled baseline command, and no runtime breakage or source/target inconsistency was evidenced from that choice alone.
- `.agents/skills/trellis-brainstorm` 缺 personal bootstrap 逻辑 -> false alarm as stated. The actual shared stage-skill carrier in installed target projects is `.agents/skills/brainstorm/SKILL.md`, and it already contained the full personal bootstrap guidance. The real drift was narrower: auxiliary platform-local `trellis-brainstorm` skills for Claude/OpenCode only had generic baseline wording, so they received a minimal workflow-specific note instead of being treated as the primary missing carrier.
- `完整流程演练.md` 未更新 -> false alarm in this round. `docs/workflows/新项目开发工作流/完整流程演练.md` declares itself an external-project dual-track special-case walkthrough rather than the generic first-entry guide, so keeping its fixed `feasibility -> brainstorm` path is consistent with its scoped example.
- `test_cmd_route_prefers_keyed_degraded_hint_over_shared_file` 失败 -> false alarm in this round. The current source test passes as-is and was not affected by the personal-profile routing work.
- `validate_external_project_controls(target_stage!=None)` should keep the full personal bootstrap exemption -> false alarm in this round. Allowing stage transitions out of `brainstorm` without an assessment would weaken the intended gate; the real defect was the old message implying “go do feasibility” instead of “finish the bootstrap baseline here first.”
- `is_personal_brainstorm_bootstrap_allowed` should remain true in `awaiting_user_confirmation` -> false alarm in this round. The supported model is that bootstrap is allowed during normal `in_progress` work; once the user marks the stage ready to exit, missing assessment becomes a blocker. The repaired wording now makes that boundary explicit instead of misleading users toward feasibility.
- `task.json.status` 降级为 bookkeeping only -> false alarm in this round. Current strong-gate source docs, hooks, and target-project router consistently treat `workflow-state.py route` / `workflow-state.json` as the routing authority; no residual status-driven routing bug was confirmed in this audit.
- `workflow-state.py` / `工作流总纲.md` 体量过大 -> unconfirmed as a defect. The size claims are factually true, but this round did not find a correctness bug that follows from size alone, so no shrink-only rewrite was applied.
- `6 个 critical runtime patches` / `15 个 helper scripts` -> unconfirmed as a defect. Complexity is real, but this run did not prove that patch count itself caused a current source/target contract failure beyond the repaired personal-entry drift.
- `DEFAULT_PROFILE = "outsourcing"` -> not auto-changed. This is a product policy decision with broad workflow-behavior impact; `/tmp/trellis-0.5.17-2` confirms the current contract, but this audit did not establish that flipping the default is a safe same-run maintenance fix.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- None yet.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not re-audited in this round
- Repo-local evidence checked: `start-patch-phase-router.md`, `workflow-patch-projectization.md`, installer-generated Claude command carriers
- Practical development-use evidence checked: partial; generated target-project workflow guide and phase-router command text were inspected
- Agreement / discrepancy: repaired local discrepancy around personal first-entry wording
- Expected carrier model: phase-router command text must describe the same first-entry branches as `workflow-state.py route`
- Does the current implementation match: yes after the source fix and regression pass
- If not, what is wrong: n/a

### OpenCode
- Official docs checked: not re-audited in this round
- Repo-local evidence checked: `start-patch-phase-router.md`, `workflow-patch-projectization.md`
- Practical development-use evidence checked: indirect; shared phase-router source and installer regression cover the generated OpenCode command surface
- Agreement / discrepancy: repaired local discrepancy around personal first-entry wording
- Expected carrier model: generated command text must stay aligned with `workflow-state.py route`
- Does the current implementation match: yes after the source fix and regression pass
- If not, what is wrong: n/a

### Codex
- Official docs checked: not re-audited in this round
- Repo-local evidence checked: `start-skill-patch-phase-router.md`, `workflow-state.py`, installer patch helpers
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md` plus target-project route output
- Agreement / discrepancy: repaired local discrepancy around personal first-entry wording
- Expected carrier model: `trellis-start` skill and `.trellis/workflow.md` must expose the same profile-aware first-entry rules as `workflow-state.py route`
- Does the current implementation match: yes after the source fix and regression pass
- If not, what is wrong: n/a

## Suggested Fix Directions
- Keep treating “复杂 / 重 / 管得多”与“真实缺陷”分开：只有当源合同、装后结果、运行时输出三者出现可证明的不一致时再修。
- If a future audit wants to revisit `DEFAULT_PROFILE`, handle it as a dedicated product-policy change with its own blast-radius review instead of folding it into unrelated maintenance bugfixes.

## Propagation Scope and Synchronized Update Range
- Updated layers in this round:
  - `commands/shell/workflow-state.py`
  - `commands/feasibility.md`
  - `commands/install-workflow.py`
  - `commands/start-patch-phase-router.md`
  - `commands/start-skill-patch-phase-router.md`
  - `commands/workflow-patch-projectization.md`
  - `命令映射.md`
  - `commands/shell/test_workflow_state.py`
  - `commands/test_workflow_installers.py`
  - `工作流总纲.md`
  - `工作流全局流转说明（通俗版）.md`
  - `多CLI通用新项目完整流程演练.md`
- Additional synchronized behavior added in this round:
  - route/validate non-blocking warnings for personal bootstrap
  - route-time drift detection for optional shared helper `trellis-brainstorm`
  - explicit assessment-vs-install-record precedence wording in generated workflow guidance
- Propagation risk: first-entry routing rules are unusually propagation-prone because the same contract is duplicated across runtime router code, generated target-project workflow text, Codex start skill text, and installer regressions

## Recommended Next Step
- Recommended action: `plain-language wrap-up`
- Trigger condition: confirmed defect repaired, targeted verification green, and no further evidence-backed source defect is queued in this round
- Recommendation reason: the remaining candidate issues are either false alarms in this round or broader product-policy questions, not safe same-run maintenance fixes
- Stronger alternatives not selected: no architecture rewrite and no `DEFAULT_PROFILE` flip because this run did not prove those larger changes are necessary or low-risk

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - whether to open a separate follow-up scope for `DEFAULT_PROFILE` / broader workflow product positioning, which was intentionally not changed in this maintenance fix

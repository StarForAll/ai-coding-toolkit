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
  - READY 即自动继续的旧语义残留
  - Codex 自然语言收尾路由仍把“记录/保存进度/收工/结束工作”映射到 finish-work
  - `repair_needed` 在缺少 `workflow-state.json` 时给出错误的 `init --stage feasibility` 恢复提示
  - `trellis-finish-work` skill 标题/摘要仍泄漏旧的 delivery / record-session 边界
  - 跨 CLI 同步已补脚本但未彻底收口，导致 prompt 层与脚本层不再单一真相源
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and checked `COMPATIBLE_TRELLIS_VERSION` — Layer: `source repo`
- Ran `trellis -v` and recorded the current version — Layer: `runtime command output`
- Used `ace.search_context` to locate source workflow files related to READY gating, finish/record-session routing, repair flow, and CLI patch surfaces — Layer: `source repo`
- Read repo-local audit/spec contracts for workflow maintenance under `.trellis/spec/skills/workflow-audit.md`, `.trellis/spec/scripts/workflow-command-doc-contracts.md`, `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` — Layer: `source repo`
- Searched the source workflow and `/tmp/trellis-0.5.17-2` for READY auto-continue, finish-work / record-session routing, and repair guidance residues via `rg` — Layer: `source repo` / `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Inspected `/tmp/trellis-0.5.17-2/AGENTS.md`, `.codex/hooks/session-start.py`, `.claude/hooks/session-start.py`, `.opencode/lib/session-utils.js`, `.agents/skills/trellis-finish-work/SKILL.md`, and `.trellis/workflow.md` to confirm installed-state behavior — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Updated workflow source files only under `docs/workflows/新项目开发工作流/` and kept task artifacts under `.trellis/tasks/05-19-fix-workflow-gating-and-finish-routing/` — Layer: `source repo`
- Ran `/ops/softwares/python/bin/python3 -m unittest test_workflow_installers.py` in `docs/workflows/新项目开发工作流/commands` — Layer: `runtime command output`
- Ran `/ops/softwares/python/bin/python3 -m unittest test_workflow_state.py` in `docs/workflows/新项目开发工作流/commands/shell` — Layer: `runtime command output`
- Re-scanned the workflow root for second-pass residues around `record-session` asset classification and walkthrough close-out flow wording — Layer: `source repo`
- Ran targeted installer regression tests for the second-pass doc residues:
  - `test_cli_matrix_treats_record_session_as_distributed_not_baseline_patch`
  - `test_full_walkthrough_closeout_example_keeps_delivery_before_record_session`
  - `test_upgrade_merge_removes_ready_autocontinue_prompt_residue`
  — Layer: `runtime command output`

## Confirmed Issues

### [P1] SessionStart / session-utils 入口提示仍残留 READY 自动续跑旧语义
- Conclusion: 真实存在；虽然强门禁补丁已把 `_get_task_status()` / `getTaskStatus()` 改成 route-first，但 Python / JS carrier 的 `<ready>` 提示仍明确要求“READY 就直接继续下一步”，会诱导新会话越过人工确认门禁。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.codex/hooks/session-start.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
  - `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js`
  - All three installed carriers still contained `If a task is READY, execute its Next required action without asking whether to continue.`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Validation Action:
  - Searched both source and installed target files for the legacy READY auto-continue sentence.
  - Read the existing patch logic and confirmed it only replaced route logic, not the startup guidance sentence.
- Impact Scope:
  - Claude Code / Codex session-start carriers
  - OpenCode session context carrier
  - New-session / re-enter prompt behavior
- Suggested Fix Direction:
  - Extend Python session-start patching and OpenCode session-utils patching to rewrite the legacy READY sentence into route-authoritative strong-gate guidance.
  - Strengthen `upgrade-compat.py --check` and installer tests so marker presence alone is no longer considered sufficient.
  - Fix Applied:
  - Updated `patch-session-start-strong-gate.py`, `install-workflow.py`, `upgrade-compat.py`, and installer tests to detect and remove READY auto-continue residue.

### [P1] Codex NL 路由仍把“记录/保存进度/收工/结束工作”指向 finish-work
- Conclusion: 真实存在；当前终态是 `record-session`，而不是 `finish-work`。把这些意图路由到 `finish-work` 会把用户带回前序收尾阶段，造成重复收尾或错误回退感。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/AGENTS.md`
  - Installed AGENTS block mapped `记录、保存进度` / `收工、结束工作` to `/trellis:finish-work`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/命令映射.md`
- Validation Action:
  - Compared installed AGENTS routing with `record-session.md` and `.trellis/workflow.md` terminal-stage definition.
  - Verified the source installer generated the same wrong rows, so the residue was source-authored rather than target-only drift.
- Impact Scope:
  - Codex AGENTS natural-language routing
  - Human-readable command mapping docs
- Suggested Fix Direction:
  - Route these terminal close-out intents to `record-session`, and document that strong-gate validation may still bounce the user back if delivery is incomplete.
  - Fix Applied:
  - Updated `install-workflow.py`, `命令映射.md`, `record-session.md`, and installer tests to map these intents to `record-session`.

### [P1] `repair_needed` 缺失状态文件时仍错误提示 `init --stage feasibility`
- Conclusion: 真实存在；`workflow-state.py repair` 已明确禁止从产物反推阶段，但 `route` 在缺少 `workflow-state.json` 时仍硬编码提示 `init <task-dir> --stage feasibility`，会把已有任务粗暴重置到早期阶段。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - Missing-state route branch returned a `repair_needed` reason that explicitly told users to run `workflow-state.py init <task-dir> --stage feasibility`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - User-provided evidence pointed to `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
- Validation Action:
  - Read the missing-state route branch in source and compared it against `cmd_repair` behavior plus the phase-router docs that already instruct `workflow-state.py repair`.
  - Added a regression assertion in `test_workflow_state.py` to ensure the route reason references `repair`, not `init feasibility`.
- Impact Scope:
  - All CLIs that rely on `workflow-state.py route`
  - Any task created before workflow installation or with missing state file
- Suggested Fix Direction:
  - Make the route reason instruct `workflow-state.py repair`, and surface the same explicit confirmation requirements already enforced by `cmd_repair`.
  - Fix Applied:
  - Updated the route reason in `workflow-state.py` and added test coverage in `test_workflow_state.py`.

### [P2] finish-work 项目化补丁摘要仍泄漏旧的 delivery / record-session hand-off 模型
- Conclusion: 真实存在；`build_finish_work_content()` 仍把 `trellis-finish-work` 的 description / opening summary 写成 “hand off to delivery / record-session”，与当前 `finish-work` 只负责 pre-delivery close-out 的边界不够干净。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-finish-work/SKILL.md`
  - Installed skill description and opening summary still described finish-work as handing off to `delivery / record-session`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- Validation Action:
  - Compared the installed Codex `trellis-finish-work` skill text against `.trellis/workflow.md` and `record-session.md`.
  - Located the source string replacements in `build_finish_work_content()`.
- Impact Scope:
  - Codex shared `trellis-finish-work` skill
  - Any carrier that reuses the same finish-work projectization string replacements
- Suggested Fix Direction:
  - Rewrite the description/opening summary so finish-work is described as pre-delivery close-out only, with archive + add_session deferred explicitly to `record-session`.
  - Fix Applied:
  - Updated the finish-work string replacements in `install-workflow.py` and kept installer regression coverage on the absence of the old wording.

### [P2] close-out 文档层仍散落旧模型，和当前状态机/终态顺序不一致
- Conclusion: 真实存在；除脚本和 AGENTS 路由外，多份工作流总纲、演练、README、思维导图和装后核对清单仍把 finish-work 描述成最终收尾入口，或把顺序写成“先记录 session 再 archive”，与当前 `finish-work → delivery → record-session` 且终态先 archive 再 add_session 的模型冲突。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/完整流程演练.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/README.md`
  - `docs/workflows/新项目开发工作流/工作流思维导图.html`
- Validation Action:
  - Searched the workflow root for phrases such as `含 session record`, `先记录 session`, `先记录再archive`, and `会话记录由 .*finish-work`.
  - Cross-checked those lines against `.trellis/workflow.md`, `delivery.md`, and `record-session.md`, which already describe the authoritative strong-gate close-out chain.
- Impact Scope:
  - Maintainer-facing workflow documentation
  - CLI-specific platform readmes
  - Mindmap / walkthrough guidance
- Suggested Fix Direction:
  - Normalize all of these docs to the same close-out chain and terminal-stage order, without changing unrelated structure.
  - Fix Applied:
  - Updated the affected docs and mindmap text so they consistently describe `finish-work → delivery → record-session`, with archive preceding add_session at the terminal stage.

### [P2] 资产分类总览仍把 `record-session` 误写成 baseline patch
- Conclusion: 第二轮深扫中确认仍有残留；`CLI原生适配边界矩阵.md` 的跨平台对比与收尾基线依赖表，仍把 `record-session` 归到 baseline patch / fresh baseline patch，但 `workflow_assets.py` 的单一真相里它属于 `OVERLAY_BASELINE_COMMANDS`。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- Validation Action:
  - Compared the matrix rows against `PATCH_BASELINE_COMMANDS = ["continue", "finish-work"]` and `OVERLAY_BASELINE_COMMANDS = ["brainstorm", "check", "record-session"]`.
  - Added a static regression assertion in `test_workflow_installers.py` so future edits cannot silently reclassify `record-session`.
- Impact Scope:
  - Maintainer-facing managed-surface summary
  - Close-out asset ownership documentation
- Suggested Fix Direction:
  - Reclassify `record-session` as workflow-distributed terminal close-out command/skill and keep legacy baseline `record-session` language only inside compatibility caveats.
  - Fix Applied:
  - Updated `CLI原生适配边界矩阵.md` and added a regression assertion in `test_workflow_installers.py`.

### [P2] `完整流程演练.md` 的最小收尾样例仍绕过 `delivery` / `record-session` 阶段命令
- Conclusion: 第二轮深扫中确认仍有残留；该样例标题仍写成 `finish-work → session record`，并直接展示 `task.py archive` / `add_session.py`，容易让读者误以为可以跳过 `delivery` 与 `record-session` 终态命令。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/完整流程演练.md`
- Validation Action:
  - Re-read the walkthrough section against `delivery.md`, `record-session.md`, and `.trellis/workflow.md`.
  - Added a static regression assertion in `test_workflow_installers.py` requiring the walkthrough header to keep `finish-work → delivery → record-session`.
- Impact Scope:
  - Human-facing walkthrough documentation
  - Future maintainer understanding of terminal close-out flow
- Suggested Fix Direction:
  - Keep the underlying `archive` / `add_session.py` commands as implementation detail of `record-session`, but restore the stage-command chain in the example itself.
  - Fix Applied:
  - Updated `完整流程演练.md` and added a regression assertion in `test_workflow_installers.py`.

## Unconfirmed Items / False Alarms

- None. All candidate items above were confirmed as real defects or grouped into a broader confirmed drift issue.

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

- None currently.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: `not-applicable` for this round; no upstream Claude capability judgment was needed to confirm these source-local patch/document residues
- Repo-local evidence checked: `commands/install-workflow.py`, `commands/claude/README.md`, `commands/session-start-patch-strong-gate.md`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
- Agreement / discrepancy: repo-local workflow contract and installed-state output had drift before the fix; source contract is now aligned to the strong-gate model
- Expected carrier model: baseline `continue` / `finish-work` command patch + route-first `session-start.py`
- Does the current implementation match: `yes after source fix`
- If not, what is wrong: pre-fix source lacked startup-guidance cleanup and had close-out wording drift

### OpenCode
- Official docs checked: `not-applicable` for this round; no upstream OpenCode capability judgment was needed to confirm these source-local patch/document residues
- Repo-local evidence checked: `commands/install-workflow.py`, `commands/opencode/README.md`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js`
- Agreement / discrepancy: repo-local workflow contract and installed-state output had drift before the fix; source contract is now aligned to the strong-gate model
- Expected carrier model: baseline command patches plus workflow-managed `session-utils.js` strong-gate patch
- Does the current implementation match: `yes after source fix`
- If not, what is wrong: pre-fix source did not upgrade READY auto-continue prompt residue in `session-utils.js`

### Codex
- Official docs checked: `not-applicable` for this round; no upstream Codex capability judgment was needed to confirm these source-local patch/document residues
- Repo-local evidence checked: `commands/install-workflow.py`, `commands/codex/README.md`, `commands/workflow_assets.py`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/AGENTS.md`, `/tmp/trellis-0.5.17-2/.codex/hooks/session-start.py`, `/tmp/trellis-0.5.17-2/.agents/skills/trellis-finish-work/SKILL.md`
- Agreement / discrepancy: repo-local workflow contract and installed-state output had drift before the fix; source contract is now aligned to the strong-gate model
- Expected carrier model: AGENTS NL routing + active shared skills dir + route-first session-start hook
- Does the current implementation match: `yes after source fix`
- If not, what is wrong: pre-fix source routed terminal close-out intents to finish-work and left finish-work summary/startup guidance residues

## Suggested Fix Directions

- Keep `workflow-state.py route` as the only authority for startup / breadcrumb / close-out routing semantics.
- Treat installer patches, installed docs, AGENTS NL routing, and regression tests as one change surface whenever close-out or startup semantics change.
- Prefer validating partial-patch residues by behavior/text, not by patch marker presence alone.

## Propagation Scope and Synchronized Update Range

- 可能涉及 `commands/*.md`、`commands/shell/*.py`、`commands/*/README.md`、`workflow_assets.py`、`test_*.py`
- 风险点：补丁行为、安装契约、说明文档和测试之间容易发生同步遗漏

## Recommended Next Step

- Recommended action: `进入 trellis-check / 提交前收尾`
- Trigger condition: 源工作流修复已完成，关键安装器与 workflow-state 回归测试已通过
- Recommendation reason: 当前最合理的下一步是做最终质量复核并准备 Phase 3.4 的提交计划
- Stronger alternatives not selected: 未继续扩大审计范围到版本兼容或正式重新嵌入，因为本轮缺陷已在同版本源工作流内闭环验证

## Stop Point and Pending Confirmations

- Auto-continue allowed: `No`
- User confirmation required for:
  - Phase 3.4 的提交计划与 commit message 分组

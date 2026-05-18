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
  - `finish-work` 门禁未被 `workflow-state.py` 真正强制校验 `finish-work-checklist.md`
  - `trellis-meta` 参考文档残留旧三阶段 / `task.json.status` 模型
  - `personal` profile 的 `first_entry` 路由文案与实际脚本不一致
  - Codex `SessionStart` 集成疑似半安装状态
  - 文档/帮助文本仍把 `task.json.status` 当主状态，和 `workflow-state.json.stage` 冲突
  - 缺少对脚本 / hooks / skills / commands 漂移的回归测试护栏
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Checked workflow anchor version in `docs/workflows/新项目开发工作流/commands/workflow_assets.py` — Layer: `source repo`
- Ran `trellis -v` and confirmed `0.5.17` — Layer: `runtime command output`
- Read repo-local audit guidance, docs/scripts/skills specs, and workflow-audit report contract — Layer: `source repo`
- Used semantic code search to locate workflow-state, finish-work, trellis-meta, Codex hook, first-entry routing, and test assets — Layer: `source repo`
- Inspected `/tmp/trellis-0.5.17-2` installed assets: `.trellis/workflow.md`, `.trellis/scripts/workflow/workflow-state.py`, `.agents/skills/trellis-finish-work/SKILL.md`, `.agents/.claude/.opencode` `trellis-meta` references, `.codex/hooks.json`, `.codex/hooks/session-start.py`, `.trellis/workflow-installed.json` — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Ran `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` — Layer: `runtime command output`
- Ran `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` — Layer: `runtime command output`

## Confirmed Issues

### [P1] `finish-work` 门禁没有真正强制 `finish-work-checklist.md`
- Conclusion: 真实存在；原状态机只在 `check -> finish-work/review-gate` 校验 `check.md`，但 `finish-work -> delivery` 没有任何 `finish-work-checklist.md` 强校验，确实能在未冻结验证矩阵/收尾证据的情况下进入 `delivery`。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 原实现仅对 `new_stage in {"finish-work", "review-gate"}` 调 `validate_check_gate`，且 `collect_exit_gate_blockers()` 不含 `finish-work`
  - Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py` 具有同样缺口
- Validation Action:
  - 静态比对 source repo 与 `/tmp` 安装态脚本
  - 新增/运行 `workflow-state` 回归用例，验证 `finish-work -> delivery` 缺 checklist 时被拒绝，补 checklist 后放行
- Impact Scope:
  - `.trellis/scripts/workflow/workflow-state.py`
  - `finish-work` / `delivery` close-out 主链
- Suggested Fix Direction:
  - 新增 `validate_finish_work_gate()`
  - 将 `finish-work-checklist.md` 设为 `finish-work -> delivery` 强门禁
  - `repair` 推断支持 `finish-work`
  - `finish-work` 补丁文档收紧为“必须落盘 checklist”

### [P1] `trellis-meta` 参考文档仍在教授旧三阶段 / `task.json.status` 模型
- Conclusion: 真实存在；`/tmp` 中 `.agents/skills/trellis-meta` 及 `.claude/.opencode` 对应副本的多个参考文档仍描述 `planning / in_progress / completed`、`/finish-work` 内 archive、以及“current task status” 驱动的 workflow-state，和强门禁 stage 链明显冲突。
- Evidence Source:
  - Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/local-architecture/workflow.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/local-architecture/context-injection.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/platform-files/hooks-and-settings.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/customize-local/change-workflow.md`
- Validation Action:
  - 直接读取 `/tmp` 安装态文档并核对其中的状态模型描述
  - 反查 source workflow 是否已有对应 overlay；结论为没有，需要在 workflow 内新增 install-time 覆盖
- Impact Scope:
  - `.agents/skills/trellis-meta/references/**`
  - `.claude/skills/trellis-meta/references/**`
  - `.opencode/skills/trellis-meta/references/**`
- Suggested Fix Direction:
  - 在 workflow 源内新增 `trellis-meta-strong-gate/` 覆盖文本
  - 安装时若目标项目存在对应 reference 文件，则统一覆盖成强门禁版本

### [P2] `first_entry` 路由文案对 personal profile 写错
- Conclusion: 真实存在；`workflow-state.py route` 对 personal profile 已返回 `target=brainstorm`，但 continue/start patch 表格仍写成固定“Use the feasibility skill / 路由到 /trellis:feasibility”。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` 已有 personal-profile route 用例
  - Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-continue/SKILL.md`
- Validation Action:
  - 对比 route 实际行为与 installed continue skill/action table
- Impact Scope:
  - Claude/OpenCode continue command patch
  - Codex continue skill patch
- Suggested Fix Direction:
  - 把 `first_entry` 执行动作改为“按 `target` 字段进入对应阶段”

### [P2] Codex `SessionStart` 处于“被 workflow 当必需，但实际未接线”的半安装状态
- Conclusion: 真实存在，但更准确的根因是**合同漂移**而不是单纯“缺失接线”；当前 workflow 文档已把 Codex 主承载定义为 `.codex/hooks.json -> inject-workflow-state.py` 的 turn-level hook，但安装器、`critical_runtime_patches` 和 `upgrade-compat` 又把 `.codex/hooks/session-start.py` 当成必需补丁面。
- Evidence Source:
  - Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.codex/hooks.json` 仅注册 `UserPromptSubmit`
  - `/tmp/trellis-0.5.17-2/.codex/hooks/session-start.py` 存在且被打补丁
  - `/tmp/trellis-0.5.17-2/.trellis/workflow-installed.json` 把 `session-start-strong-gate` 记为 critical runtime patch
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md` / `CLI原生适配边界矩阵.md` 已将 Codex 主承载描述为 turn-level hook
- Validation Action:
  - 核对 installed hooks.json 与 session-start carrier
  - 核对安装器、状态机 embed-invalid 检查、upgrade-compat 检查的期望是否一致
- Impact Scope:
  - `install-workflow.py`
  - `upgrade-compat.py`
  - `workflow-state.py` embed-invalid check
  - Codex maintainer docs
- Suggested Fix Direction:
  - 把 Codex `session-start.py` 明确降级为可选辅助面
  - 仅保留 `.codex/hooks.json` + `inject-workflow-state.py` 为当前 workflow 的主合同
  - 相应调整 install-record `critical_runtime_patches`

### [P2] `workflow.md` 与项目化补丁仍残留 `task.json.status` 主状态口径
- Conclusion: 真实存在；目标项目 `.trellis/workflow.md` 的 task system 段落仍写“`task.py start` flips `task.json.status` from planning to in_progress`”，而项目化 patch 的 customize-local 说明也仍在指导“custom status 由 lifecycle hook 写 `task.json.status`”，与强门禁真实判定链冲突。
- Evidence Source:
  - Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- Validation Action:
  - 读取 `/tmp` installed workflow guide
  - 对照 source patch 文本与 `patch-task-start-strong-gate.py` 的真实运行时语义
- Impact Scope:
  - `.trellis/workflow.md` install-time patch
  - 相关 maintainer/reference docs
- Suggested Fix Direction:
  - 安装器对 workflow guide 中的旧 `Current-task mechanism` 说明做强门禁对齐替换
  - patch 文本改为明确“routing layer emits breadcrumb keys，`task.json.status` 不是 stage source of truth”

### [P2] 额外发现：plan gate 被错误施加到 `brainstorm -> implementation/test-first` 直达路径
- Conclusion: 真实存在；代码注释写的是“Plan -> execution requires plan artifacts”，实现却对所有进入执行态的切换都执行了 `validate_plan_gate()`，导致 L0 直达路径被误拒。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - Layer: `runtime command output`
  - `test_workflow_state.py` 原有 `Issue 7` 用例在回归时失败，报 `task_plan.md` 缺失
- Validation Action:
  - 运行 `workflow-state` 全量测试时触发失败，再回溯状态机条件
- Impact Scope:
  - `workflow-state.py` stage transition gates
- Suggested Fix Direction:
  - 仅在 `state.stage == "plan"` 且 `new_stage in EXECUTION_STAGES` 时执行 `validate_plan_gate()`

## Unconfirmed Items / False Alarms

- “这层工作流几乎没有回归测试护栏” -> `false alarm`
  - 实际存在较完整的 `commands/test_workflow_installers.py` 与 `commands/shell/test_workflow_state.py` 等测试集
  - 更准确的问题是：此前**缺少针对本轮缺陷的特定回归用例**，例如 `finish-work` 强门禁、Codex SessionStart 可选合同、trellis-meta 强门禁 reference 覆盖、以及 workflow guide 文案漂移
  - 本轮已补上这些测试

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

- None yet

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable
- Repo-local evidence checked: `continue.md`, `finish-work.md`, `.claude/hooks/*.py`, install/upgrade scripts
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2` installed assets
- Agreement / discrepancy: 主要一致
- Expected carrier model: workflow patch 负责 Claude baseline commands；SessionStart hook 仍是强门禁补丁面
- Does the current implementation match: yes, after fix
- If not, what is wrong: none remaining in current fix scope

### OpenCode
- Official docs checked: not-applicable
- Repo-local evidence checked: `continue.md`, `finish-work.md`, `.opencode/lib/session-utils.js`, install/upgrade scripts
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2` installed assets
- Agreement / discrepancy: 主要一致
- Expected carrier model: workflow patch 管理命令与 session-utils 强门禁补丁；共享 `.agents/skills/` 仅作 shared carrier
- Does the current implementation match: yes, after fix
- If not, what is wrong: none remaining in current fix scope

### Codex
- Official docs checked: local CLI evidence only (`codex --help`, installed hook carriers, repo-local Codex adapter docs)
- Repo-local evidence checked: `commands/codex/README.md`, `CLI原生适配边界矩阵.md`, `install-workflow.py`, `upgrade-compat.py`, `workflow-state.py`
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.codex/hooks.json` + `.codex/hooks/*.py`
- Agreement / discrepancy: 之前存在明显合同漂移；修复后统一为“turn-level hook 主承载 + SessionStart 可选辅助面”
- Expected carrier model: `.codex/hooks.json -> inject-workflow-state.py` 为主；`.agents/skills/` 为 workflow 共享 skills 主入口；`session-start.py` 非当前必需 carrier
- Does the current implementation match: yes, after fix
- If not, what is wrong: none remaining in current fix scope

## Suggested Fix Directions

- 已实施：`workflow-state.py` 增加 `finish-work` 强门禁、repair 推断与 blocker 回报
- 已实施：Codex SessionStart 合同降级为可选辅助面，并把 install/upgrade/install-record/runtime checks 对齐
- 已实施：为 trellis-meta 参考文档新增 workflow-local 强门禁覆盖层，并在安装时同步到 `.agents/.claude/.opencode`
- 已实施：修正 `start`/`continue` 的 `first_entry` 动作表与 workflow guide / patch 文案冲突
- 已实施：补充针对上述缺陷的 installer 与 workflow-state 回归测试

## Propagation Scope and Synchronized Update Range

- `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/**`
- `docs/workflows/新项目开发工作流/commands/*phase-router*.md`
- `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/workflow-patch-projectization.md`
- `docs/workflows/新项目开发工作流/commands/codex/README.md`
- `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
- `docs/workflows/新项目开发工作流/工作流总纲.md`
- `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
- `docs/workflows/新项目开发工作流/工作流思维导图.html`
- `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`

## Recommended Next Step
- Recommended action: `check`
- Trigger condition: `所有修复已落盘，相关脚本/installer 全量测试通过`
- Recommendation reason: `当前已完成实现与主验证，可以进入收尾/提交评估`
- Stronger alternatives not selected: `无需继续扩展范围到 repo 外 live carriers`

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - `是否接受将 trellis-meta live source carriers（当前仓库 .agents/.claude/.opencode）继续留在 repo 外范围，仅通过 workflow 安装覆盖修正目标项目`
  - `提交/归档策略`

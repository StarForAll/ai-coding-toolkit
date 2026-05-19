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
  - brainstorm 到 implementation/test-first 缺少 L0 硬门禁
  - record-session 命令层仍可直接执行
  - degraded active-task fallback 为 repo 级共享文件
  - session-start 强门禁补丁保留不可达旧分支
  - brainstorm 文档与脚本对出口快照字段门禁语义漂移
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `workflow_assets.py` and ran `trellis -v` to confirm version gate — Layer: `source repo`
- Read workflow authoring specs, workflow-audit skill contract, and command/script specs — Layer: `source repo`
- Indexed workflow source assets and searched issue-related identifiers across `docs/workflows/新项目开发工作流/` and `/tmp/trellis-0.5.17-2` — Layer: `source repo`
- Compared installed workflow copies inside `/tmp/trellis-0.5.17-2` for brainstorm / delivery / record-session / hook carriers / workflow-state references — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`

## Confirmed Issues

### [P1] brainstorm 直达执行态缺少 L0 脚本硬门禁
- Conclusion: `brainstorm` 在 `allowed_next_stages` 指向 `implementation/test-first` 时，原实现只校验粗估、正式 PRD 和出口快照字段存在性，没有把 `complexity_decision=L0` 作为直达执行态的强约束，导致高复杂度任务可绕过 `design/plan`
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - command: `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state.WorkflowStateScriptTests.test_route_brainstorm_execution_path_blocks_when_complexity_is_not_l0 ...`
- Validation Action:
  - 对比 `brainstorm.md` 中 L0 降级规则与 `validate_brainstorm_exit_gate()` 的实现
  - 先新增失败用例证明 `L1/L2` 仍可拿到 `awaiting_confirmation`
  - 修复后重跑相关与全量 `test_workflow_state.py`
- Impact Scope:
  - `workflow-state.py route`
  - `workflow-state.py set --stage implementation/test-first`
  - 所有安装后目标项目的强门禁执行阶段入口
- Suggested Fix Direction:
  - 在 `validate_brainstorm_exit_gate()` 中仅对“纯直达执行态”路径追加 `complexity_decision=L0` 检查
  - 同步修正文档对该字段门禁等级的描述

### [P1] record-session 交互层仍像可直接执行入口，且 validate 未覆盖 record-session 终态门禁
- Conclusion: 虽然状态机已封死 `finish-work -> record-session` 快捷切换，但 `record-session.md` 仍像自由入口操作手册，安装器 NL 路由表还把“记录、保存进度”映射到 `record-session`；同时 `workflow-state.py validate` 未在 `stage=record-session` 时复核 delivery 产物
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/record-session.md`
  - `docs/workflows/新项目开发工作流/commands/delivery.md`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - command: `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state.WorkflowStateScriptTests.test_validate_record_session_stage_requires_delivery_artifacts`
- Validation Action:
  - 对比 `.trellis/workflow.md` 的阶段链路与 `record-session.md` / 安装器 NL 路由表
  - 新增 `record-session` validate 失败用例，证明原实现未拦截缺失的 delivery 产物
- Impact Scope:
  - 目标项目中的 `/trellis:record-session`
  - AGENTS 自然语言路由表
  - `workflow-state.py validate`
- Suggested Fix Direction:
  - `record-session.md` 加 route/validate 门禁块
  - `delivery.md` 和 NL 路由表统一改成通过 `finish-work -> delivery -> record-session` 进入终态
  - `validate_stage_exit_artifacts()` 覆盖 `record-session`

### [P2] degraded active-task fallback 为 repo 级共享文件，存在错路由风险
- Conclusion: 当完全缺失 session identity 时，原工作流补丁只使用 `.trellis/.runtime/degraded-active-task.json` 作为共享 fallback；多 degraded 会话并发时存在最后写入覆盖前者的风险
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`
- Validation Action:
  - 阅读已安装目标项目中的 `task.py` degraded 补丁与 router fallback 逻辑
  - 新增 keyed degraded 优先级测试，证明修复后先读 `degraded-active-task-<key>.json`，再回退共享文件
- Impact Scope:
  - 无 session identity 的 CLI / degraded 会话
  - `task.py start/current/finish`
  - `workflow-state.py route`
- Suggested Fix Direction:
  - 保留共享 fallback 兼容旧项目，但优先使用 `TRELLIS_CONTEXT_ID` / `TERM_SESSION_ID` / `ppid` 派生的 keyed degraded 文件做次级隔离
  - 在审计结论中明确这是风险缓释而非绝对消除

### [P1] session-start 强门禁补丁保留不可达旧尾逻辑
- Conclusion: 原补丁通过在 `_get_task_status()` 中前插一个总是 return 的 route-first 代码块实现，导致旧 `PLANNING/READY/COMPLETED` 尾逻辑残留为不可达死代码，已在 `/tmp/trellis-0.5.17-2` 的已安装产物中实际出现
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  - `docs/workflows/新项目开发工作流/commands/session-start-patch-strong-gate.md`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
  - command: `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py WorkflowInstallerTests.test_install_session_start_patch_removes_legacy_tail_logic`
- Validation Action:
  - 对比目标项目已安装 `session-start.py`，确认补丁块后仍保留旧 `Status: READY` 尾逻辑
  - 修改补丁生成策略后，重跑安装器编译与尾逻辑移除测试
- Impact Scope:
  - `.claude/hooks/session-start.py`
  - 使用该补丁脚本的后续嵌入/升级路径
- Suggested Fix Direction:
  - 将补丁改成替换 legacy tail routing，而不是前插一个总是 return 的补丁块
  - 文档明确禁止保留不可达旧尾逻辑

### [P2] brainstorm 文档与脚本对出口快照字段门禁语义漂移
- Conclusion: 文档原本声称出口快照字段“不由 `workflow-state.py` 单独逐字段强校验”，但脚本实际上已强校验字段存在性；修复 L0 硬门禁后，`complexity_decision` 还进一步承担了脚本级分流门禁，因此原表述已不成立
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/brainstorm.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- Validation Action:
  - 逐行对比文档说明与 `validate_brainstorm_exit_gate()` 的字段检查行为
  - 在实现调整后同步修正文档语义
- Impact Scope:
  - 维护者理解门禁边界
  - 安装后 `brainstorm` 阶段执行预期
- Suggested Fix Direction:
  - 文档明确区分“字段存在性硬门禁”与“除 `complexity_decision` 外其余字段目前主要用于结构留痕/人工复核”

## Unconfirmed Items / False Alarms

- “命令面没有完全绑定状态机” 这条候选项并非纯状态机缺口。状态机层已正确封住 `finish-work -> record-session`，真实问题主要在命令文档和自然语言路由层未完全封口；因此归类为已确认的交互层缺口，而不是新的状态机 bug

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

None currently.

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: `session-start` / `inject-workflow-state` / `/trellis:*` command载体
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`、`.claude/commands/trellis/*.md`
- Agreement / discrepancy: 一致性已恢复；`session-start` 死代码补丁缺口已修复
- Expected carrier model: `session-start` 与 `inject-workflow-state` 共同承载强门禁路由提示
- Does the current implementation match: yes
- If not, what is wrong: n/a

### OpenCode
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: `.opencode/lib/session-utils.js` 与命令文档
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js`
- Agreement / discrepancy: 与本轮修复范围一致；本次未发现额外 OpenCode 专属偏差
- Expected carrier model: route-centered session utils + 分发命令文档
- Does the current implementation match: yes
- If not, what is wrong: n/a

### Codex
- Official docs checked: not-applicable in this round
- Repo-local evidence checked: `.agents/skills/*`、`.codex/hooks/inject-workflow-state.py`、AGENTS 路由表生成逻辑
- Practical development-use evidence checked: `/tmp/trellis-0.5.17-2/.agents/skills/record-session/SKILL.md`、`.codex/hooks/session-start.py`
- Agreement / discrepancy: Codex 仍把 `session-start.py` 视为可选辅助面，符合当前合同；NL 路由表中“记录、保存进度”已与 `命令映射.md` 对齐到 `finish-work`
- Expected carrier model: `.agents/skills/` 为主，`.codex/hooks/*` 为辅
- Does the current implementation match: yes
- If not, what is wrong: n/a

## Suggested Fix Directions

- 已完成：在 `workflow-state.py` 中补齐 `brainstorm -> execution` 的 `L0` 硬门禁、`record-session` 的 validate 覆盖、以及 keyed degraded fallback 优先级
- 已完成：将 `patch-session-start-strong-gate.py` 改为真正替换 legacy tail routing，消除已安装 carrier 中的不可达旧逻辑
- 已完成：同步 `brainstorm.md`、`record-session.md`、`delivery.md`、`session-start-patch-strong-gate.md` 与安装器 NL 路由表
- 保留说明：degraded fallback 的多会话串线风险已通过 keyed fallback 明显缓释，但在完全缺失稳定会话标识时，shared fallback 仍作为兼容兜底存在，风险是“降低”而不是“理论归零”

## Propagation Scope and Synchronized Update Range

- `commands/*.md`
- `commands/shell/*.py`
- `commands/install-workflow.py`
- `commands/*test*.py`
- `/tmp/trellis-0.5.17-2` 仅作为证据对象，未直接修改

## Recommended Next Step

- Recommended action: proceed to manual spot-check in a fresh `/tmp` embed fixture when convenient, then commit
- Trigger condition: source-level regression tests and installer regression tests are green
- Recommendation reason: 当前证据已足以证明修复成立；下一步价值最高的是再做一次 fresh embed 抽查，而不是继续扩大源码改动面
- Stronger alternatives not selected: 未再扩大到更多无关安装/升级套件，因为本轮问题已由对应源码层与直接回归测试覆盖

## Stop Point and Pending Confirmations

- Auto-continue allowed: No
- User confirmation required for:
  - 是否需要我再额外基于一个全新 `/tmp` 目标项目做一次人工 spot-check

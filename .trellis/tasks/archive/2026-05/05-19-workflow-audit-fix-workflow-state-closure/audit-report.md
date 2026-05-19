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
  - repair 在执行阶段不可用且恢复链路有损
  - route 对阶段内结构性失效检查不足，存在带病重入
  - 状态机缺少成型自动化回归测试
  - 语义复制过多且安装校验 fail-closed 维护成本高
  - degraded fallback 与 active-task 解析分叉
  - legacy 机制未真正退出关键路径
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and extracted `COMPATIBLE_TRELLIS_VERSION = 0.5.17` — Layer: `source repo`
- Ran `trellis -v` and confirmed `0.5.17` — Layer: `runtime command output`
- Read `workflow-audit` skill/spec and selected task-based runtime mode because the user explicitly requested `/tmp` validation — Layer: `source repo`
- Read `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`, `install-workflow.py`, `upgrade-compat.py`, patch docs, and bundled regression tests to compare the declared repair/degraded contracts against actual source behavior — Layer: `source repo`
- Inspected `/tmp/trellis-0.5.17-2` and confirmed it is a valid post-install target-project sample with installed workflow assets but no active runtime task state yet — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Created an isolated copy `/tmp/trellis-0.5.17-2-repro-repair` and reproduced execution-stage `workflow-state.py repair` behavior plus degraded active-task divergence there — Layer: `runtime command output`
- Ran `/ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.shell.test_workflow_state` and `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` after the source fixes — Layer: `runtime command output`

## Confirmed Issues

### [P1] `workflow-state.py repair` 对执行阶段恢复链路不闭合，且会有损抹掉可恢复确认语义
- Conclusion: 旧版 `repair` 在 `implementation` / `test-first` 阶段默认重建出非法状态，导致官方恢复入口对执行态直接 `repair_blocked`；即便原 state 里仍保留了有效的 `execution_authorized` 与 `last_confirmed_transition`，旧逻辑也会把它们抹掉。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py` 旧逻辑用 `build_default_state()` 直接重建，默认 `execution_authorized=false`、`last_confirmed_transition=null`，随后再用 `validate_execution_boundary()` 拒绝执行态。
  - Layer: `runtime command output`
  - Stage: `workflow-installed state after install-workflow.py`
  - 在 `/tmp/trellis-0.5.17-2-repro-repair` 上运行 `workflow-state.py repair ... --stage implementation`，得到 `repair_blocked`，blockers 为缺少 `checkpoints.execution_authorized=true` 和 `last_confirmed_transition`。
- Validation Action:
  - 用 `/tmp` 已嵌入样本副本创建最小任务。
  - 分别测试 `--stage plan` 与 `--stage implementation`。
  - 再构造“执行阶段旧确认字段仍在，但 state 其余内容不合法”的样本验证旧逻辑会有损恢复。
- Impact Scope:
  - `workflow-state.py repair`
  - 所有安装后目标项目的执行阶段恢复路径
  - `/trellis:continue` / `trellis-continue` 遇到 `repair_needed` 时的官方建议链路
- Suggested Fix Direction:
  - 允许 `repair` 接收与 `set` 对齐的显式确认参数
  - 对执行阶段保留合法且与目标 stage 匹配的确认字段；其余语义维持保守重建
  - 文档同步说明执行态恢复需要 `--execution-authorized true` 与 `--transition-from <previous-stage>`

### [P1] degraded fallback 的 `task.py current --source` 路径在已安装目标项目里确实是死分支
- Conclusion: 当前工作流源的安装器模板会向目标项目写入一个逻辑有误的 degraded current-read 补丁；在无可用 session current_task、但存在 `.trellis/.runtime/degraded-active-task.json` 的场景下，`task.py current` 可返回 degraded task，而 `task.py current --source` 会提前输出 `(none)` 并返回 1，形成自相矛盾的恢复信号。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` 中，`args.source` 分支在任何 degraded fallback 检查前就已返回。
  - Layer: `runtime command output`
  - Stage: `workflow-installed state after install-workflow.py`
  - 在 `/tmp/trellis-0.5.17-2-repro-repair` 中保留空 session 文件并写入 `degraded-active-task.json` 后：
    - `task.py current` 返回 degraded task
    - `task.py current --source` 返回 `Current task: (none)` / `Source: none`
  - Layer: `source repo`
  - Stage: `n/a`
  - 同一错误逻辑存在于 `docs/workflows/新项目开发工作流/commands/install-workflow.py` 的 `patch_task_start_degraded_fallback()` 模板中，会持续生成错误补丁。
- Validation Action:
  - 检查 `/tmp` 已安装目标项目内实际落盘的 `task.py`
  - 用最小复现目录分别执行 `current` 与 `current --source` 对比行为
  - 回溯到安装器源码确认模板同样错误
- Impact Scope:
  - 所有通过该工作流安装器嵌入后的目标项目
  - degraded 恢复场景下的诊断输出与人工恢复判断
  - `upgrade-compat.py --check` 对 patch presence 的表面通过无法发现该逻辑错误
- Suggested Fix Direction:
  - 在安装器模板中把 degraded fallback 读取移入 `args.source` 分支内，避免提前返回
  - 增加 installer 回归测试，校验补丁后 `task.py` 文本形态不再保留死分支结构

### [P2] “没有自动化回归测试”的候选问题已不成立，但执行态 repair / degraded current-read 的关键回归此前确实缺失
- Conclusion: 当前工作流目录并非没有测试；`test_workflow_state.py` 与 `test_workflow_installers.py` 已承载较大面积回归。但用户列举的两类真实问题之所以反复出现，是因为现有测试没有覆盖这些具体坏路径。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - 存在 `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - 存在 `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - 原测试覆盖了 degraded fallback presence、repair 基础行为、route 阻塞逻辑，但未覆盖“执行态 repair 需显式恢复确认字段”与“`current --source` degraded 死分支”
- Validation Action:
  - 枚举工作流目录下的测试文件
  - 搜索并阅读相关测试用例
  - 补新增量回归后重新执行两套核心测试
- Impact Scope:
  - 审计结论层面：候选问题 3 需要改判为“测试盲区”而非“无测试”
  - 维护层面：需要继续以 targeted regression 的方式补足高风险恢复路径
- Suggested Fix Direction:
  - 保留现有测试体系判断
  - 在缺口点新增精确回归，而不是泛泛增加一个新测试目录

## Unconfirmed Items / False Alarms

- 候选问题 2（“路由器只在离开阶段时严查多数产物，平时允许带病重入”） -> `部分过时 / 需精确改判`
  - 当前源版本里，`route` 已在阶段内部对 `plan`、执行态、以及所有 `awaiting_user_confirmation` 退出口执行相当数量的 blocker 检查；对应测试覆盖了 README、Context7 review、finish-work checklist、delivery validators、project-audit、review-gate 等多个门禁。
  - 它不再是“只到离开阶段才暴露”的旧状态，因此不能按原说法直接判真。
- 候选问题 4（“语义复制过多且安装校验 fail-closed 维护代价偏高”） -> `真实风险存在，但本轮未作为明确 defect 直接修复`
  - 当前确有多载体同步和 fail-closed 检查；这是设计上的维护成本，不自动等于 defect。
  - 本轮已顺手修复其中一个真实传播故障点：installer 模板自身携带了错误 degraded current-read 逻辑。
- 候选问题 6（“旧机制未真正退出关键路径”） -> `部分成立，但不是本轮最直接的运行闭环故障`
  - `task.py start` 中 `task.json.status` 的 legacy bookkeeping 仍存在，不过在强门禁安装下已通过 patch 显式跳过有 `workflow-state.json` 的状态翻转。
  - `workflow_phase.py` 的 legacy step lookup 也仍保留兼容壳，但已有强门禁补丁与回归测试防止在存在 strong-gate state 时继续走旧路径。

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)

- 候选问题 5 的另一半（`route` 在“存在其他 session current_task”时是否过度保守忽略 degraded fallback）本轮未进一步变更。
  - Type: `Evidence Gap`
  - Cause: 现有行为与代码注释一致，属于显式的“多窗口不猜测”策略；要把它升级为 defect 需要额外的误恢复案例，而不仅是行为分叉本身。
  - Impact: 在多 session 脏 runtime 场景下，恢复可能偏保守，需要人工重新 `task.py start`
  - What is needed to continue: 更多目标项目级误导性恢复案例，或产品上明确改变“多窗口时拒绝猜测”的策略

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: not-applicable in this round; this audit focused on workflow-state recovery semantics, not upstream Claude capability drift
- Repo-local evidence checked: yes — installer/upgrade scripts, patch docs, and `/tmp/.claude/hooks/*`
- Practical development-use evidence checked: yes — `/tmp/trellis-0.5.17-2` installed artifact shape
- Agreement / discrepancy: no new CLI-specific discrepancy confirmed in this round
- Expected carrier model: SessionStart + inject hook should surface route-centered state rather than legacy status routing
- Does the current implementation match: yes for inspected surfaces
- If not, what is wrong: none confirmed in this round

### OpenCode
- Official docs checked: not-applicable in this round; this audit focused on workflow-state recovery semantics, not upstream OpenCode capability drift
- Repo-local evidence checked: yes — installer/upgrade scripts and target-project installed carriers
- Practical development-use evidence checked: yes — `/tmp/trellis-0.5.17-2/.opencode/**`
- Agreement / discrepancy: no new CLI-specific discrepancy confirmed in this round
- Expected carrier model: plugin/session-utils should consume route-centered workflow-state output
- Does the current implementation match: yes for inspected managed surfaces
- If not, what is wrong: none confirmed in this round

### Codex
- Official docs checked: not-applicable in this round; this audit focused on installed workflow-source behavior rather than latest upstream Codex docs
- Repo-local evidence checked: yes — installer patches, `task.py` degraded fallback template, route-centered hook contract, target-project installed `.codex/`/`.agents/skills/`
- Practical development-use evidence checked: yes — `/tmp/trellis-0.5.17-2` and the isolated reproduction copy
- Agreement / discrepancy: confirmed discrepancy existed in degraded `task.py current --source`; now fixed in workflow source
- Expected carrier model: Codex route/hook surfaces can remain route-centered while formal embed execution itself stays outside Codex
- Does the current implementation match: yes after the source fix for degraded current-read template
- If not, what is wrong: already installed older targets may still carry the dead degraded-source branch until they are re-embedded or repaired

## Suggested Fix Directions

- Keep `workflow-state.py repair` conservative about stage inference, but allow explicit reconstruction of execution-stage confirmation fields and preserve valid existing execution confirmation where possible
- Keep degraded fallback as a last-resort strategy, but make `task.py current --source` report it consistently instead of contradicting `task.py current`
- Continue using targeted regression additions inside the existing workflow test suite rather than inventing a parallel test framework

## Propagation Scope and Synchronized Update Range
- Updated layers in this round:
  - workflow helper script: `commands/shell/workflow-state.py`
  - installer template logic: `commands/install-workflow.py`
  - workflow regression tests: `commands/shell/test_workflow_state.py`, `commands/test_workflow_installers.py`
  - route/maintainer docs: `commands/start-patch-phase-router.md`, `commands/start-skill-patch-phase-router.md`, `commands/trellis-meta-strong-gate/customize-local/change-workflow.md`
- Propagation risk notes:
  - `repair` semantics are referenced by both command-facing route docs and maintainer-facing architecture notes
  - `task.py` degraded fallback behavior is generated from installer template code, so fixing only an installed target project would not be sufficient

## Recommended Next Step
- Recommended action: complete the close-out pass for this audit task, including spec-update judgment and commit plan
- Trigger condition: confirmed defects have been fixed in workflow source and both core regression suites now pass
- Recommendation reason: the highest-signal runtime defects identified in this round are already closed with test evidence
- Stronger alternatives not selected: broad refactoring of legacy bookkeeping / multi-session degraded strategy would expand scope beyond the confirmed breakages repaired here

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - whether to把剩余“legacy complexity / multi-session degraded conservatism”作为后续维护任务单独处理，而不是继续扩大本轮修复范围

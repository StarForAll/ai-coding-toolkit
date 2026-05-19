# Audit Report: docs/workflows/新项目开发工作流

## Audit Boundary

- Workflow Path: `docs/workflows/新项目开发工作流/`
- Generated Target Project: `/tmp/trellis-0.5.17-2`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Current CLI: `codex`

## Candidate Issues

1. `implementation` stage 缺少对称入口
2. `blocked` / `repair_needed` / `awaiting_confirmation_with_blockers` 缺少一等 breadcrumb 模板
3. `workflow-state.json` 不是唯一真相，`task.json.status` 仍是隐性前提
4. 工作流单源配置已经演变成分布式契约
5. 状态解析路径过度依赖子进程调用
6. 自动化回归验证缺位

## Initial Evidence Notes

- `generated target project / workflow-installed state`
  - `.trellis/workflow-installed.json` 的 `commands` 不包含 `implementation`
  - `.agents/skills/trellis-start/SKILL.md` 与 `.agents/skills/trellis-continue/SKILL.md` 均包含 “use the skill matching the target field” 语句
  - `.codex/hooks/inject-workflow-state.py` 与 `.opencode/plugins/inject-workflow-state.js` 均先取 `route.stage` 作为 `status`
  - `.trellis/workflow.md` 不存在 `[workflow-state:blocked]`、`[workflow-state:repair_needed]`、`[workflow-state:awaiting_confirmation_with_blockers]` 块
- `source repo`
  - 已存在针对 `workflow-state.py route` 的 hook 补丁和强门禁测试，但本次候选问题仍需核实是否落地完整

## Findings In Progress

### Confirmed Issues

1. `implementation` 的公开重入契约存在真实歧义，已修复
   - `generated target project / workflow-installed state`
     - `.agents/skills/trellis-start/SKILL.md`
     - `.agents/skills/trellis-continue/SKILL.md`
     - `.trellis/workflow.md`
     - `.trellis/workflow-installed.json`
   - Validation action:
     - 检查安装后 `commands` / `.agents/skills/` / `.trellis/workflow.md` 的入口映射，确认 `implementation` 是正式 stage，但 Phase Router 文案仍写成“use the skill matching the target field”，而 `.trellis/workflow-installed.json.commands` 没有 `implementation`
   - Conclusion:
     - 缺陷不是“缺少 stage 资产”，而是“缺少明确的公开入口契约”。当前设计实际由 `/trellis:continue` 重入 implementation，但目标项目安装后的入口文案与 AGENTS 路由表没有把这一点说清楚。
   - Fix:
     - 在 `start-patch-phase-router.md`、`start-skill-patch-phase-router.md`、`workflow-patch-projectization.md`、`install-workflow.py` 的 NL routing section 中显式声明 implementation 通过 `/trellis:continue` / `trellis-continue` 重入，不存在对称的 `/trellis:implementation`

2. 阻塞态 / 修复态 breadcrumb 正文会被普通 stage 模板吞掉，已修复
   - `generated target project / workflow-installed state`
     - `.codex/hooks/inject-workflow-state.py`
     - `.opencode/plugins/inject-workflow-state.js`
     - `.trellis/workflow.md`
   - Validation action:
     - 检查 hook 已安装代码，确认其在存在 `route.stage` 时优先用 stage 作为 `status`
     - 检查 `.trellis/workflow.md`，确认缺少 `[workflow-state:blocked]`、`[workflow-state:repair_needed]`、`[workflow-state:awaiting_confirmation_with_blockers]` 等动作态 block
   - Conclusion:
     - 这是实质性缺陷。header 会显示 Action/Blockers，但正文仍继续发 stage 指令，造成冲突信号。
   - Fix:
     - 在 `workflow-patch-projectization.md` 增加 `blocked`、`awaiting_confirmation`、`awaiting_confirmation_with_blockers`、`context_needed`、`recovery_needed`、`repair_needed`、`embed_invalid`、`workflow-state.route_failed` 的专用 breadcrumb blocks
     - 在 hook patch 中改为 action-first template 选择；若是动作态，则 header 里保留 `Stage:` 仅作上下文

3. per-turn hook 对 `task.json.status` 仍有隐性硬依赖，已修复
   - `generated target project / workflow-installed state`
     - `.codex/hooks/inject-workflow-state.py`
     - `.opencode/plugins/inject-workflow-state.js`
   - Validation action:
     - 检查安装后 hook 代码，确认旧逻辑会在 `task.json.status` 为空时提前 `return null` / `return None`，从而根本不执行后续 `workflow-state.py route`
   - Conclusion:
     - 这是实质性缺陷。即便 `workflow-state.json` 与 route 层仍可提供当前阶段，hook 也会因为 bookkeeping 字段为空而放弃强门禁路由。
   - Fix:
     - hook patch 改成以 `task.json` 仅作为可选 ID / fallback 来源；即便缺少 `status`，也继续尝试 route

4. Python 热路径对子进程的依赖过重，已做低风险削减
   - `source repo`
     - `commands/shell/patch-inject-workflow-state.py`
     - `commands/install-workflow.py`
   - Validation action:
     - 检查 Python hook patch 与 `common/tasks.py` patch，确认旧实现分别用 `subprocess.run(...)` 调 `workflow-state.py route`
   - Conclusion:
     - 这是实质性维护/性能问题，尤其是任务列表视图会对每个 task 起一次子进程。JS carrier 仍受平台约束需要 `execFileSync`，但 Python 热路径可以改进。
   - Fix:
     - Python hook patch 改为进程内加载 `workflow-state.py` 并调用 `cmd_route`
     - `common/tasks.py` 的 `route-aware` 状态摘要改为进程内加载 route helper，消除每 task 一次 `subprocess.run`

5. 本轮真实缺陷已补自动化回归断言，避免再回归
   - `source repo`
     - `commands/test_workflow_installers.py`
   - Validation action:
     - 增加对 implementation 入口文案、动作态 blocks、hook 不再依赖空 `task.json.status`、Python 任务视图不再 `subprocess.run` 的断言

6. Codex `finish-work` 路由仍有一个名称不对称残留，已修复
   - `generated target project / workflow-installed state`
     - `.agents/skills/trellis-finish-work/SKILL.md`
     - `.agents/skills/trellis-continue/SKILL.md`
   - Validation action:
     - 对照 `workflow-state.py` 的 `target=finish-work` 与目标项目 `.agents/skills/` 的实际 skill 名，确认公开 skill 是 `trellis-finish-work` 而不是 `finish-work`
     - 复查 `commands/start-skill-patch-phase-router.md`，确认 `reenter` 分支此前仍把非 implementation 统一表述为 “use the skill matching the target field”
   - Conclusion:
     - 这是上轮修复后仍残留的真实缺陷。对 Codex 而言，`finish-work` 不是同名 skill，Phase Router 需要显式特判。
   - Fix:
     - 在 `start-skill-patch-phase-router.md` 中加入 `target=finish-work -> trellis-finish-work` 的明确映射
     - 在 `commands/test_workflow_installers.py` 中新增对应断言

### False Alarms / Non-Defects In Current Version

1. “完全没有自动化回归验证”不成立
   - `source repo`
     - `commands/test_workflow_installers.py`
     - `commands/shell/test_workflow_state.py`
   - Conclusion:
     - 当前版本已经存在成体系测试。问题不在“零测试”，而在本轮缺陷缺少对应断言，现已补上。

2. `task.py start` 仍执行 legacy `planning -> in_progress` flip，不成立于工作流安装后的目标项目
   - `generated target project / workflow-installed state`
     - `.trellis/scripts/task.py`
   - Conclusion:
     - 安装后目标项目已通过 `patch-task-start-strong-gate.py` 跳过该 flip。当前源仓库自己的 `.trellis/scripts/task.py` 仍会 flip，但那不在本次工作流目标项目审计范围内。

3. “implementation 完全没有入口”表述过度
   - Conclusion:
     - 当前版本真实问题是“入口契约不明确”，不是完全没有入口。`/trellis:continue` 一直是 implementation 的实际公开重入点，只是安装后文案与自然语言路由没有把这一点说清楚。

## Verification

- `source repo`
  - `cd docs/workflows/新项目开发工作流/commands && /ops/softwares/python/bin/python3 -m unittest test_workflow_installers.py`
  - Result: pass (`Ran 116 tests in 223.660s`)
- `source repo`
  - `cd docs/workflows/新项目开发工作流/commands/shell && /ops/softwares/python/bin/python3 -m unittest test_workflow_state.py`
  - Result: pass (`Ran 114 tests in 17.029s`)
- `source repo`
  - `/ops/softwares/python/bin/python3 -m py_compile docs/workflows/新项目开发工作流/commands/install-workflow.py docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  - Result: pass

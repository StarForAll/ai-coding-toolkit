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
  - Codex / OpenCode per-turn 注入仅消费 `stage`，未消费 `action / stage_status / blockers`
  - Claude SessionStart 在缺失 `workflow-state.json` 时回退为 `ACTIVE`
  - `trellis-start` / `trellis-continue` 未消费 `context_needed`
  - 平台主链仍残留显式例外与 stage-centered breadcrumb
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and extracted `COMPATIBLE_TRELLIS_VERSION=0.5.17` — Layer: `source repo`
- Ran `trellis -v` and confirmed `0.5.17` — Layer: `runtime command output`
- Read `.trellis/spec/skills/workflow-audit.md` and `.agents/skills/workflow-audit/SKILL.md` to bind same-version audit contract and task-based runtime path — Layer: `source repo`
- Used `ace.search_context` to locate workflow route, hook patch, and skill-consumption code paths — Layer: `source repo`
- Read installed target-project carriers under `/tmp/trellis-0.5.17-2` (`.claude/hooks/session-start.py`, `.claude/hooks/inject-workflow-state.py`, `.opencode/plugins/inject-workflow-state.js`, `.agents/skills/trellis-start/SKILL.md`, `.agents/skills/trellis-continue/SKILL.md`) — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Ran `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` — Layer: `runtime command output`
- Ran `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers` — Layer: `runtime command output`

## Confirmed Issues

### [P1] Codex / Claude / OpenCode per-turn breadcrumb 仅暴露阶段名，丢失 route 强门禁信息
- Conclusion: 工作流源码中的 `patch-inject-workflow-state.py` 和安装器检查逻辑仍以 `workflow-state.json.stage` 为主要补丁目标，导致 `blocked`、`awaiting_confirmation_with_blockers`、`repair_needed`、`context_needed` 等正式路由结果在 per-turn 注入中被降维成普通阶段名。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/inject-workflow-state.py`
  - `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-workflow-state.js`
  - Validation command: `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers`
- Validation Action:
  - 对照 route 输出契约与安装后 hook 真实内容，确认 header 只使用 stage / status
  - 将补丁链升级为 route-centered，并用安装器测试验证部署和装后自检恢复通过
- Impact Scope:
  - Codex `.codex/hooks/inject-workflow-state.py`
  - Claude `.claude/hooks/inject-workflow-state.py`
  - OpenCode `.opencode/plugins/inject-workflow-state.js`
  - 安装器、升级检查、自测夹具与 trellis-meta 参考文档
- Suggested Fix Direction:
  - 统一改为“用 `workflow-state.py route` 决定 header 元数据，stage 只决定模板 body”

### [P1] Claude SessionStart 在状态缺失/损坏时会把 repair 分支隐藏成 ACTIVE
- Conclusion: 安装后目标项目的 `.claude/hooks/session-start.py` 只有在 `workflow-state.json` 存在且 stage 合法时才调用 `workflow-state.py route`，否则直接返回 `ACTIVE`，与权威路由器的 `repair_needed` 契约冲突。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-session-start-strong-gate.py`
  - `docs/workflows/新项目开发工作流/commands/session-start-patch-strong-gate.md`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
  - Validation command: `PYTHONPATH=docs/workflows/新项目开发工作流/commands /ops/softwares/python/bin/python3 -m unittest docs.workflows.新项目开发工作流.commands.test_workflow_installers`
- Validation Action:
  - 读取安装后 hook，确认其注释和执行逻辑都把“无 `workflow-state.json`”定义成 `ACTIVE`
  - 将补丁升级为 route-first，允许 `route` 在状态缺失时直接返回 `repair_needed`
- Impact Scope:
  - Claude session-start carrier
  - 相关安装器、升级检查与补丁说明文档
- Suggested Fix Direction:
  - SessionStart 只在 route helper 不可用或 route 输出非法时才回退到 `ACTIVE`

### [P2] start / continue 入口协议缺少 `context_needed` 消费分支
- Conclusion: 工作流路由器已能返回 `context_needed`，但入口层 Phase Router 文档没有把该 action 纳入消费表，导致“父任务含 children 不能直接执行”这类状态没有统一承接语义。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-start/SKILL.md`
  - `/tmp/trellis-0.5.17-2/.agents/skills/trellis-continue/SKILL.md`
- Validation Action:
  - 对照 router 输出和入口路由表，确认已存在的 installed skill 未列出 `context_needed`
  - 将两个入口补丁文案同步加入 `context_needed`
- Impact Scope:
  - Codex 共享 skill 入口
  - Claude / OpenCode continue/start 路由说明
- Suggested Fix Direction:
  - 保持 `context_needed` 为显式路由动作，并要求切换到子任务后再继续

## Unconfirmed Items / False Alarms
- “平台主链仍未统一，Codex 对 `trellis-research` 保留显式例外” 不按 confirmed issue 处理：当前证据更支持它是 `codex.dispatch_mode = inline` 下的设计边界，而不是本工作流安装后的运行缺陷。
- “Claude session-start.py 仍保留旧 PLANNING/READY 残影” 作为代码味道存在，但在本轮 route-first patch 后旧分支已被明确旁路，不单独升级为新问题。

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- 暂无硬阻塞；本轮已用现有 `/tmp/trellis-0.5.17-2` 和源码回归测试完成验证。

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked: `not-applicable`
- Repo-local evidence checked: `session-start.py`, `inject-workflow-state.py`, installer patch docs, upgrade-compat checks
- Practical development-use evidence checked: installed target-project `.claude/hooks/*` carriers
- Agreement / discrepancy: `已确认 discrepancy`
- Expected carrier model: `session-start 可选，但若存在强门禁补丁则必须尊重 route；per-turn hook 不能只显示 stage`
- Does the current implementation match: `已修复后匹配`
- If not, what is wrong: `修复前会把 repair_needed 隐藏成 ACTIVE，并把 blocked/awaiting blockers 降级成阶段 breadcrumb`

### OpenCode
- Official docs checked: `not-applicable`
- Repo-local evidence checked: `.opencode/plugins/inject-workflow-state.js`, `.opencode/lib/session-utils.js`, installer patch logic
- Practical development-use evidence checked: installed target-project `.opencode/plugins/inject-workflow-state.js`
- Agreement / discrepancy: `已确认 discrepancy`
- Expected carrier model: `plugin/header 应显式展示 route metadata`
- Does the current implementation match: `已修复后匹配`
- If not, what is wrong: `修复前 plugin 只把 workflow-state.json.stage 注入为 status`

### Codex
- Official docs checked: `not-applicable`
- Repo-local evidence checked: `.codex/hooks/inject-workflow-state.py`, `.agents/skills/trellis-start`, `.agents/skills/trellis-continue`, `commands/codex/README.md`
- Practical development-use evidence checked: installed target-project `.codex/hooks/inject-workflow-state.py` and `.agents/skills/*`
- Agreement / discrepancy: `已确认 discrepancy`
- Expected carrier model: `Codex 主要依赖 per-turn hook + shared skills；hook header 不能旁路 route`
- Does the current implementation match: `已修复后匹配`
- If not, what is wrong: `修复前 hook 只暴露 stage，入口表缺少 context_needed`

## Suggested Fix Directions
- 将 per-turn breadcrumb 补丁从 `stage-centered` 升级为 `route-centered`
- 将 Claude SessionStart 升级为 `route-first`，仅在 route helper 不可用时回退
- 同步更新安装器、升级检查、回归测试和 trellis-meta 参考文档，避免新 drift

## Propagation Scope and Synchronized Update Range
- 已涉及 `commands/shell/*.py`、`commands/*.md`、工作流说明文档、`commands/test_workflow_installers.py`、`commands/shell/test_workflow_state.py`
- 风险点：若后续只改 hook patch 而不改安装器/upgrade-compat/trellis-meta 文档，会重新形成 route 契约漂移

## Recommended Next Step
- Recommended action: `trellis-check`
- Trigger condition: 代码修改与回归测试已完成，需要做最终质量核对和 close-out 判断
- Recommendation reason: 当前问题已完成修复与验证，下一步应进入仓库标准质量关口
- Stronger alternatives not selected: 不需要再继续扩大修复范围到工作流外目录

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - 是否继续进入本仓库收尾步骤（spec update / commit 计划）

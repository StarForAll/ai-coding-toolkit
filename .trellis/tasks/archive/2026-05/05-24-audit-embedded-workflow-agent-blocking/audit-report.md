# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`
- Bypass Detail: `none`
- Audit Scope: `task-based static`
- Current CLI: `codex`
- Candidate Issues:
  - 嵌入后不适合使用 agents/subagents，需要显式阻断 Claude Code / OpenCode / Codex 使用
  - 需要判断是否存在同类漏口并一并修复
- Generated Target Project Root: `/tmp/trellis-0.5.17-2`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py` — Layer: `source repo`
- Ran `trellis -v` and confirmed `0.5.17` — Layer: `runtime command output`
- Compared source docs / installer templates / patch helpers with `/tmp/trellis-0.5.17-2` installed artifacts — Layer: `source repo`
- Read `/tmp/trellis-0.5.17-2/AGENTS.md`, `.claude/settings.json`, `.claude/hooks/session-start.py`, `.opencode/lib/session-utils.js`, `.opencode/plugins/inject-subagent-context.js`, `.codex/hooks.json`, `.codex/hooks/inject-workflow-state.py`, `.trellis/config.yaml` — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- Checked official product docs for Codex, OpenCode, Claude Code agent/subagent/hook/AGENTS capabilities — Layer: `runtime command output`

## Confirmed Issues

### [P1] Claude / OpenCode 活跃 startup carrier 仍默认要求派发子代理
- Conclusion: 嵌入后的目标项目在活跃 startup carrier 上仍把 `trellis-implement` / `trellis-check` 作为默认执行路径，与“该 workflow 不适合使用 agents/subagents”这一目标相冲突。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.claude/settings.json:5-70` 明确接线 `SessionStart -> .claude/hooks/session-start.py`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py:726-737` 明确写着默认 dispatch `trellis-implement` / `trellis-check`
  - `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js:260-265` 明确写着 “do NOT edit code directly in the main session; dispatch `trellis-implement` and `trellis-check`”
- Validation Action:
  - 读取目标项目已落盘 runtime carrier，并核对这些文件是否处于已接线/活跃路径
- Impact Scope:
  - `Claude Code`
  - `OpenCode`
  - implementation 内部链路的默认执行模型
- Suggested Fix Direction:
  - 在 workflow 安装器补丁层把这些 startup guidance 改成“必须回到 main session，不得默认派发 subagent”

### [P1] OpenCode 子代理注入补丁是“条件放行”，不是“工作流级禁用”
- Conclusion: 当前 workflow 对 OpenCode 做的是阶段门禁式放行，不是显式阻断；这与用户要求的产品行为不一致。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/shell/patch-opencode-inject-subagent-context.py:35-57` 的 `shouldAllowTaskInjection()` 会在若干阶段返回允许
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md:286-289` 明确说明该补丁只是在 route 允许阶段注入 implement/check
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-subagent-context.js:47-69` 与 `:559-561` 保留了允许阶段的注入逻辑
- Validation Action:
  - 对照 source-side patch helper 与目标项目落盘 JS，确认运行时行为确实是“条件放行”
- Impact Scope:
  - `OpenCode`
  - `inject-subagent-context.js`
  - `critical_runtime_patches` 合同
- Suggested Fix Direction:
  - 把 OpenCode 子代理补丁从“按阶段允许”改为“对当前嵌入 workflow 统一阻断并回退主会话”

### [P1] 安装器生成路由和多份源文档仍把 agent/subagent 当成兼容/内部路径保留
- Conclusion: 当前 workflow 的 source docs 与生成 AGENTS 路由存在一致性漂移: 文案虽说“不建议”，但仍持续保留 agent/subagent 的显式入口或内部默认链，无法形成明确阻断。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py:303-331` 生成的 AGENTS 路由只做弱提醒；Codex 行仍允许显式触发 `trellis-research` skill / agent
  - `docs/workflows/新项目开发工作流/commands/check.md:42-44` 仍声明 implementation 阶段默认允许 Trellis agent 链
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md:620` 仍声明 `continue` 默认先执行 Trellis agent 链
  - `docs/workflows/新项目开发工作流/命令映射.md:41-46,623` 仍把 Codex 描述成 `skills/agents` 模型，并保留内部 agent 链
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md:201-205,288-289` 仍只说“不建议手工派发”
  - `docs/workflows/新项目开发工作流/commands/codex/README.md:268-343` 仍保留 `subagents` / 内部角色链叙述
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/AGENTS.md:30-35,58` 目标项目实际落盘的路由表延续了同样口径
- Validation Action:
  - source docs 搜索 `agent/subagent/dispatch/trellis-implement/trellis-check`
  - 对照目标项目 AGENTS 落盘结果确认不是 source-only 死文档
- Impact Scope:
  - 安装器模板
  - 目标项目 `AGENTS.md`
  - 多份 workflow 文档
- Suggested Fix Direction:
  - 统一把“兼容承载面/不建议”升级为“当前嵌入 workflow 禁止使用 agent/subagent 路径，必须回到 main session / 阶段入口”

### [P2] Codex 活跃 hook 仍保留 `sub-agent` 模式入口，未形成 workflow 级硬收口
- Conclusion: 尽管 fresh install 默认仍是 `inline`，但当前 workflow 的 Codex 活跃 hook 与文档仍允许通过 `codex.dispatch_mode = sub-agent` 进入子代理模式，不符合“该嵌入 workflow 不适合使用 subagent”的目标。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `/tmp/trellis-0.5.17-2/.codex/hooks.json:2-14` 表明活跃 hook 是 `inject-workflow-state.py`
  - `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py:355-381` 明确支持 `codex.dispatch_mode` 在 `inline/sub-agent` 间切换
  - `/tmp/trellis-0.5.17-2/.trellis/config.yaml:82-90` 注释文本继续把 `sub-agent` 作为合法 opt-in 路径
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md:200-203,335-342` 仍按“inline 默认、subagent 兼容”描述
- Validation Action:
  - 确认当前活跃 Codex hook 读取 `dispatch_mode`
  - 确认 fresh install 虽默认 inline，但并未被 workflow 产品层硬性收口
- Impact Scope:
  - `Codex`
  - `.codex/hooks/inject-workflow-state.py`
  - `AGENTS.md` 路由和 Codex 适配文档
- Suggested Fix Direction:
  - 在 workflow 对 Codex 的补丁层把已嵌入项目的 dispatch 语义固定到 main-session-only，并同步修改 AGENTS / 文档说明

## Unconfirmed Items / False Alarms
- “平台本身不支持 agents/subagents/hooks” -> `false alarm`
  - 官方文档显示 Claude Code、OpenCode、Codex 均支持相应能力；本任务的问题是当前 workflow 产品层不该继续暴露/鼓励这些路径。

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- 无当前阻塞项；等待你确认是否进入源码修复。

## Per-CLI Adaptation Conclusions

### Claude Code
- Official docs checked:
  - Anthropic 官方文章 `Customize Claude Code with plugins`（2025-10-09）
- Repo-local evidence checked:
  - `commands/claude/README.md`
  - 安装器与 patch helper
- Practical development-use evidence checked:
  - `/tmp/trellis-0.5.17-2/.claude/settings.json`
  - `/tmp/trellis-0.5.17-2/.claude/hooks/session-start.py`
- Agreement / discrepancy:
  - 官方说明 Claude Code 支持 commands / hooks / agents(subagents)；本 workflow 当前也沿用了这些能力，但与本任务目标要求的“禁用当前 workflow 的 agent/subagent 路径”相冲突
- Expected carrier model:
  - 平台支持该能力；workflow 产品层可选择禁用其作为主路径
- Does the current implementation match:
  - 不匹配当前候选目标
- If not, what is wrong:
  - 活跃 startup carrier 还在默认 dispatch sub-agents

### OpenCode
- Official docs checked:
  - `https://opencode.ai/docs/agents/`
  - `https://opencode.ai/docs/rules/`
- Repo-local evidence checked:
  - `commands/opencode/README.md`
  - `commands/shell/patch-opencode-inject-subagent-context.py`
- Practical development-use evidence checked:
  - `/tmp/trellis-0.5.17-2/.opencode/lib/session-utils.js`
  - `/tmp/trellis-0.5.17-2/.opencode/plugins/inject-subagent-context.js`
- Agreement / discrepancy:
  - 官方说明 OpenCode 原生支持 primary agents/subagents，并支持 `AGENTS.md`；本 workflow 当前只做阶段门禁，没有做 workflow 级禁用
- Expected carrier model:
  - 平台支持 agent/subagent，但 workflow 可以显式禁用其作为产品执行路径
- Does the current implementation match:
  - 不匹配当前候选目标
- If not, what is wrong:
  - startup 与 subagent 注入链都仍在放行/推荐

### Codex
- Official docs checked:
  - `https://developers.openai.com/codex/cli`
  - `https://developers.openai.com/codex/guides/agents-md`
- Repo-local evidence checked:
  - `commands/codex/README.md`
  - `commands/shell/patch-inject-workflow-state.py`
- Practical development-use evidence checked:
  - `/tmp/trellis-0.5.17-2/AGENTS.md`
  - `/tmp/trellis-0.5.17-2/.codex/hooks.json`
  - `/tmp/trellis-0.5.17-2/.codex/hooks/inject-workflow-state.py`
- Agreement / discrepancy:
  - 官方说明 Codex 支持 `AGENTS.md` 和 subagents；当前 workflow 默认 inline，但仍保留 `sub-agent` 模式和弱提醒式兼容口径
- Expected carrier model:
  - 若本 workflow 决定禁用 subagent 路径，应在 hook 与路由层显式收口
- Does the current implementation match:
  - 部分匹配，但不满足“显式阻断”
- If not, what is wrong:
  - 默认 inline 之外仍保留 opt-in 与文档兼容口径

## Suggested Fix Directions
- 把安装器生成的 `AGENTS.md` NL 路由从“弱提醒”改成“显式禁止当前 workflow 使用 agent/subagent 路径”
- 对 Claude / OpenCode / Codex 的活跃 runtime carrier 增加 workflow-side blocking patch，使任何子代理路径都回退主会话
- 清理同类文档漏口，统一去掉“implementation 内部默认 agent 链”“兼容 carrier 可用”这类误导性执行说明
- 补充 installer / upgrade / audit 测试，断言目标项目落盘后会显示阻断而不是条件放行

## Propagation Scope and Synchronized Update Range
- 安装器模板：`commands/install-workflow.py`
- 运行时补丁：`commands/shell/patch-*.py`
- workflow 文档：`commands/*.md`、`commands/*/README.md`、根目录 workflow docs
- 测试：`commands/test_workflow_installers.py` 及相关 patch/helper 测试
- Propagation risk notes:
  - 必须同步改 source docs、生成模板、runtime patch、测试；否则会出现“文档说禁用，运行时仍放行”的回归

## Recommended Next Step
- Recommended action: `plain-language action`
- Trigger condition: 你确认进入源码修复
- Recommendation reason: 证据已经足够，不需要再扩大审计面；下一步应直接在 workflow 源码中实现补丁和文档同步
- Stronger alternatives not selected:
  - 直接修改 `/tmp/trellis-0.5.17-2`：只能治标，不能修 workflow 产品源码

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - 是否按上述方向进入 `docs/workflows/新项目开发工作流/` 源码修复
  - 是否接受将 Claude/OpenCode/Codex 的 agent/subagent 路径统一改为当前 workflow 显式禁用

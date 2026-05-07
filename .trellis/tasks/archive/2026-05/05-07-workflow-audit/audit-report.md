# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: task-based runtime
- Current CLI: `codex` (inferred from current executor)
- Candidate Issues: OpenCode 双入口暴露、`todo.txt` 合同化、Codex dual-skills 复杂度、`parallel` 移除必要性、legacy `record-session` 兼容链残余复杂度
- Audit Stop Classification: `Blocked / No Handoff Target`

## Evidence-Gathering Actions Executed in This Round
- Read `COMPATIBLE_TRELLIS_VERSION` from `docs/workflows/新项目开发工作流/commands/workflow_assets.py` and compared it against `trellis -v` — Layer: `source repo`
- Read `.trellis/spec/skills/workflow-audit.md` to confirm the version gate, supported CLI surface, runtime escalation rules, and Codex handoff boundary — Layer: `source repo`
- Cross-checked `CLI原生适配边界矩阵.md`, `装后隐藏目录与托管边界核对清单.md`, `工作流总纲.md`, and `工作流嵌入执行规范.md` against actual script entrypoints — Layer: `source repo`
- Inspected `detect-embed-state.py`, `install-workflow.py`, and `upgrade-compat.py` for formal install gating, dual-skills handling, `parallel` removal, install record schema, and legacy agent migration logic — Layer: `source repo`
- Created `/tmp/trellis-workflow-audit-8SW9ej`, initialized Git `main`, configured 2 push URLs on `origin`, and ran `trellis init --claude --opencode --codex -y -u xzc` successfully — Layer: `runtime command output`
- Verified fresh baseline artifacts: `.agents/skills/` contains only `trellis-*` baseline skills; `.codex/` contains agents/hooks/config but no `.codex/skills/` directory; `.opencode/commands/trellis/` contains baseline `continue.md` and `finish-work.md` — Layer: `generated target project`
- Ran `detect-embed-state.py --json` against the `/tmp` target and confirmed `INITIAL_BASELINE_READY` with no traces/blockers — Layer: `runtime command output`
- Ran `install-workflow.py --dry-run` and confirmed planned deployment of phase commands, shared skills, helper scripts, execution cards, workflow patch, requirements pack import, bootstrap cleanup, AGENTS routing, `todo.txt`, and post-install `upgrade-compat.py --check` — Layer: `runtime command output`
- Ran `install-workflow.py` without `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` and confirmed the Codex formal-install gate rejects execution before any embed occurs — Layer: `runtime command output`

## Confirmed Issues

### [P1] OpenCode 的正式命令入口与 `.agents/skills` 共享 skills 形成重复暴露面
- Conclusion: workflow 现有设计会让 OpenCode 同时拥有 `.opencode/commands/trellis/*` 正式命令入口，以及 `.agents/skills/*/SKILL.md` 的可发现 phase skills，形成同语义双入口暴露。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:118`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md:80`
  - Layer: `runtime command output`
  - `install-workflow.py --dry-run` 明确计划把 `feasibility` 到 `delivery` phase skills 写入 `.agents/skills/`
- Validation Action:
  - 对照 OpenCode carrier 文档与安装器 dry-run 输出，确认 OpenCode 的正式入口仍是 `.opencode/commands/trellis/*`，同时同一轮安装又会把同语义 phase skills 写入 OpenCode 可扫描的 `.agents/skills/`
- Impact Scope:
  - OpenCode 使用入口、CLI 适配说明、审计影响面、用户认知成本
- Suggested Fix Direction:
  - 保留 Codex 所需 shared skills，但把 OpenCode 的“正式入口 / 次入口”边界收紧成单一权威口径，或减少 OpenCode 可发现的重复 phase surface

### `todo.txt` install-only reminder artifact
- Conclusion: false alarm after product-intent clarification. `install-workflow.py` 中保留 `ensure_project_todo()` 是有意设计；`todo.txt` 应按 install-only 协作提醒解释，而不是作为错误或 drift 信号。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/工作流总纲.md:259`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py:1492`
  - Layer: `runtime command output`
  - `install-workflow.py --dry-run` 计划在正式安装阶段创建 `todo.txt`
- Validation Action:
  - 结合产品意图澄清与总纲现有说明，确认 `todo.txt` 的设计目标是“安装时新增一个协作提醒文件”，而不是参与门禁或闭环
- Impact Scope:
  - 影响的是 spec 与 audit 的解释口径，不要求删除 `ensure_project_todo()`
- Suggested Fix Direction:
  - 在相关 spec 中明确：`todo.txt` 是 intentional install-only artifact，默认不应被后续 audit / capability 判断视为错误

### [P2] 当前 0.5.4 基线下，Codex dual-skills 的“典型 `.codex/skills/parallel` 现象”已不再是可复现默认态
- Conclusion: 现有文档仍把 `.codex/skills/parallel` 作为当前 `trellis init` 的典型观察示例，但 fresh `0.5.4` 基线运行并未生成 `.codex/skills/`，这使当前 dual-skills 叙述带有过时样本偏差。
- Evidence Source:
  - Layer: `source repo`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:160`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md:70`
  - Layer: `generated target project`
  - `/tmp/trellis-workflow-audit-8SW9ej` 中 `.agents/skills/` 存在且仅有 `trellis-*` baseline skills；`.codex/` 仅有 `agents/`, `hooks/`, `config.toml`
  - Layer: `runtime command output`
  - `find .codex -maxdepth 3 -type f | sort` 未显示任何 `.codex/skills/*`
- Validation Action:
  - 以 fresh `/tmp` 目标项目执行 `trellis init --claude --opencode --codex -y -u xzc`，直接比对 Codex 基线落盘目录；再回看文档中将 `.codex/skills/parallel` 作为“当前实际观察例子”的段落
- Impact Scope:
  - Codex 适配文档、装后核对重点、维护者对真实 baseline 风险点的判断
- Suggested Fix Direction:
  - 把 `.codex/skills/` 明确收敛为“历史上可能出现 / 当前需条件化检查”的次级影响面，而不是当前基线的典型默认例子

## Unconfirmed Items / False Alarms
- “workflow 仍在 overlay Trellis 原生 agents” -> false alarm
- “`.kiro/` / `.qoder/` 缺少当前 workflow 适配属于缺陷” -> false alarm
- “`parallel` 移除已经没有必要” -> unconfirmed
- “legacy `record-session` 兼容链在 fresh baseline 下已经完全可以删除” -> unconfirmed

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- `parallel` 移除是否仍有必要
  - Type: `Evidence Gap`
  - Cause: 当前 fresh baseline 未生成 `parallel` 入口，因此只能证明“当前默认态下不会触发该路径”，还不能证明历史/条件场景完全不存在
  - Impact: 无法把 `parallel` 清理链直接定性为 dead code
  - What is needed to continue: 用能稳定生成 `parallel` 的目标项目样本或历史 fixture 验证该路径是否仍有真实输入
- legacy `record-session` 兼容链是否仍值得保留
  - Type: `Evidence Gap`
  - Cause: 当前 fresh baseline 不含 `record-session`，本轮未进入 legacy 目标项目样本
  - Impact: 只能判断它对 fresh baseline 不是必需项，不能直接断言旧目标项目已不需要兼容
  - What is needed to continue: 选择带 legacy `record-session` 的升级样本项目做兼容链验证

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model: `.claude/commands/trellis/*.md` + Trellis 原生 `.claude/agents/*.md` + shared helper / workflow patch / AGENTS routing
- Does the current implementation match: 静态上匹配
- If not, what is wrong: 尚未看到静态层面的 source-contract 漂移；formal install 后落盘结果待验证

### OpenCode
- Expected carrier model: `.opencode/commands/trellis/*.md` 为正式主入口；`.agents/skills/*/SKILL.md` 会被扫描但不应替代命令入口
- Does the current implementation match: 不完全匹配
- If not, what is wrong: 共享 phase skills 被有意写入 `.agents/skills/`，而 OpenCode 又会扫描该目录，导致“正式命令入口 + 可发现技能入口”并存

### Codex
- Expected carrier model: `.agents/skills/*/SKILL.md` 为共享阶段 skills 主承载面；`.codex/skills/` 只保留 Codex 独有或项目自定义 skills；agents 由 Trellis 原生提供
- Does the current implementation match: 静态上匹配
- If not, what is wrong: 设计仍保留 dual-skills 条件分支，但 fresh `0.5.4` baseline 未生成 `.codex/skills/`，说明文档里的“当前典型现象”已经落后于当前默认运行态

## Suggested Fix Directions
- 收敛 OpenCode 的入口语义：让 `.opencode/commands/trellis/*` 保持唯一权威主入口，避免把 `.agents/skills` 同时描述成可操作的等价 phase surface
- 在 spec 中补充 `todo.txt` 的 intentional install-only 解释，避免后续 audit / capability 判断把它当成错误
- 更新 Codex 文档，把 `.codex/skills` 从“当前典型默认现象”改成“条件存在时的次级影响面”
- 把 fresh baseline 与 legacy 兼容面的验证步骤拆分得更显式，降低 `parallel` / `record-session` 对当前主文档的干扰权重

## Propagation Scope and Synchronized Update Range
- 可能受影响的层：
  - `docs/workflows/新项目开发工作流/*.md`
  - `docs/workflows/新项目开发工作流/commands/*.py`
  - `docs/workflows/新项目开发工作流/commands/{claude,opencode,codex}/README.md`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/*`
- Propagation risk notes:
  - CLI 边界文档、安装器、升级检查器、测试必须原子同步，否则会重新引入 source contract drift

## Recommended Next Step
- Recommended action: plain-language action
- Trigger condition: `/tmp` baseline、`detect-embed-state`、dry-run 与 Codex formal-install gate 都已跑通，剩余未验证点集中在 formal install handoff 与 legacy/conditional branches
- Recommendation reason: 现在最合理的下一步不是继续扩展静态阅读，而是选择是否补做非 Codex handoff；如果不补做，就应按当前报告进入修复讨论
- Stronger alternatives not selected: 当前不直接进入源文件修复，因为 formal install + post-install `upgrade-compat.py --check` 还没有非 Codex 证据闭环

## Stop Point and Pending Confirmations
- Auto-continue allowed: No
- User confirmation required for:
  - 是否由 Claude Code / OpenCode 在外部接手 `/tmp/trellis-workflow-audit-8SW9ej` 的 formal install 与 `upgrade-compat.py --check`
  - 若当前没有可用 handoff CLI，是否按本报告直接进入修复决策
- User confirmation received:
  - 已确认保留当前 `todo.txt` 处理方向：`install-workflow.py` 中的 `ensure_project_todo()` 属于 intentional install-only 设计；当前结果保持“不是错误信号，也不是必须升级回强合同面”的解释口径
  - 已确认继续执行本轮 source-level 修复与 spec/test 收敛；当前代码与文档修复已完成，formal install handoff 仍属于独立的外部运行时边界

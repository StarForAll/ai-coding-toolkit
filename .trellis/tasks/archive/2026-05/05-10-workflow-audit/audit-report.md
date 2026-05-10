# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues: `none`
- Generated Target Project Root: `/tmp/workflow-audit-NVba75`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- 读取 `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 并确认 `COMPATIBLE_TRELLIS_VERSION = 0.5.10` — Layer: `source repo`
- 执行 `trellis -v` 并确认实际版本为 `0.5.10` — Layer: `runtime command output`
- 阅读 `CLI原生适配边界矩阵.md`、`装后隐藏目录与托管边界核对清单.md`、`工作流嵌入执行规范.md`，建立 managed surface、baseline、Codex handoff 边界模型 — Layer: `source repo`
- 阅读 `install-workflow.py`、`upgrade-compat.py`、`detect-embed-state.py`，核对脚本合同、Codex gate、shared skills 目录策略、`parallel` 移除逻辑、装后 `--check` 闭环 — Layer: `source repo`
- 阅读 `test_workflow_installers.py` 中的 fixture/build 验证点，确认存在针对多 push URL、dry-run、Codex barrier、INITIAL_BASELINE_READY 的动态断言覆盖 — Layer: `source repo`
- 在 `/tmp/workflow-audit-NVba75` 创建 fresh target project：`git init -b main`、配置 `origin` 双 push URL、执行 `trellis init --claude --opencode --codex -u audit-dev -y` — Layer: `generated target project` — Stage: `baseline after trellis init`
- 检查 fresh baseline 落盘结果：存在 `.trellis/`、`.claude/`、`.opencode/`、`.codex/`、`.agents/` 与 `AGENTS.md`；存在 `.agents/skills/trellis-*` 与 `.codex/agents/trellis-*.toml`，但不存在 `.codex/skills/` 与 `workflow-nl-routing` 区段 — Layer: `generated target project` — Stage: `baseline after trellis init`
- 执行 `detect-embed-state.py --project-root /tmp/workflow-audit-NVba75 --json`，返回 `INITIAL_BASELINE_READY`、`traces=[]`、`blockers=[]` — Layer: `runtime command output`
- 执行 `install-workflow.py --project-root /tmp/workflow-audit-NVba75 --dry-run`，确认将分发 9 个阶段入口、2 个 Codex baseline skill patch、增强版 `trellis-research`、`workflow.md` patch、`AGENTS.md` NL routing、helper scripts、execution cards、install record 与 post-install check — Layer: `runtime command output`
- 执行未带 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` 的正式 `install-workflow.py`，确认在 Codex 下被硬阻断，且未写入 `.trellis/workflow-embed-attempt.json` — Layer: `runtime command output`
- 通过 Claude Code handoff 执行 formal install：`WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1 install-workflow.py --project-root /tmp/workflow-audit-NVba75` 返回 `0`，并回传“正式安装成功，装后自检通过” — Layer: `runtime command output`
- 在 formal install 后执行 `upgrade-compat.py --project-root /tmp/workflow-audit-NVba75 --check` 返回 `0`，输出“版本一致，部署完整，总冲突: 0” — Layer: `runtime command output`
- formal install 后核对 installed-state：`AGENTS.md` 已出现 `workflow-nl-routing` 区段、`.trellis/workflow.md` 已含 `workflow-projectization-patch`、`.trellis/scripts/workflow/` 有 7 个 helper 脚本、`.trellis/workflow-installed.json` 与 `.trellis/library-lock.yaml` 存在、`.agents/skills/` 新增 9 个 workflow phase skills、`todo.txt` 存在、`.trellis/workflow-embed-attempt.json` 不存在 — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`

## Confirmed Issues

### [P2] Codex 安装摘要把手动维护的 hooks 误算进 workflow patch
- Conclusion: `install-workflow.py` 在 Codex 汇总结果里把 `.codex/hooks.json` 的存在性校验计入 `patches`，与文档定义的“手动维护资产”边界冲突，导致 patch 计数夸大 workflow 实际写入量。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:149`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:150`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:157`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md:158`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py:1275`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py:1278`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - fresh baseline dry-run 摘要显示 `"[codex] 命令: 9/9, 补丁: 3, Agents: 1"`；但同一轮输出中并未发生 `.codex/skills/parallel` 移除，第三个 `patch` 实际来自 hooks 存在性计数
- Validation Action:
  - 在 fresh `trellis init` baseline 中确认 `.codex/hooks.json` 为 Trellis 产物、`.codex/skills/` 不存在
  - 运行 `install-workflow.py --dry-run`
  - 对照代码路径，确认 `result["patches"] += 1` 来自 hooks 存在性检查，而非 workflow 实际注入
- Impact Scope:
  - Codex dry-run / install 汇总结果
  - 维护者对“workflow 实际变更面”的审计判断
  - 可能影响后续回归测试对 patch 数的理解
- Suggested Fix Direction:
  - 把“手动维护资产存在性校验”从 `patches` 计数中剥离
  - 单独输出为 `prereq checks` 或 `manual baseline checks`

## Unconfirmed Items / False Alarms
- “workflow 仍在整体 overlay Trellis agents” -> false alarm
  - 静态证据显示当前合同只 overlay 增强版 `trellis-research`，`trellis-implement` / `trellis-check` 已回归 Trellis 原生管理
- “增强版 `trellis-research` 已经多余” -> false alarm
  - baseline 与 source repo carrier 的 diff 显示增强版引入了 `ace.search_context`、Context7、deepwiki、grok-search、exa advanced、Codex active-task 解析增强等能力，和 Trellis baseline agent 并不等价
- “`brainstorm` / `check` 与 Trellis 原生 `trellis-brainstorm` / `trellis-check` 共存属于重复错误” -> false alarm
  - 这是 workflow 阶段化产品语义与 Trellis 通用任务语义的并存，不是同一入口的重复分发
- “`.agents/skills/` 的存在本身就是重复缺陷” -> false alarm
  - 当前合同将其定义为 Codex 共享 skills 主承载面，同时也是 OpenCode 的共享分发核对面
- “`.codex/skills/` 必须始终存在且应承载 shared workflow skills” -> false alarm
  - fresh `0.5.10` baseline 实测不存在 `.codex/skills/`；source repo 也已把它降级为 conditional secondary carrier
- “formal install 后会残留 `workflow-embed-attempt.json` 或 install/check 闭环不完整” -> false alarm
  - Claude handoff 的 formal install 返回成功，随后 `upgrade-compat.py --check` 通过，且 attempt 文件不存在

## Confirmed Classification Snapshot
- 多余但仍有兼容价值：
  - `legacy start / finish-work / record-session` 兼容链路
  - legacy bare-name agents 迁移
  - `.codex/skills/` duplicate shared skill 清理分支
  - `parallel` 入口移除分支
- 当前 fresh `0.5.10` 主链不需要默认依赖：
  - 把 `.codex/skills/` 当成默认存在目录
  - 把 `.codex/skills/parallel` 当成 baseline 必检项
- 当前仍然必要：
  - 增强版 `trellis-research`
  - 9 个 workflow 阶段入口
  - `continue` / `finish-work` / `workflow.md` 的产品化 patch
  - `AGENTS.md` 的 `workflow-nl-routing`
  - helper scripts、execution cards、install record、attempt record
- 明确错误：
  - Codex patch 汇总把手动 hooks 存在性算成 workflow patch

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- none

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model: `.claude/commands/trellis/*.md` + Trellis 原生 `.claude/agents/*.md` + 项目自维护 `.claude/settings*.json` / hooks
- Does the current implementation match: `confirmed`
- If not, what is wrong: 当前 runtime 证据未发现 CLI 适配漂移；若后续要做裁剪，应集中在 legacy 兼容分支，而不是 Claude 主链映射

### OpenCode
- Expected carrier model: `.opencode/commands/trellis/*.md` + `.agents/skills/` 共享分发面 + Trellis 原生 `.opencode/agents/*.md`
- Does the current implementation match: `confirmed`
- If not, what is wrong: 当前 runtime 证据未发现 OpenCode 主链适配漂移；需单独谨慎的是，不要把 `.agents/skills/` 误表述成 OpenCode 正式入口

### Codex
- Expected carrier model: `.agents/skills/` 共享主承载面 + `.codex/config.toml` / `.codex/hooks.json` + Trellis 原生 `.codex/agents/*.toml`
- Does the current implementation match: `mostly confirmed`
- If not, what is wrong: `.codex/skills/` secondary carrier 已被证实不是 fresh baseline 默认面；它应继续被视为 legacy/conditional branch，而不是主链责任

## Suggested Fix Directions
- 先用 fresh `/tmp` baseline 识别“只服务历史兼容”的分支，再把它们与“当前仍必要的产品化增强”分开
- 对所有围绕 `.codex/skills/` 的逻辑，按“fresh baseline 必需 / 仅 legacy 兼容 / 已无观测价值”三档重分级
- 对增强版 `trellis-research`，补一份“为什么 Trellis 原生 still insufficient”的证据说明；若差异已消失，应考虑退役该 overlay

## Propagation Scope and Synchronized Update Range
- 受影响层：`docs/workflows/新项目开发工作流/*.md`、`commands/*.py`、`commands/test_workflow_installers.py`、平台 README、shared skill/command 分发合同
- 风险：一旦误把 legacy compatibility 当成 fresh baseline 必需，会导致文档、安装器、升级器、测试持续保留冗余分支

## Recommended Next Step
- Recommended action: `trellis-brainstorm`
- Trigger condition: 运行验证已闭环，当前剩下的是“要不要保留 legacy compatibility 的范围决策”，而不是再补事实
- Recommendation reason: 现在最合适的是先把“保留哪些兼容分支、删除哪些主链冗余”收敛成明确改动范围，再进入实现
- Stronger alternatives not selected: 不直接 `start` 或改代码，因为兼容保留策略还没冻结；不直接 `check`，因为目前还没有 source remediation 变更可验

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - 是否进入修复阶段，开始裁剪 legacy/conditional 分支并修正文档与脚本计数口径
  - 对 legacy compatibility 的保留边界：仅保留 upgrade path，还是继续保留 fresh-baseline 主链里的兼容描述

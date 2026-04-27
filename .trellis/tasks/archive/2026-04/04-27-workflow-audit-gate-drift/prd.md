# brainstorm: audit new-project workflow gate drift

## Goal

审计 `docs/workflows/新项目开发工作流` 在真实目标项目中的嵌入与运行语义，判断用户列出的 feasibility / brainstorm / design / plan 以及跨阶段问题在当前源资产中是否真实存在；若存在，先给出基于 Trellis 核心优先、Claude Code / Codex / OpenCode 原生适配的修正方案，待用户确认后再实施修改。

## What I Already Know

- 目标工作流位于 `docs/workflows/新项目开发工作流/`，后续改动也限定在该目录内。
- 当前 workflow 采用“`trellis init` 基线 + install-workflow.py 嵌入增强”的模型，首次嵌入前必须满足 `INITIAL_BASELINE_READY`。
- 嵌入协议要求：先 `detect-embed-state.py`，再 `install-workflow.py --dry-run`，再正式安装，最后 `upgrade-compat.py --check`。
- 当前 workflow 的关键源资产包括：
  - `commands/*.md` 阶段命令
  - `commands/shell/*.py` helper
  - `commands/install-workflow.py`
  - `commands/upgrade-compat.py`
  - `commands/workflow_assets.py`
  - 各 CLI 适配 README 与 `命令映射.md`
- 当前任务要判断的问题主要集中在：
  - 阶段出口是否真的冻结了关键决策
  - 粗估是否被阶段性强制刷新
  - UI / watermark / packaging / CI 等横切 lane 是否前置识别
  - 文档 source-of-truth 是否漂移
  - workflow-state 笔记是否替代了可验证快照

## Assumptions (Temporary)

- 你提供的问题样本来自某个真实目标项目的运行痕迹，但不代表当前源工作流一定已经存在同样问题。
- 当前审计以“现有源资产 + 在 `/tmp` 新建 Trellis 基线项目的嵌入实测”作为主要证据，不直接修改当前仓库直到你确认方案。
- 若某个问题只在历史目标项目里出现、但当前源资产已经修复，我会明确标注为“历史问题，当前源未复现”。

## Open Questions

- 当前无阻塞问题；先完成源资产审阅与 `/tmp` 实测，再决定是否需要向你确认额外边界。

## Requirements (Evolving)

- 审计对象仅限 `docs/workflows/新项目开发工作流/` 对应的 workflow。
- 必须先在 `/tmp` 新建临时项目并执行 `trellis init`，再按当前 workflow 的正式嵌入协议进行验证。
- 需要同时核对 Trellis 核心机制与三类 CLI 原生适配边界：Claude Code / Codex / OpenCode。
- 输出需要区分：
  - 问题确实存在
  - 问题部分存在 / 表述不准确
  - 当前源资产中不存在
- 对于存在的问题，先给“如何修正”的方案，不直接落盘修改。

## Acceptance Criteria (Evolving)

- [ ] 完成对 `feasibility.md`、`brainstorm.md`、`design.md`、`plan.md` 及相关 helper / 映射文档的源级审阅。
- [ ] 在 `/tmp` 创建 Trellis 基线项目，并完成状态检测、dry-run、正式嵌入、自检链路验证。
- [ ] 对用户列出的每个错误点给出“是否存在 + 证据 + 影响 + 修正方案”。
- [ ] 在实施前给出一版明确的修改提案，并等待用户确认。

## Out of Scope

- 未经确认直接修改 workflow 源资产。
- 对 `docs/workflows/新项目开发工作流/` 之外的 workflow 做广泛重构。
- 为历史目标项目直接修补运行态数据或归档产物。

## Technical Notes

- 关键协议来源：
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
- 初步定位到的关键实现：
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
- 实测将优先验证：
  - 初始态判定
  - 三 CLI 资产部署形态
  - workflow patch / helper / skills / agents 的落盘边界
- `/tmp` 实测目标项目：`/tmp/trellis-workflow-audit-1lPHR2`
- 已验证嵌入链路：
  - 安装前 `detect-embed-state.py` 返回 `INITIAL_BASELINE_READY`
  - `install-workflow.py --dry-run` 成功预演三 CLI 资产部署
  - 设置 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` 后正式安装成功
  - 安装后 `detect-embed-state.py` 返回 `ALREADY_VALID_EMBEDDED`
- 已验证负例：
  - 构造 `external_outsourcing` 的 `assessment.md`，故意缺失 `source_watermark_*` / `ownership_proof_required` 字段时，`workflow-state.py validate` 仍可通过；但 `ownership-proof-validate.py --phase feasibility` 会失败
  - 构造仅含空壳 `index.md` / `TAD.md` / `ODD-dev.md` / `ODD-user.md` 的 `design/` 目录时，`design-export.py --validate` 可通过；配合最小 `assessment.md` 与 `prd.md` 后，`workflow-state.py validate` 也可通过

## Workflow Decisions

- Accuracy Status: in_progress
- Complexity: L2
- Need More Divergence: yes
- Need Sub Tasks: no
- Next Step: inspect source assets and run `/tmp` embed rehearsal

# workflow-audit: 新项目开发工作流

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` 且已嵌入 `docs/workflows/新项目开发工作流/` 的目标项目，审计当前源工作流是否存在真实缺陷，并仅在 `docs/workflows/新项目开发工作流/` 范围内修复真实问题；对 Trellis 原生问题只允许通过该工作流的安装器 / 补丁链做目标项目侧修复，不直接改 repo 其他目录。

## What I already know

- 当前仓库是 workflow authoring source repo，不是目标项目运行态。
- 当前审计目标固定为 `docs/workflows/新项目开发工作流/`。
- 目标项目样本固定为 `/tmp/trellis-0.5.17-2`。
- 当前版本门禁通过：`COMPATIBLE_TRELLIS_VERSION=0.5.17`，`trellis -v` 实际也是 `0.5.17`。
- 用户要求本轮先分析和给出修复方案，得到同意后再修改源工作流。
- 用户明确限制：除当前任务目录外，其他修改范围只能落在 `docs/workflows/新项目开发工作流/`。

## Assumptions

- `/tmp/trellis-0.5.17-2` 保持可读且代表当前工作流嵌入后的真实样本。
- 本轮无需重新在 `/tmp` 执行 formal embed，只需用现有目标项目做对照分析。
- 若发现“文档与代码不一致”，优先修源工作流单一事实源，再同步关联文档/测试。

## Requirements

- 必须区分 confirmed issue / false alarm / evidence gap。
- 必须判断是否存在同类问题，不能只修单点表面症状。
- 必须避免把当前设计合同误判为 defect，尤其是安装器托管边界与 workflow-docs 分发范围。
- 在用户同意前，不修改 `docs/workflows/新项目开发工作流/`。

## Acceptance Criteria

- [ ] 形成基于源工作流与 `/tmp/trellis-0.5.17-2` 的证据化问题清单。
- [ ] 对每个候选问题给出真实性判断、影响范围、同类问题范围。
- [ ] 给出只修改 `docs/workflows/新项目开发工作流/` 的修复方案。
- [ ] 在未获用户同意前，不修改工作流源文件。

## Out of Scope

- 不直接修改当前仓库根级 `.trellis/`、`.claude/`、`.codex/`、`.opencode/` 等 repo-local 运行层。
- 不把 workflow-managed subset 扩大到当前合同之外。
- 不把 Trellis 原生上游问题直接修到仓库其他目录。

## Technical Notes

- 关键证据源：
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/trellis-meta-strong-gate/local-architecture/workflow.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `/tmp/trellis-0.5.17-2/.trellis/workflow.md`
  - `/tmp/trellis-0.5.17-2/.trellis/scripts/workflow/workflow-state.py`

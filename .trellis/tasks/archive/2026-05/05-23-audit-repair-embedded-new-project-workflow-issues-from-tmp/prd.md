# workflow-audit: 嵌入式新项目工作流问题审计与修复

## Goal

以 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 并嵌入
`docs/workflows/新项目开发工作流/` 的临时目标项目为运行时证据源，
核实用户列出的阶段状态机、命令契约、执行卡集成、CLI 原生适配、文档一致性
和旧版本兼容性问题是否真实存在；若确认存在，后续只在
`docs/workflows/新项目开发工作流/` 范围内修复，不修改其他目录。

## What I already know

- 当前仓库是工作流作者仓库，不是被嵌入的目标项目。
- 用户要求分析判断对象是 `/tmp/trellis-0.5.17-2`，不是当前仓库自身运行中的
  `.trellis/`。
- 若需要修 Trellis 原生问题，应该在该工作流内以补丁方式修复，供安装器嵌入时应用。
- 用户明确要求：先分析判断真实问题，再给出修正方案，获得同意后才继续源码修复。
- 修复范围受限于 `docs/workflows/新项目开发工作流/`；当前任务目录可正常写入。
- `workflow-audit` 版本门禁已通过：
  - `COMPATIBLE_TRELLIS_VERSION = 0.5.17`
  - `trellis -v = 0.5.17`
- 当前 CLI 为 Codex；本仓库 `.trellis/config.yaml` 的 `codex.dispatch_mode`
  约束为 `inline`，本次不能使用子代理。

## Assumptions (temporary)

- `/tmp/trellis-0.5.17-2` 能作为有效的 workflow-installed 状态样本。
- 用户给出的 15 个问题与解决思路都只是候选假设，不能直接当作 defect。
- 本轮先完成 task-based runtime audit 的取证与提案，不在用户确认前修改
  `docs/workflows/新项目开发工作流/`。

## Open Questions

- `/tmp/trellis-0.5.17-2` 是否已经足够代表当前工作流安装后的真实状态，还是还需
  额外重建 clean baseline 来做更强归因。
- 对于 Codex formal embed handoff 边界，本轮是否能完全通过已有 `/tmp` 证据闭合，
  或仍会留下部分 Evidence Gap。

## Requirements (evolving)

- 逐项核实用户列出的候选问题，并区分 confirmed issue / false alarm /
  evidence gap。
- 主动寻找同类问题，不能只限于 15 个候选点。
- 审计与修复边界必须严格限制在 `docs/workflows/新项目开发工作流/`。
- 在给出分析结论和修正方案后暂停，等待用户确认。
- 用户确认后，修复必须以最小且成组的补丁方式落到 workflow source，
  不能引入新的路由绕过、阶段歧义或安装回归。

## Acceptance Criteria (evolving)

- [ ] `audit-report.md` 形成证据化结论，覆盖 confirmed issue / false alarm /
      evidence gap。
- [ ] 每个 confirmed issue 都有源头证据、影响范围和最小修复方向。
- [ ] 用户确认前不修改 `docs/workflows/新项目开发工作流/` 源文件。
- [ ] 用户确认后，所有改动仅发生在 `docs/workflows/新项目开发工作流/`。
- [ ] 完成后运行与本次改动直接相关的校验，并如实报告 pass / fail / not run。

## Definition of Done

- 问题真实性已基于 source repo、`/tmp` 目标项目和运行命令输出完成交叉判断。
- 修复方案明确了传播范围、脚本/文档契约同步点和回归风险。
- 如进入修复阶段，相关校验命令已执行并记录真实结果。

## Out of Scope (explicit)

- 修改当前仓库除 `docs/workflows/新项目开发工作流/` 以外的目录。
- 把用户的候选问题未经验证直接当作 defect 批量修改。
- 在未获确认前提前修补 workflow source。

## Technical Notes

- 审计技能：`workflow-audit`
- 配套流程技能：`trellis-start`、`trellis-brainstorm`
- 关键入口文件初步定位：
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/*.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `/tmp/trellis-0.5.17-2`

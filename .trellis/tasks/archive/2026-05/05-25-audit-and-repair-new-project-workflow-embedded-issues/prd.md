# audit-and-repair-new-project-workflow-embedded-issues

## Goal

基于 `/tmp/trellis-0.5.17-2` 这个已经执行过 `trellis init` 并嵌入 `docs/workflows/新项目开发工作流/` 的临时目标项目，审计该工作流的真实嵌入行为、阶段门禁、文档契约、运行时补丁与安装后完整性，判断用户列出的候选问题及同类问题是否真实存在；若确认存在，再提出只修改 `docs/workflows/新项目开发工作流/` 的低风险修复方案，等待用户确认后实施。

## What I already know

- 修复范围被严格限制为 `docs/workflows/新项目开发工作流/`；其他目录不能修改。
- 审计对象不是当前仓库自身的运行态，而是 `/tmp/trellis-0.5.17-2` 的实际嵌入结果。
- 如果问题属于 Trellis 原生缺陷，要求在该工作流内以补丁/安装器修复方式处理，而不是改动仓库外的原生 Trellis 源。
- 用户要求先分析判断，再给出修正方案，待用户同意后再继续修改。
- 用户强制要求：“任何项目都不能跳过 feasibility 阶段”，因此所有允许 personal 首次入口跳过 feasibility 的行为都需要重点核查。

## Assumptions

- `/tmp/trellis-0.5.17-2` 是本轮审计的权威目标项目样本，可用于验证嵌入后行为。
- 当前仓库中的 `docs/workflows/新项目开发工作流/commands/shell/*.py` 是安装器分发到目标项目 `.trellis/scripts/workflow/` 的源脚本。
- 仅在用户确认修复方案后，才会开始修改 `docs/workflows/新项目开发工作流/` 下的源资产与测试。

## Open Questions

- 无阻塞问题；当前先完成证据化审计和方案收敛。

## Requirements

- 逐项核验用户列出的候选问题，不得直接假设为真。
- 对每个候选问题给出：证据、是否真实存在、影响范围、是否存在同类问题。
- 额外搜寻同一类缺陷，避免只修单点。
- 若确认问题真实存在，提出最小风险修复方案，并说明需要联动修改的文件类别（脚本 / 测试 / 文档 / 安装器补丁）。
- 在用户确认前，不修改 `docs/workflows/新项目开发工作流/` 源资产。
- 进入正式修复后，必须同步补充相关联 spec / 说明文档。
- 文档语言边界：
  - 维护侧文档（工作流源维护说明、审计/维护规则、中文总览类文档）使用中文
  - 嵌入到目标项目的命令/运行时文档仅维护英文内容，不额外补中文副本
- 修复时不得引入新的阶段门禁绕过、安装态漂移或文档/脚本语义不一致问题。

## Acceptance Criteria

- [ ] 已基于源工作流和 `/tmp/trellis-0.5.17-2` 嵌入态完成候选问题取证。
- [ ] 已给出“真实存在 / 不成立 / 需补证”的清单。
- [ ] 已给出待用户确认的修复方案，且修复范围仅指向 `docs/workflows/新项目开发工作流/`。
- [ ] 在未获用户确认前，不改动目标修复目录中的源资产。
- [ ] 正式修复时已同步更新相关联 spec / 文档，并满足“维护侧中文、嵌入侧英文”的语言边界。
- [ ] 修复后相关测试、验证脚本和文档引用保持一致，没有引入新的已知回归。

## Out of Scope

- 不修改当前仓库中 `docs/workflows/新项目开发工作流/` 以外的目录。
- 不把当前仓库自身 Trellis 工作流状态误当作本次审计对象。
- 不在本阶段执行正式修复。

## Technical Notes

- 版本门已确认通过：`docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = 0.5.17`，当前 `trellis -v = 0.5.17`。
- 已定位核心实现面：`workflow-state.py`、`validators_gates.py`、`validators_core.py`、`state_utils.py`、`embed_integrity.py`、`source-watermark-guard.py`、`plan-validate.py`、`check.md`、`workflow-patch-projectization.md`、`阶段状态机与强门禁协议.md`。
- `/tmp/trellis-0.5.17-2/.trellis/` 中存在嵌入后的 `workflow.md` 与 `.trellis/scripts/workflow/*` 安装态脚本，可用于静态/轻量运行验证。

# workflow-audit: 历史修复点满足性审计

## Goal

基于当前仓库中的 `工作流历史修复点.txt`，对固定目标 `docs/workflows/新项目开发工作流/` 做同版本维护审计，判断目标项目嵌入该工作流后，是否满足其中 25 条历史修复点。结论必须区分：可由 source repo 静态证明、需 `/tmp` 目标项目运行时证明、以及因 Codex formal embed 边界而暂时无法闭环的部分。

## What I already know

- 审计目标固定为 `docs/workflows/新项目开发工作流/`
- `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 中 `COMPATIBLE_TRELLIS_VERSION = "0.5.9"`
- 当前环境 `trellis -v` 返回 `0.5.9`，版本预检通过
- 当前主执行器是 Codex，因此运行时验证进入 formal embed 时必须停下并交接给 Claude Code 或 OpenCode
- `工作流历史修复点.txt` 共 25 条，覆盖安装前置条件、阶段门禁、项目级文档产物、README 双语、法律风险、水印与归属、性能优化子任务、research/implement/check 子代理链、CLI 嵌入规范等多个层面
- 当前工作流的关键权威文件包括：
  - `工作流嵌入执行规范.md`
  - `CLI原生适配边界矩阵.md`
  - `装后隐藏目录与托管边界核对清单.md`
  - `工作流总纲.md`
  - `阶段状态机与强门禁协议.md`
- 当前工作流安装器会自动导入 `pack.requirements-discovery-foundation`，并在存在时清理 `00-bootstrap-guidelines`
- 当前 Trellis 0.5.9 基线原生提供 `trellis-research` / `trellis-implement` / `trellis-check` agents；workflow 不再 overlay agent 内容，只做 legacy bare-name 迁移

## Assumptions (temporary)

- 本轮可以完成 `/tmp` 目标项目创建、Git 前置条件配置、`trellis init`、`detect-embed-state.py` 与 `install-workflow.py --dry-run`
- 当前会话不能把 formal install 和 post-install `upgrade-compat.py --check` 声称为“已验证完成”，除非获得非 Codex CLI 的交接证据
- 25 条历史修复点中，部分属于安装器/脚本合同，部分属于阶段命令和状态机合同，部分属于导入 spec 和项目运行治理合同，不能混成一个层次判断

## Open Questions

- 哪些历史修复点已经能被 source repo 静态证据直接证明满足或不满足
- 哪些历史修复点只有在 `/tmp` 目标项目形成 baseline 和 workflow-installed state 后才能判断
- formal install 交接未完成前，哪些点必须保持 `Blocked / Evidence Gap`
- 当前 `parallel` 移除、legacy `record-session` 兼容链、`.codex/skills/` 次级影响面是否仍属于真实现存分支，还是只剩历史兼容负担

## Requirements (evolving)

- 审计必须逐条覆盖 `工作流历史修复点.txt` 中 25 条历史点
- 每条结论必须标明证据层：`source repo` / `generated target project` / `runtime command output`
- 必须使用 `A. Understand target system mechanics -> B. Static evidence gathering -> C. Structured gap analysis` 主线
- 因用户要求“最深的分析判断步骤”，必须进入 task-based runtime 审计路径
- `/tmp` 运行时验证至少覆盖：
  - clean Git 项目创建
  - `origin` 双 push URL 前置条件
  - `trellis init`
  - baseline 快照
  - `detect-embed-state.py`
  - `install-workflow.py --dry-run`
- 到达 formal install 时必须停止并输出 Codex handoff block，不能伪造完成
- 当前回合不修改 workflow source files，只产出审计结论和后续建议

## Acceptance Criteria (evolving)

- [ ] 版本预检结果已记录
- [ ] 25 条历史修复点已经完成逐条分类和证据定位
- [ ] 任务内 `audit-report.md` 已记录 A/B/C 静态证据
- [ ] `/tmp` baseline 与 dry-run 证据已记录
- [ ] 所有结论区分 confirmed / unconfirmed / false alarm / blocked
- [ ] formal install handoff 边界被明确标记，未越权执行

## Definition of Done (team quality bar)

- 所有结论基于已执行的命令、已读取的文件和明确的 source-layer 证据
- 不把“文档里提到”误写成“目标项目嵌入后已验证满足”
- 对无法闭环的项明确写出缺口、原因、下一步
- 建议路径只到 stop-and-confirm，不自动进入修复

## Out of Scope (explicit)

- 跨版本兼容性审计；这属于 `workflow-capability-audit`
- 直接修复 workflow source files
- `.kiro/`、`.qoder/` 等当前 managed surface 之外的平台
- 与 workflow 无关的普通业务代码审查

## Technical Notes

- 输入基准：`工作流历史修复点.txt`
- 核心审计契约：
  - `.trellis/spec/skills/workflow-audit.md`
  - `.agents/skills/workflow-audit/SKILL.md`
- 核心 source repo 文档：
  - `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
- 关键脚本：
  - `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/upgrade-compat.py`
  - `docs/workflows/新项目开发工作流/commands/shell/workflow-state.py`
  - `docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py`
  - `docs/workflows/新项目开发工作流/commands/shell/ownership-proof-validate.py`

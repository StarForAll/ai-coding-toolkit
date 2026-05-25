# audit and repair embedded workflow gate issues

## Goal

修复 `docs/workflows/新项目开发工作流/` 中与嵌入目标项目 gate 校验相关的真实缺陷，使后续通过安装器嵌入到目标项目后，review-gate / project-audit / delivery 等阶段的路径契约、结构化字段契约和强门禁行为一致且可验证。

## What I already know

- 用户已明确要求只修改 `docs/workflows/新项目开发工作流/`，其他目录不做产品层修复。
- 目标验证对象不是当前仓库运行态，而是 `/tmp/trellis-0.5.17-2` 这一已执行 `trellis init` 并嵌入工作流的临时项目。
- 已确认 `trellis -v` 为 `0.5.17`，与工作流兼容锚点一致。
- 已确认以下真实问题存在：
  - 缺失多个 gate status 时脚本默认放行
  - review-gate 多 CLI 产物路径契约与校验器不一致
  - formal project-audit 缺少 `task_plan.md` 时跳过任务完成校验
  - project-audit 内部 multi-cli-review 缺少脚本级闭环校验
  - project-audit / review-gate 的 Mode / Decision 使用 substring 判定，存在误判
- 已确认现有测试把部分 legacy 放行行为视为通过，需要同步收紧。

## Assumptions

- 以“脚本行为对齐当前文档契约”为主，不通过放宽文档去迁就错误实现。
- 对 legacy 宽松兼容的收紧是预期修复，不视为破坏性误改。
- 允许新增或调整 `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py` 等相关测试，以锁定行为。

## Requirements

- 修复 `validators_gates.py` 中 gate status 缺失放行问题。
- 修复 review-gate 与 project-audit 对 multi-cli-review 产物路径和闭环文件的校验逻辑。
- 对 Mode / Decision / 同类结构化字段改为严格、确定性的单值解析。
- formal project-audit 必须在缺少 `task_plan.md` 或无法证明全部代码相关任务完成时阻断。
- 对已识别的同类问题一并修复，避免只修表面。
- 修复不能引入新的明显回归，需以测试验证。

## Acceptance Criteria

- [ ] 相关 gate 校验逻辑与命令文档契约一致
- [ ] 缺失 `check_gate_status` / `project_audit_gate_status` / `review_gate_closure_status` / `delivery_gate_status` / `finish_work_gate_status` 时，相关阶段校验被正确阻断
- [ ] review-gate / project-audit 的 multi-cli-review 路径契约与校验路径一致
- [ ] Mode / Decision 模板残留或混合值不再被 substring 误判通过
- [ ] formal project-audit 在缺少 `task_plan.md` 或未完成全部代码相关任务时会被阻断
- [ ] 相关单元测试通过

## Out of Scope

- 修改当前仓库 `.trellis/` 运行态逻辑之外的其他产品目录
- 修复 Trellis 原生上游源码本体
- 处理与本次 gate 主题无关的文档润色或结构重写

## Technical Notes

- 主要修改范围：
  - `docs/workflows/新项目开发工作流/commands/shell/validators_gates.py`
  - `docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
  - `docs/workflows/新项目开发工作流/commands/review-gate.md`
  - `docs/workflows/新项目开发工作流/commands/project-audit.md`
- 需要遵循：
  - `.trellis/spec/scripts/python-conventions.md`
  - `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
  - `.trellis/spec/scripts/workflow-command-doc-contracts.md`
  - `.trellis/spec/docs/index.md`

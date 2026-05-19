# 初始审计记录

## Audit Boundary

- Workflow source root: `docs/workflows/新项目开发工作流/`
- Target evidence root: `/tmp/trellis-0.5.17-2`
- Current CLI: `codex`
- Compatible Anchor Version: `0.5.17`
- Current Trellis Version: `0.5.17`
- Version Gate: `passed`

## Validation Actions Already Performed

1. 读取 `docs/workflows/新项目开发工作流/commands/workflow_assets.py`，确认 `COMPATIBLE_TRELLIS_VERSION = "0.5.17"`。
2. 运行 `trellis -v`，结果为 `0.5.17`。
3. 使用语义检索定位工作流源中的以下关键实现：
   - `commands/shell/workflow-state.py`
   - `commands/record-session.md`
   - `commands/detect-embed-state.py`
   - `commands/shell/patch-session-start-strong-gate.py`
   - `commands/shell/patch-inject-workflow-state.py`
4. 使用语义检索定位 `/tmp/trellis-0.5.17-2` 中的已安装对应物：
   - `.trellis/scripts/workflow/workflow-state.py`
   - `.claude/commands/trellis/record-session.md`
   - `.opencode/commands/trellis/record-session.md`
   - `.agents/skills/record-session/SKILL.md`
   - `.claude/hooks/session-start.py`

## Candidate Issues Under Verification

### H1. `record-session` 终态门禁未覆盖完整收尾闭环

- 源实现线索：
  - `validate_record_session_gate()` 直接委托 `validate_delivery_gate()`
  - `validate_delivery_gate()` 支持 `repo_root`，但 `validate_record_session_gate()` 当前未传入
- 已观察到的文档契约：
  - `record-session.md` 和 record-session skill 明确要求 archive、add_session 与元数据收尾
- 待补证：
  - `validate` 是否会在未 archive / 未 add_session / 元数据未清理时仍报告通过
  - delivery 外包门禁是否因缺少 `repo_root` 被弱化

### H2. `route` / `set` / `validate` 阶段校验语义分叉

- 源实现线索：
  - `collect_exit_gate_blockers()` 覆盖 design / brainstorm 等退出门禁
  - `validate_stage_exit_artifacts()` 当前分支集合与上述逻辑不一致
- 待补证：
  - design 阶段是否确实存在 `route` 阻塞而 `validate` 通过
  - brainstorm 的 customer-facing PRD 要求是否在 `route` 与 `validate` 间不一致

### H3. 非执行阶段重入策略过宽

- 源实现线索：
  - `cmd_route()` 对非执行阶段存在普遍 `reenter` 路径
- 待补证：
  - 哪些阶段只发 warning、不阻塞
  - 哪些阶段按工作流契约应收紧

### H4. 多平台副本一致性自检不足

- 源实现线索：
  - `detect_embed_invalid()` 目前聚焦 install record、library lock、critical patch marker
- 待补证：
  - 是否缺少对 `.claude/.opencode/.agents/.codex` 中命令/skill 语义漂移的检测
  - 当前工作流源是否已有可复用的一致性检查基础

### H5. degraded / single-session fallback 兼容层残留

- 这是候选风险，不预设为 defect。
- 待补证：
  - 现有 fallback 是否仍满足“多 session 不猜”的收敛边界
  - 若只是兼容层存在但不破坏闭环，应记录为保留风险而非本轮主修复项

## Expected Next Evidence

- 逐段读取 `workflow-state.py`、`task.py`、`active_task.py`、record-session 命令文档与安装/升级检测逻辑。
- 在 `/tmp/trellis-0.5.17-2` 以只读方式构造最小复现，确认 `validate` / `route` / `set` 实际输出差异。
- 基于确认结果设计最小回归测试矩阵，再进入修复。

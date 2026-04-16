# clarify workflow baseline dependency

## Goal

在 `docs/workflows/新项目开发工作流` 中明确说明：该 workflow 是嵌入到 Trellis 基线之上的，某些运行时行为直接依赖目标项目的 Trellis 基线实现；本次特别说明 close-out 链路中的 `task.py archive` 依赖包含 archive auto-commit pathspec 修复的较新 Trellis 基线，而不是由当前 workflow 自身分发这段基线代码。

## Requirements

- 明确区分 Trellis 基线能力与 workflow 分发资产
- 对 `record-session -> archive` close-out 链路补充基线依赖说明
- 在安装或使用入口处给出可见提示，避免用户误以为 workflow 自己携带了该修复
- 不复制 `.trellis/scripts/common/task_store.py` 到 workflow 目录

## Acceptance Criteria

- [ ] `工作流总纲.md` 明确说明该 workflow 的 close-out 行为依赖 Trellis 基线
- [ ] 至少一个用户真正会看到的入口位置包含该提示（安装器或 walkthrough）
- [ ] close-out 相关文档说明 archive 仍直接调用 `python3 ./.trellis/scripts/task.py archive`
- [ ] 没有新增将基线脚本复制进 workflow 分发资产的行为

## Technical Notes

- 基线修复位置：`.trellis/scripts/common/task_store.py`
- workflow 分发边界：`docs/workflows/新项目开发工作流/commands/workflow_assets.py`
- 收尾命令说明：`docs/workflows/新项目开发工作流/commands/delivery.md`、`docs/workflows/新项目开发工作流/commands/record-session-patch-metadata-closure.md`

### 1. Code Quality

<!-- finish-work-projectization-patch -->

不要继续沿用 Trellis 基线里的默认包管理器占位命令。

这里必须改成**当前项目在 `§3 design -> 3.7 技术架构确认后的项目 Spec 对齐` 阶段已经明确的真实自动化检查矩阵**。

进入 `/trellis:finish-work` 前，至少确认：

- [ ] 当前项目已经定义清楚必须通过的真实检查命令（如 lint / type-check / test / build / e2e / migration / packaging / 质量平台门禁等），且检查矩阵与 design 3.7 阶段确定的自动化检查矩阵一致
- [ ] `finish-work` 正文、项目 `.trellis/spec/` 与 README / 交付说明中的检查矩阵保持一致
- [ ] 默认包管理器占位命令已经删除，不再继续沿用通用模板
- [ ] 如果技术架构尚未确定，先回到 `design` 完成矩阵定义，而不是伪造校验命令
- [ ] 所有“必须通过”的命令都已实际执行，并只记录真实结果：通过 / 失败 / 未运行
- [ ] 当前 task 已形成或更新 `finish-work-checklist.md`，至少记录：
  - 冻结验证矩阵的 `Check / Command or Method / Result`
  - 人工验证的真实状态与证据缺口
  - 若为 child task，parent 记录同步状态
  - 若为 Trellis / workflow 相关修改，隐藏目录联动同步状态
- [ ] 若当前轮次不落盘 `finish-work-checklist.md`，则命令输出中必须逐项覆盖以上信息，并明确为什么没有形成 task-local checklist

```bash
<your-quality-platform-gate-command-here>
```

```text
由当前项目在 design 阶段补充完整检查矩阵；
这里不再保留任何默认包管理器占位。
必须有明确质量平台门禁；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因。
```

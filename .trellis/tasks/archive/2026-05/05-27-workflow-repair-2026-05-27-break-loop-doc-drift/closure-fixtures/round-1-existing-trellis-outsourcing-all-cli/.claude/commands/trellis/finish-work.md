# Finish Work - Pre-Commit Checklist

Wrap up the current session: verify close-out evidence, confirm the frozen quality matrix, and complete the native Trellis archive + session-record steps after delivery. Code commits are NOT done here — those happen in workflow Phase 3.4 before you invoke this command.



---

# Finish Work

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
  - 采用固定章节标题：`## 冻结验证矩阵` / `## 人工验证` / `## 同步结论`
  - 冻结验证矩阵的 `Check / Command or Method / Result`
  - 人工验证的真实状态与证据缺口
  - 若为 child task，parent 记录同步状态
  - 若为 Trellis / workflow 相关修改，隐藏目录联动同步状态
- [ ] 若当前 task 还没有 `finish-work-checklist.md`，先以 `.trellis/workflow-docs/finish-work-checklist-template.md` 为骨架生成，再填写真实结果
- [ ] 当前轮次必须落盘 `finish-work-checklist.md`；不能只靠会话输出临时描述来替代强门禁证据文件

```bash
<your-quality-platform-gate-command-here>
```

```text
由当前项目在 design 阶段补充完整检查矩阵；
这里不再保留任何默认包管理器占位。
必须有明确质量平台门禁；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因。
```

### 2. close-out 基线路径

当前 workflow 对 Trellis 原生 `finish-work` 的项目化要求如下：

- `delivery` 负责项目级/交付级验收、交付物确认与所有权证明（外包 profile）
- Trellis 原生 `finish-work` 是**当前活动任务**的正常终态入口，负责收尾冻结、当前活动任务的 `task.py archive` 与 `add_session.py`
- `record-session` 不再属于 fresh baseline 主链；若旧目标项目仍保留该入口，只按 legacy 兼容入口处理
- 因此，`delivery` 与原生 `finish-work` 不是同一层级的阶段定义；不要把 `delivery` 写成原生 `finish-work` 的内建步骤，也不要把原生 `finish-work` 改写成项目级交付阶段

进入 `/trellis:finish-work` 前，至少确认：

- [ ] 若当前项目存在项目级/交付级收口要求，相关 `delivery` 证据已完成
- [ ] 当前 task 已形成或更新 `finish-work-checklist.md`（见上方 §1）
- [ ] 已先执行 `python3 ./.trellis/scripts/workflow/workflow-state.py validate <task-dir>`，确认当前 task 的 `delivery` 门禁已真实通过；`finish-work` 不得只凭文字 checklist 假定 `delivery` 已完成
- [ ] 使用 Trellis 原生 `finish-work` 完成最终 `archive + add_session`，不要再额外发明第二套 close-out helper
- [ ] 若目标项目的 `.trellis/` 元数据自动提交失败，按目标项目当前 Trellis 基线能力处理，不在 workflow 层额外发明 helper 分支

**archive 链基线依赖说明**：

- `task.py archive` 与 `add_session.py` 的自动提交均由 Trellis 基线负责，workflow 不分发 `task.py` / `task_store.py`
- 若 archive 或 `add_session.py` 的自动提交失败，建议先升级目标项目的 Trellis 基线版本

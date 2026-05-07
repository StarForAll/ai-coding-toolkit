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

### 2. record-session 自动提交失败恢复

`record-session-helper.py` 已内置只读失败检测与恢复机制。该增强对所有平台生效（三个平台共用同一套 `record-session-helper.py`），但 Codex（沙箱环境）最容易触发。

**架构：`--no-commit` + commit-only 分离**

`record-session-helper.py` 调用 `add_session.py` 时传递 `--no-commit`，阻止其自动提交和生成 pending。元数据提交由 `metadata-autocommit-guard.py --commit-message` 单独执行（commit-only 模式）。这保证了只读失败时只产生一份 pending 和一条恢复命令。

**恢复流程**：

1. `add_session.py --no-commit` 写入 journal/index（不触发 git commit）
2. `metadata-autocommit-guard.py --commit-message` 执行 commit-only
3. 若 commit-only 因只读/权限失败，在 `.trellis/.pending-record-session/` 下生成 pending 文件
4. 失败时输出 `TRELLIS_AUTO_ESCALATE_COMMAND=...`，支持提权重试
5. `--resume` 为 commit-only 恢复：仅重试提交磁盘上已写入的元数据，不重跑 `add_session.py`
6. 恢复成功后自动清理 pending 文件及 body 旁路文件

**使用 `--resume`**：

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py --resume .trellis/.pending-record-session/<pending-file>
```

**限制**：
- `--resume` 为 commit-only，不会重新写入 journal / index.md（因为 `add_session.py --no-commit` 在首次尝试时已写入磁盘数据）
- 若首次尝试中 `add_session.py` 尚未写入任何数据（如 pre-check 阶段就失败了），恢复后 journal 中不会出现该 session 记录
- stdin 内容会保存在 pending 目录的 `.body.md` 旁路文件中，但 commit-only 恢复不会重新传递给 `add_session.py`
- 只有 commit-only 步骤失败才会生成 pending；pre-check 或 add_session 失败不生成（前者是前置条件不满足，后者是数据写入失败，两者都不适合通过提权重试恢复）
- post-check 失败也不生成 pending：commit 成功后 post-check 失败说明有其他未预期的脏变更，不是只读环境问题

**`add_session.py` 边界说明**：

- `add_session.py` 自身也包含 readonly 检测和 pending 生成逻辑（`_ensure_record_session_resume_state` 等），但通过 `--no-commit` 调用时这些路径不会触发
- 如果不通过 helper 直接调用 `add_session.py`（不带 `--no-commit`），会走其自带的自动提交和恢复路径，产生独立的 pending 文件（不含 stdin body sidecar）
- 推荐始终通过 `record-session-helper.py` 调用，避免两套恢复路径并存

**archive 链基线依赖说明**：

- `task.py archive` 的自动提交仍由 Trellis 基线负责，workflow 不分发 `task.py` / `task_store.py`
- 若 archive 自动提交失败，建议升级目标项目的 Trellis 基线版本
- `record-session` 链的恢复机制仅覆盖 `record-session-helper.py` 管理的 `.trellis/workspace` + `.trellis/tasks` 提交

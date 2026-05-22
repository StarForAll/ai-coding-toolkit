<!-- finish-work-strong-gate-step-replacement -->

**⚠️ 强门禁模式下 Step 2 误导语言修正说明**：SKILL.md 正文 Step 2 中包含与强门禁模型矛盾的 archive 语义措辞。在嵌入安装时，安装器必须对 Step 2 中的以下语句进行替换：

| 原文（误导措辞） | 替换为（强门禁对齐措辞） |
|---|---|
| `current active task is always archived in Step 3 regardless` | `current active task is NOT archived in finish-work; archiving is deferred to the record-session stage` |
| `archive them too in this round` | `note them for archiving in the record-session stage` |

修正理由：强门禁模式下 close-out 链路为 **finish-work → delivery → record-session**。`finish-work` 不执行任何 archive 操作；archive 仅在 `record-session` 阶段执行。Step 2 中任何暗示"在本轮/archive"的措辞必须替换为"延期至 record-session"的对齐表述。

安装器实现提示：在处理 Step 2 正文时，按上述映射表对两处短语执行文本替换即可，无需替换整个 Step 2 段落。

---

**⚠️ 强门禁模式下 Step 3/4 替换说明**：本补丁内容替换 SKILL.md 正文中的旧 Step 3（Archive task(s)）和 Step 4（Record session journal）。在嵌入安装时，安装器必须将 SKILL.md 中从 "## Step 3: Archive task(s)" 到 "## Step 4: Record session journal" 结束的整个段落替换为以下内容：

> **Step 3**: 确认 `finish-work-checklist.md` 已落盘 → 进入 delivery 阶段
>
> archive 和 add_session 移至 `record-session` 阶段执行。finish-work 在强门禁模式下**不执行** `task.py archive` 或 `add_session.py`。

收尾链路为：**finish-work → delivery → record-session**。`finish-work` 只负责提交检查清单与收尾证据；`delivery` 负责验收、交付物与所有权证明；`record-session` 才执行 `task.py archive` + `add_session.py`。

---

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

当前 workflow 的 close-out 遵循三阶段顺序：**finish-work → delivery → record-session**。

- `finish-work` **只负责**提交检查清单与收尾证据，**不执行** `task.py archive` 或 `add_session.py`
- `delivery` 负责验收、交付物确认与所有权证明（外包 profile）
- `record-session` 才执行 `task.py archive` + `add_session.py`，完成最终归档

**⚠️ 本补丁覆盖 SKILL.md 正文中的旧 Step 3/4 语义**：finish-work 在强门禁模式下不执行 archive / add_session。替换为：

> **Step 3**: 确认 `finish-work-checklist.md` 已落盘 → 进入 delivery 阶段

archive 和 add_session 移至 `record-session` 阶段执行。

进入 `/trellis:finish-work` 前，至少确认：

- [ ] 当前 task 已形成或更新 `finish-work-checklist.md`（见上方 §1）
- [ ] 不在此阶段执行 `task.py archive` — archive 移至 `record-session` 阶段
- [ ] 若目标项目的 `.trellis/` 元数据自动提交失败，按目标项目当前 Trellis 基线能力处理，不在 workflow 层额外发明 helper 分支

**archive 链基线依赖说明**：

- `task.py archive` 与 `add_session.py` 的自动提交均由 Trellis 基线负责，workflow 不分发 `task.py` / `task_store.py`
- 若 archive 或 `add_session.py` 的自动提交失败，建议先升级目标项目的 Trellis 基线版本

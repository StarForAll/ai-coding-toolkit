# /trellis:metadata-auto-commit

元数据自动提交辅助流程 —— 确保 `.trellis/` 目录的元数据变更被可靠地自动提交。

---

## 1. 目的与适用范围

### 1.1 解决的问题

在 AI 辅助开发工作流中，以下脚本会修改 `.trellis/` 目录的元数据文件：

- `task.py archive` —— 归档任务，移动 `.trellis/tasks/active/` → `.trellis/tasks/archive/`
- `add_session.py` —— 记录会话，追加 `.trellis/workspace/<developer>/journal-N.md`
- 其他元数据操作 —— 更新索引、统计等

**核心问题**：脚本输出"成功"不等于元数据已真实提交。若自动提交失败，会导致：
- 任务状态与实际不符
- 会话记录丢失
- 多开发者协作冲突

### 1.2 适用范围

| 场景 | 触发脚本 | 提交范围 |
|------|----------|----------|
| 任务归档 | `task.py archive <name>` | `.trellis/tasks/` |
| 会话记录 | `add_session.py` | `.trellis/workspace/`, `.trellis/tasks/` |
| 其他元数据操作 | 各类元数据脚本 | `.trellis/` 相关目录 |

---

## 2. 核心原则

### 2.1 脚本输出 ≠ 实际完成

- 不要仅凭脚本输出的 "task archived" 或 "session added successfully" 判定完成
- 脚本执行成功仅表示**尝试**了自动提交，不代表**实际**提交成功

### 2.2 git 状态是唯一可信来源

- 自动提交后，必须通过 `git status --short` 验证目标目录是否已清空
- 预期输出：**空**（无任何变更）

### 2.3 失败必须阻断流程

- 若 `.trellis/` 目录仍有未提交的变更，视为元数据操作未完成
- 必须先解决失败原因，才能继续后续流程

---

## 3. 自动提交流程

### 3.1 实现机制

```python
# .trellis/scripts/common/git.py::auto_commit_paths()
def auto_commit_paths(paths: list[str], cwd: Path, commit_msg: str) -> tuple[str, str]:
    """
    Returns:
        ("committed", "")  —— 成功创建提交
        ("clean", "")      —— 无变更需要提交
        ("failed", "<reason>") —— 失败，附带原因
    """
```

流程：
1. `git add -A -- <paths>` —— 暂存目标路径
2. `git diff --cached --quiet -- <paths>` —— 检查是否有 staged 变更
3. `git commit -m <msg>` —— 创建提交

### 3.2 返回状态处理

| 状态 | 含义 | 处理方式 |
|------|------|----------|
| `committed` | 成功创建新提交 | 流程正常完成 |
| `clean` | 无变更需要提交 | 流程正常完成（幂等） |
| `failed` | 提交失败 | 必须中断流程，排查原因 |

---

## 4. 校验清单

### 4.1 任务归档后的校验

```bash
# 执行归档
python3 ./.trellis/scripts/task.py archive <task-name>

# 校验：.trellis/tasks 目录应为空
git status --short .trellis/tasks
```

**预期输出**：空（无任何内容）

### 4.2 会话记录后的校验

```bash
# 执行记录
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2"

# 校验：workspace 和 tasks 目录应为空
git status --short .trellis/workspace .trellis/tasks
```

**预期输出**：空（无任何内容）

### 4.3 快速校验命令

```bash
# 统一校验（推荐）
git status --short .trellis/workspace .trellis/tasks
```

---

## 5. 失败处理

### 5.1 常见失败原因

| 原因 | 症状 | 解决方案 |
|------|------|----------|
| git add 失败 | 权限不足、路径不存在 | 检查文件权限，确认路径正确 |
| git commit 失败 | 作者信息缺失、pre-commit hook 失败 | 配置 git user，检查 hook |
| 磁盘/IO 错误 | 写入失败、磁盘满 | 检查磁盘空间，重试 |

### 5.2 诊断步骤

```bash
# 1. 查看详细状态
git status .trellis/

# 2. 查看 staged 变更
git diff --cached .trellis/

# 3. 手动尝试提交（查看错误信息）
git add .trellis/workspace .trellis/tasks
git commit -m "debug: manual commit"
```

### 5.3 修复与重试

1. **解决根本原因**（权限、配置、磁盘等）
2. **手动提交**（如需立即恢复）：
   ```bash
   git add .trellis/workspace .trellis/tasks
   git commit -m "chore(trellis): manual metadata commit"
   ```
3. **验证修复**：重新运行校验命令，确认输出为空

---

## 6. 集成点

### 6.1 在 delivery 阶段的调用

在 `/trellis:delivery` 的 Step 10（收尾记录校验）中：
- 执行 `record-session` 前确认代码已提交
- 执行后必须校验 `.trellis/` 元数据已自动提交

参见：[delivery.md Step 10](./delivery.md#step-10-收尾记录校验)

### 6.2 在 record-session 中的调用

`add_session.py` 自动调用 `auto_commit_paths()` 提交 `.trellis/workspace` 和 `.trellis/tasks` 的变更。

参见：[record-session Skill](../../../../../.agents/skills/record-session/SKILL.md)

### 6.3 在 task archive 中的调用

`task.py archive` 自动调用 `auto_commit_paths()` 提交 `.trellis/tasks` 的变更。

---

## 7. 相关文件

| 文件 | 用途 |
|------|------|
| `.trellis/scripts/common/git.py` | `auto_commit_paths()` 实现 |
| `.trellis/scripts/task.py` | 任务管理，含归档功能 |
| `.trellis/scripts/add_session.py` | 会话记录，含自动提交 |
| `.agents/skills/record-session/SKILL.md` | 会话记录 Skill |

---

## 下一步

完成元数据自动提交校验后：

| 场景 | 推荐命令 |
|------|----------|
| 交付阶段完成 | `/trellis:record-session` |
| 需要更新规范 | `/trellis:update-spec` |
| 交付物检查 | 参见 [delivery.md](./delivery.md) |

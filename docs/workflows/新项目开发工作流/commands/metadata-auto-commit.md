# /trellis:metadata-auto-commit

元数据自动提交辅助流程 —— 约束 `.trellis/` 元数据在“当前任务收尾”场景中的自动提交边界。

---

## 1. 目的与定位

本流程解决的不是“如何让脚本顺手 commit 一下”，而是：

- 避免把不该提交的代码或元数据误带进自动提交
- 避免把“脚本打印成功”误当成“元数据已真实闭环”
- 避免在非当前任务、批量补记、补归档等场景中扩大自动提交边界

**结论先行**：

- 自动 commit 只服务于**当前执行任务已完成后的收尾**
- 任何超出该边界的场景，默认不允许自动 commit
- 若 git 状态未清空，视为收尾未完成

---

## 2. 适用范围

### 2.1 允许自动 commit 的场景

| 场景 | 触发脚本 | 提交目标 | 约束 |
|------|----------|----------|------|
| 当前任务归档 | `task.py archive <current-task>` | `.trellis/tasks/` 及归档副作用文件 | 仅当前任务完成后允许 |
| 当前任务会话记录 | `add_session.py` | `.trellis/workspace/`, `.trellis/tasks/` | 仅当前任务完成后允许 |

### 2.2 不允许自动 commit 的场景

- 非当前任务的归档、补归档、批量归档
- 进行中任务的状态推进或 phase 变更
- `set-branch` / `set-base-branch` / `set-scope` 这类任务配置修改
- `.trellis/.current-task` 的普通切换
- 任何“只是顺手修改了 `.trellis/`，但不属于当前任务完成收尾”的动作

### 2.3 例外模式

`--no-commit` 只能视为**调试 / 例外模式**：

- 它不是正式闭环路径
- 使用后不能宣称“record-session 已完成”或“archive 已完成”
- 使用后必须由操作者自行处理后续 git 校验与提交

---

## 3. P0 规则

### 3.1 当前任务边界

P0 必须满足：

- 自动 commit 前必须确认目标任务就是 `.trellis/.current-task` 指向的当前任务
- 若检测到“已完成但非当前任务”的归档或收尾意图，必须**硬阻断**
- 不允许通过自动 commit 顺手清理其他任务的元数据

### 3.2 staged 污染硬阻断

P0 必须满足：

- 自动 commit 前必须检查 index / staged 区
- 若 staged 区混入了非本次元数据提交目标的变更，必须**硬阻断**
- 不接受仅靠文档提醒“请先清空 staged 区”；应在脚本层明确拒绝

**原因**：
当前自动提交流程最终会执行 `git commit -m <msg>`。若 index 已混入其他 staged 变更，这些变更会被一并提交，风险高于“提交失败”。

### 3.3 git 状态是唯一可信校验

- 不要仅凭 `task archived` 或 `session added successfully` 判定完成
- 自动提交后必须检查目标 `.trellis/` 路径是否已清空
- 若校验后仍有目标路径变更，视为收尾失败

---

## 4. 当前实现与文档边界

本文件描述的是**当前工作流要求 + P0/P1 约束**，不是对现状实现的美化。

### 4.1 当前已确认现状

- `add_session.py` 已使用共享自动提交 helper
- `task.py archive` 当前仍有独立自动提交逻辑，失败语义未完全统一
- 归档时除 `.trellis/tasks/` 外，还可能影响 `.trellis/.current-task`

### 4.2 当前文档必须避免的误导

- 不要写成任务从 `.trellis/tasks/active/` 移动到 `archive/`
- 不要写成 `task.py archive` 已与 `add_session.py` 完全共享同一自动提交语义
- 不要把“其他元数据脚本”笼统纳入自动 commit 范围

### 4.3 P1 补强项

P1 再处理：

- `task.py archive` 自动提交失败强阻断
- `archive` 与 `add_session` 的失败语义统一
- 共享 helper 进一步收敛

---

## 5. 执行前检查

### 5.1 任务边界检查

执行 `task.py archive` 或 `add_session.py` 前，必须先确认：

- 当前任务已完成
- 待归档 / 待收尾的目标就是当前任务
- 不是在补记其他任务、批量处理多个任务、或顺手清理历史任务

### 5.2 git 检查

执行前至少确认：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py \
  --mode archive --check pre --task-dir <current-task>

python3 docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py \
  --mode record-session --check pre

git status --short
git diff --cached --name-only
```

重点检查：

- staged 区是否已经混入无关变更
- 本次操作是否会把非目标内容带入自动提交

---

## 6. 校验清单

### 6.1 当前任务归档后的校验

```bash
python3 ./.trellis/scripts/task.py archive <current-task>

python3 docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py \
  --mode archive --check post

git status --short .trellis/tasks
git status --short .trellis/.current-task
```

**预期输出**：空

说明：

- 若 `.trellis/tasks` 仍有变更，归档未闭环
- 若 `.trellis/.current-task` 仍有异常残留，说明当前任务指针未正确清理

### 6.2 当前任务会话记录后的校验

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2"

python3 docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py \
  --mode record-session --check post

git status --short .trellis/workspace .trellis/tasks
```

**预期输出**：空

### 6.3 收尾总校验

```bash
git status --short .trellis
```

用途：

- 当局部校验有歧义时，用于确认 `.trellis/` 范围内是否仍有遗漏的副作用文件

---

## 7. 失败处理

### 7.1 常见失败类型

| 类型 | 含义 | P0 处理 |
|------|------|----------|
| staged 污染 | staged 区已有非目标变更 | 硬阻断，先清理 |
| 非当前任务收尾 | 目标不是当前任务 | 硬阻断，拒绝自动 commit |
| git add / commit 失败 | 权限、hook、作者信息等问题 | 中断并排查 |
| `--no-commit` 例外模式 | 明确跳过自动 commit | 不得宣称闭环完成 |

### 7.2 诊断步骤

```bash
# 1. 看整体状态
git status --short .trellis

# 2. 看 staged 区到底有什么
git diff --cached --name-only

# 3. 看当前任务指针
cat .trellis/.current-task 2>/dev/null || true
```

### 7.3 恢复原则

1. 先确认边界是否正确：
   - 是否真的是当前任务
   - 是否真的进入了完成收尾阶段
2. 再清理 staged 污染或修复 git 失败原因
3. 最后重新执行局部校验与总校验

---

## 8. 集成点

### 8.1 在 delivery 阶段的调用

`/trellis:delivery` 的收尾阶段必须把本流程当作门禁：

- 当前任务未完成，不进入自动提交
- 目标不是当前任务，不进入自动提交
- staged 区不干净，不进入自动提交

推荐显式执行：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py \
  --mode record-session --check pre
```

### 8.2 在 record-session 中的调用

`add_session.py` 的自动提交只应被视为**当前任务收尾的一部分**，而不是通用 `.trellis` 提交器。

### 8.3 在 task archive 中的调用

`task.py archive` 只有在归档目标就是当前任务时，才允许进入自动提交路径。

---

## 9. 相关文件

| 文件 | 用途 |
|------|------|
| `docs/workflows/新项目开发工作流/commands/shell/metadata-autocommit-guard.py` | Guard 检查脚本 |
| `docs/workflows/新项目开发工作流/commands/shell/metadata-archive-wrapper.py` | 归档一键执行 Wrapper |
| `docs/workflows/新项目开发工作流/commands/shell/metadata-record-session-wrapper.py` | 会话记录一键执行 Wrapper |
| `.trellis/scripts/task.py` | 项目脚本：任务管理入口（不可修改） |
| `.trellis/scripts/add_session.py` | 项目脚本：会话记录（不可修改） |

---

## 10. 简化工作流（Convenience Wrappers）

由于项目脚本 `.trellis/scripts/` 不可修改，工作流提供了 Python 简化脚本，自动串联 guard 检查与实际执行：

### 10.1 归档 Wrapper

```bash
# 归档当前任务（自动 guard 检查）
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-archive-wrapper.py <task-name>

# 跳过自动提交
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-archive-wrapper.py <task-name> --no-commit
```

**自动执行**:
1. Guard pre-check（当前任务边界 + staged 污染检测）
2. `task.py archive`（归档）
3. Guard post-check（验证 git 已清空）

### 10.2 记录会话 Wrapper

```bash
# 记录会话（自动 guard 检查）
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-record-session-wrapper.py \
  --title "Session Title" \
  --commit "hash1,hash2"

# 跳过自动提交
python3 docs/workflows/新项目开发工作流/commands/shell/metadata-record-session-wrapper.py \
  --title "Session Title" \
  --commit "hash" \
  --no-commit
```

**自动执行**:
1. Guard pre-check（当前任务边界 + staged 污染检测）
2. `add_session.py`（记录）
3. Guard post-check（验证 git 已清空）

### 10.3 为什么需要 Wrapper

| 问题 | 解决方案 |
|------|----------|
| 项目脚本不可修改 | 在 docs/workflows 下添加 wrapper |
| 手动执行容易遗漏步骤 | Wrapper 自动串联 guard 检查 |
| 需记忆多个命令 | 单一入口，自动完成全流程 |

---

## 下一步

**当前约束**：项目脚本 `.trellis/scripts/` 不可修改

因此采用文档层增强方案：

- ✅ Guard 脚本已实现（`metadata-autocommit-guard.py`）
- ✅ Wrapper 脚本已实现（`metadata-*-wrapper.py`）
- ✅ 手动执行流程已文档化

开发者可选择：

1. **推荐**：使用 Wrapper 一键执行
2. **高级**：手动执行 guard 检查 + 项目脚本

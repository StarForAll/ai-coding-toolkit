---
name: record-session
description: 工作流最终收尾 — 归档任务并记录会话。触发词：归档任务、记录会话、收尾完成、结束任务
---

# /trellis:record-session — 工作流最终收尾

> **Workflow Position**: 收尾链路终端 → 前: `/trellis:delivery` → 后: 无（工作流周期完成）
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:record-session`） · ✅ OpenCode（TUI: `/trellis:record-session`；CLI: `trellis/record-session`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发）

> **Strong Gate**: 本阶段是强门禁模型的终态阶段。完成后工作流周期结束。

---

## When to Use (自然触发)

- 仅当当前路由已在 `delivery` 之后，且准备执行最终归档与会话记录时使用
- "归档这个任务"
- "记录一下这次会话"
- "收尾完成了"
- "结束当前任务"

---

## 前置条件

进入本阶段前，必须确认：

- [ ] `/trellis:delivery` 阶段已完成
- [ ] `delivery/acceptance.md` 已记录验收结论
- [ ] 当前 workflow 收尾链路已按 **finish-work → delivery → record-session** 顺序执行
- [ ] 当前 task 是本次要归档的目标，不混入其他任务

### 门禁校验

先检查当前路由是否已经进入 `record-session`：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route <task-dir> --project-root <project-root>
```

再校验当前阶段产物是否满足终态收尾门禁：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
```

这里的 `validate` 只负责确认：当前 task 已满足 **进入 `record-session` 之前** 的 `delivery` 完整性门禁，尤其是交付物、外包交付控制、归属证明/水印验证等产物是否已经齐全。

它**不代表** `archive`、`add_session.py`、`.trellis/workspace` / `.trellis/tasks` / `.trellis/.runtime/sessions` 的元数据清理已经完成；这些属于下面 Step 2-4 的真实收尾动作与后置校验。

若 `route` 仍显示当前阶段是 `delivery` / `finish-work` / 其他阶段，或 `validate` 报告缺少交付产物，则不得直接执行本命令中的 archive / add_session 步骤。先回到缺失阶段补齐门禁。

---

## 流程

### Step 1: 确认 delivery 阶段完成

- [ ] 验收结果已记录
- [ ] 交付物已生成并确认
- [ ] 无未处理的 P0/P1 缺陷

### Step 2: 归档当前任务

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

如果当前任务是子任务，还需同步更新父任务协调记录（已完成的边界、待完成的边界、下一个可选子任务）。

### Step 3: 记录会话

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"
```

### Step 4: 验证元数据清理

```bash
git status --short .trellis/workspace .trellis/tasks
```

判定规则：

- `workflow-state.py validate <task-dir>` 返回 0：说明允许进入 `record-session`，**不等于** close-out 已完成
- `archive` 与 `add_session.py` 都返回 0：会话记录与元数据闭环完成
- 任一步返回非 0：close-out 不算完成，先处理 Trellis 基线写入失败原因
- `git status --short .trellis/workspace .trellis/tasks` 输出应为空

---

## 约束

- **终态入口，不是快捷跳转**：在强门禁流里，`record-session` 只应作为 `delivery` 之后的终态执行卡使用；不要把它当成跳过 `delivery` 的会话记录快捷入口
- **归档顺序**：先 `task.py archive`，再 `add_session.py`
- **范围锁定**：只归档当前任务，不批量处理其他任务
- **禁止回写**：不为补齐规则或整理台账而回写旧任务、旧会话记录或已归档目录
- **禁止混入**：staged 区不得混入非目标变更
- `archive` 与 `add_session.py` 的自动提交由 Trellis 基线负责，workflow 不分发 `task.py` / `task_store.py`

---

## 输出

- 任务状态变为 `completed` / `archived`
- 会话记录已写入
- `.trellis/workspace` 和 `.trellis/tasks` 元数据清理干净

---

## 下一步推荐

**当前状态**: 工作流周期已完成，任务已归档，会话已记录。

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 开始新任务 | `task.py create "<title>"` | 描述新任务意图 | 新的工作流周期 |
| 继续其他任务 | `/trellis:continue` | 触发 `trellis-continue` skill | 选择或恢复另一个任务 |
| 不确定 | 等待用户指示 | 等待用户指示 | 工作流已结束，无自动推进 |

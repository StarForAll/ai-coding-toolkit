## Phase Router `[AI]`

### 核心定位

收到 `/trellis:start` 后，**只做当前已确认阶段的识别与重入**，不做跨阶段自动推进。
采用强门禁模型：每个阶段完成后必须先进入 `awaiting_user_confirmation`，用户确认后才能切到下一阶段。

### 执行步骤

1. 获取上下文：

```bash
python3 ./.trellis/scripts/get_context.py
```

2. 计算路由目标：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route <task-dir> --project-root <project-root>
```

若当前无 `.current-task`（首次入口或恢复场景），可省略 `<task-dir>`：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route --project-root <project-root>
```

3. 根据 JSON 输出的 `action` 字段执行：

| action | 含义 | 执行动作 |
|--------|------|---------|
| `first_entry` | 首次进入新项目 | 路由到 `/trellis:feasibility` |
| `resume_with_assessment` | 有效 assessment 存在 | 路由到 `/trellis:brainstorm` |
| `reenter` | 重入当前阶段 | 路由到 `/trellis:<target>`（`target` 字段即目标阶段） |
| `awaiting_confirmation` | 阶段完成等待确认 | 展示已完成/未完成/缺失项，等用户确认 |
| `blocked` | 执行阶段存在阻塞条件 | 逐项展示 `blockers`，不继续推进 |
| `recovery_needed` | 无法确定当前任务 | 要求用户明确当前任务 |
| `repair_needed` | 状态文件缺失或损坏 | 运行 `workflow-state.py repair`，展示推断结果请求确认 |
| `embed_invalid` | 嵌入状态无效 | 停止；提示用户检查安装完整性 |

4. 若路由输出包含 `blockers`，逐项展示阻断原因，不继续推进。

### 实施阶段额外约束

1. **一次只推进一个具体叶子 task** — 不能把多个 task 混在同一上下文里一起做
2. **每次进入实现前自动执行 before-dev** — 不要求用户显式输入 `/trellis:before-dev`；产出落到 `$TASK_DIR/before-dev.md`
3. **串行不等于自动续跑** — 前一 task 完成后仍需再次进入 `/trellis:start`，不能自动开始下一个
4. **前端视觉首版 task** — `UI -> 首版代码界面` 不能使用 Codex 作为主执行器；完成时必须沉淀 `design/frontend-ui-spec.md`

### 下一步推荐输出格式

**每个命令执行完毕后，AI 必须在末尾输出「下一步推荐」区块**。

入口表达约束：

- Claude Code：继续使用 `/trellis:xxx`
- OpenCode：TUI 使用 `/trellis:xxx`；CLI 可补 `trellis/xxx`
- Codex：若同一阶段语义被复用到 skills / AGENTS / hooks 侧，必须改写为"自然语言意图 + 对应 skill 名"

```markdown
## 下一步推荐

**当前状态**: <一句话描述当前已确认阶段 / 当前子块 / 是否在等待确认>

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 继续当前阶段当前子块 | `/trellis:xxx` | 自然语言继续当前阶段，或显式触发 `xxx` skill | **默认推荐**。不跨阶段，只重入当前已确认阶段 |
| 在当前阶段切到另一个已允许子块 | `/trellis:xxx` | 自然语言继续当前阶段，或显式触发 `xxx` skill | 仍留在当前 stage，不得跨阶段 |
| 准备切到下一阶段 | `/trellis:xxx` | 自然语言说明要切到下一阶段，或显式触发 `xxx` skill | 仅在退出清单已完成且用户明确确认后才允许 |
| 不确定当前任务/状态 | `/trellis:start` | 描述当前状态恢复意图，或显式触发 `start` skill | 进入任务选择 / 状态恢复分支 |
```

## Phase Router `[AI]`

### 核心定位

收到 `/trellis:continue` 后，**只做当前已确认阶段的识别与重入**，不做跨阶段自动推进。legacy `/trellis:start` 仅用于旧目标项目兼容。
采用强门禁模型：每个阶段完成后必须先进入 `awaiting_user_confirmation`，用户确认后才能切到下一阶段。

**⚠️ 旧 status 路由已废弃**：不再使用 `status=planning` / `status=in_progress` 做 Step 3 路由。强门禁模式下，路由依据 `workflow-state.json` 的 `stage` 字段，由 `workflow-state.py route` 命令计算。

### 执行步骤

1. 获取上下文：

```bash
python3 ./.trellis/scripts/get_context.py
```

2. 计算路由目标：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route <task-dir> --project-root <project-root>
```

若当前 session 已解析出 active task，或当前处于首次入口 / 恢复场景，可省略 `<task-dir>`：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py route --project-root <project-root>
```

3. 根据 JSON 输出的 `action` 字段执行：

| action | 含义 | 执行动作 |
|--------|------|---------|
| `entry_choice_required` | 当前 session 尚无 active task，且项目中也没有可继续任务 | 先判断当前意图。如果是 workflow / 项目只读分析、元审计或 A/A+ 纯分析，则保持 `no_task` 直接分析，不创建任务；如果是开始新的实现任务，再进入 `target` 对应的正式入口。若项目还没有可复用的有效 assessment，outsourcing profile 默认入口应先走 `/trellis:feasibility`；personal profile 的首次入口可直接进入 `/trellis:brainstorm`，但必须在该阶段补齐 assessment 基线；其他场景只有在 route 明确复用了现有 assessment 并允许继续 brainstorm 时，才进入 `/trellis:brainstorm`。若 route 同时给出 `profile_hint=unknown`，保持 `feasibility` 的保守回退，并先确认该项目到底按 outsourcing 还是 personal 处理；不要直接猜测可跳过 feasibility。不要期待存在公开的 `/trellis:implementation` 入口。 |
| `reenter` | 重入当前阶段 | 若 `target=implementation`，继续留在当前 `/trellis:continue` 入口并按下方“实施阶段额外约束”执行；其他阶段再路由到 `/trellis:<target>`（`target` 字段即目标阶段）。 |
| `awaiting_confirmation` | 阶段完成等待确认 | 展示已完成/未完成/缺失项，等用户确认 |
| `awaiting_confirmation_with_blockers` | 阶段已到确认点，但仍有阻塞项 | 展示 `blockers`，要求先补齐阻塞项，不能直接确认推进 |
| `blocked` | 执行阶段存在阻塞条件 | 逐项展示 `blockers`，不继续推进 |
| `context_needed` | 当前 task 不能继续直接执行 | 当前阶段要求 leaf task，但当前 task 含有 children；要求切到子任务，不能继续在 parent task 上推进 |
| `recovery_needed` | 当前 session 无法确定 active task | 要求用户明确当前任务 |
| `repair_needed` | 状态文件缺失或损坏 | 运行 `workflow-state.py repair`。若输出 `repair_ready`，在用户确认后再重写；若输出 `manual_confirmation_required`，必须先让用户明确当前已确认阶段。非执行阶段通常只需 `--stage <stage>`；若当前阶段是 `implementation`，还必须显式补齐 `--execution-authorized true` 与 `--transition-from <上一阶段>`，不能靠任务产物反推。 |
| `embed_invalid` | 嵌入状态无效 | 停止；提示用户检查安装完整性 |

4. 若路由输出包含 `blockers`，逐项展示阻断原因，不继续推进。

### 实施阶段额外约束

1. **一次只推进一个具体叶子 task** — 不能把多个 task 混在同一上下文里一起做
1.1. **implementation 的公开重入入口就是 `/trellis:continue`** — 它没有对称的 `/trellis:implementation` 命令；真正写代码时由 continue 在当前 task 上执行 implementation 内部链
2. **每次进入实现前自动执行 before-dev** — 不要求用户显式输入 `/trellis:before-dev`；产出落到 `$TASK_DIR/before-dev.md`
3. **串行不等于自动续跑** — 前一 task 完成后仍需再次进入 `/trellis:continue`，不能自动开始下一个
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
| 不确定当前任务/状态 | `/trellis:continue` | 描述当前状态恢复意图，或显式触发 `trellis-continue` skill | 进入任务选择 / 状态恢复分支 |
```

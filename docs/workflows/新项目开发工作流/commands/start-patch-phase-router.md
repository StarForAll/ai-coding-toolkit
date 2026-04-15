## Phase Router `[AI]`

### 核心定位

收到 `/trellis:start` 后，**只做当前已确认阶段的识别与重入**，不做跨阶段自动推进。

当前 workflow 采用 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md)：

- 当前阶段的唯一判定链：`.trellis/.current-task -> 当前叶子任务 -> $TASK_DIR/workflow-state.json`
- `.trellis/.current-task` 不能为空；为空时不允许自动识别阶段
- 只有当前执行中的叶子任务允许持有 `workflow-state.json`
- 每个阶段完成后都必须先进入 `awaiting_user_confirmation`，用户确认后才能切到下一阶段

建议先执行：

```bash
python3 ./.trellis/scripts/get_context.py
python3 .trellis/scripts/workflow/workflow-state.py validate <task-dir>
```

在当前源仓库维护 workflow 内容时，可直接使用：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/workflow-state.py validate <task-dir>
```

### 首次嵌入后的初始化门禁

如果当前项目刚完成自定义 workflow 嵌入，安装器应已先补齐需求发现基础资产，再进入常规阶段路由。

默认由安装脚本补充 `trellis-library` 的 `pack.requirements-discovery-foundation`。`/trellis:start` 在这里负责校验是否完整，不再要求用户手工复制资产或通过自然语言提示“补装”初始 spec。

最低要求至少覆盖：

- 需求发现核心规范
- PRD 文档规范
- 配套模板与 checklist

若命中安装不完整门禁，优先由维护者重新执行 workflow 安装脚本；若只需修复需求发现基线，也可直接执行：

```bash
python3 trellis-library/cli.py assemble \
  --target <project-root> \
  --pack pack.requirements-discovery-foundation \
  --auto
```

### 路由决策树（强门禁版）

```text
get_context.py + .current-task + workflow-state.json
    │
    ├── `.trellis/workflow-installed.json` 存在 + `.trellis/library-lock.yaml` 缺失或缺少最低资产集
    │   └── 先补齐安装基线；补齐后重新执行本决策树
    │
    ├── 无 `.current-task` + 用户描述的是新项目/新客户/首次立项
    │   └── 路由 → /trellis:feasibility
    │
    ├── 无 `.current-task` + 不是首次立项场景
    │   └── 停止自动路由；先要求用户明确当前任务，或恢复当前任务
    │
    ├── `.current-task` 为空 / 指向不存在 task / 当前 task 不是叶子任务
    │   └── 停止自动路由；先修复当前任务指针，再继续
    │
    ├── 当前 task 缺少 `workflow-state.json`
    │   └── 停止自动跨阶段推断；进入“状态恢复/初始化”分支
    │
    ├── `workflow-state.stage_status = awaiting_user_confirmation`
    │   └── 只重入当前 stage，展示已完成/未完成/缺失项；等待用户确认，不自动切换下一阶段
    │
    ├── `workflow-state.stage = feasibility`
    │   └── 重入 /trellis:feasibility
    │
    ├── `workflow-state.stage = brainstorm`
    │   └── 重入 /trellis:brainstorm
    │
    ├── `workflow-state.stage = design`
    │   └── 重入 /trellis:design
    │
    ├── `workflow-state.stage = plan`
    │   └── 重入 /trellis:plan
    │
    ├── `workflow-state.stage = test-first`
    │   └── 重入 /trellis:test-first
    │
    ├── `workflow-state.stage = implementation`
    │   └── 重入实施主链（仍需 before-dev 自动前置）
    │
    ├── `workflow-state.stage = project-audit`
    │   └── 重入 /trellis:project-audit
    │
    ├── `workflow-state.stage = check`
    │   └── 重入 /trellis:check
    │
    ├── `workflow-state.stage = review-gate`
    │   └── 重入 /trellis:review-gate
    │
    ├── `workflow-state.stage = finish-work`
    │   └── 重入 /trellis:finish-work
    │
    ├── `workflow-state.stage = delivery`
    │   └── 重入 /trellis:delivery
    │
    └── `workflow-state.stage = record-session`
        └── 重入 /trellis:record-session
```

### 实施主链的约束

进入实施阶段后，仍必须遵守以下规则：

1. **一次只推进一个具体叶子 task**
   - 不能把多个 task 混在同一上下文里一起做

2. **每次进入实现前都自动执行 before-dev**
   - 不要求用户显式输入 `/trellis:before-dev`
   - 但 `/trellis:start` 必须在真正实现前自动执行一次 before-dev 步骤

3. **before-dev 的输出落到 task 本地**
   - 自动生成或刷新：

```text
$TASK_DIR/before-dev.md
```

4. **task 级测试门禁不允许提前虚构**
   - `design` / `plan` 只定义项目级全局测试基线与任务图摘要
   - 具体 task 的测试门禁，必须在进入该 task 实现前补到 `before-dev.md`

5. **串行不等于自动续跑**
   - 即使前一个 task 已完成，也不会自动开始下一个
   - 仍需再次进入 `/trellis:start`，但只能重入当前已确认阶段，不能自动跨阶段

6. **前端视觉首版落地 task 有额外执行边界**
   - 若当前选定 task 是 `UI -> 首版代码界面`，Codex 不能作为主执行器
   - 该 task 必须改由 Claude Code / OpenCode 承担主执行入口
   - 该 task 完成时，必须同步沉淀 `design/frontend-ui-spec.md`
   - 后续前端视觉相关 task 默认都应把 `design/frontend-ui-spec.md` 作为统一约束来源

### 状态恢复分支

以下任一情况都不允许自动猜阶段，只能进入恢复分支：

- `.current-task` 缺失或为空
- `.current-task` 指向不存在任务
- 当前任务已有 children，不再是叶子任务
- 当前任务缺少 `workflow-state.json`
- `workflow-state.json` 与目标项目正式文档边界冲突

恢复分支只允许做三件事：

1. 明确当前正在执行的任务
2. 初始化或修复 `workflow-state.json`
3. 回到当前已确认阶段，而不是直接切到下一阶段

### 自然语言触发词

| 用户说 | 触发命令 |
|-------|---------|
| "我有个新项目想法" "帮我评估一下这个需求" "这个项目能做吗" | `/trellis:feasibility` |
| "帮我梳理需求" "我还不太确定要做什么" "需要讨论一下方案" | `/trellis:brainstorm` |
| PRD 已冻结后说 "这个功能再加一个" "这个页面流程改一下" "这个接口字段要调整" "这个验收标准我想改" "这个功能先不做了" | [需求变更管理执行卡](../需求变更管理执行卡.md) |
| "开始设计" "画个架构图" "需要做技术选型" "出个设计方案" | `/trellis:design` |
| "拆一下任务" "做个工作计划" "把需求分解成小任务" | `/trellis:plan` |
| "先写测试" "用 TDD 方式" "测试先行" | `/trellis:test-first` |
| "开始写代码" "实现这个功能" "动手做吧" | 实施阶段（仅在 `workflow-state.stage = implementation` 时允许重入） |
| "做项目全局审查" "全局代码审查" "代码查缺补漏" "项目审计" "project-audit" | `/trellis:project-audit` |
| "检查一下这次改动" "对照 spec 看看" "做一轮质量检查" | `/trellis:check` |
| "补充审查一下" "让其他 CLI 看一下" "多人审查" "进入 review-gate" | `/trellis:review-gate` |
| "准备交付" "跑一下验收" "整理交付物" "项目收尾" | `/trellis:delivery` |
| "写代码前先看看规范" "读一下规范" "开发前准备" | `/trellis:before-dev` |

### 关于 `/trellis:before-dev` 的边界

- 它仍然保留为显式入口，供人工或 AI 在需要时单独重入
- 但当前 workflow 的默认主链**不要求用户显式输入它**
- 在默认主链中，`/trellis:start` 会自动执行 before-dev 步骤并落地 `before-dev.md`
- 手动单独调用 `/trellis:before-dev` 时，仍按 Trellis 基线语义理解为“读规范 / 注入项目知识”；**不要默认假设它单独调用时也会创建 `before-dev.md`**
- `before-dev.md` 的生成或刷新，是当前 workflow 在 `/trellis:start` 主链里的自动步骤保证的

### 执行状态边界

> 下列 `task_plan.md`、`before-dev.md`、`workflow-state.json` 都属于“目标项目采用 Trellis 任务资产模型时”的推荐判定口径。
> 若目标项目未采用这套文件结构，应保留阶段语义与前后依赖，不应把这些文件名误写成所有项目的硬前提。

- `task_plan.md`：摘要层，不再承载实时执行矩阵
- `before-dev.md`：当前 task 进入实现前的有效门禁快照
- `workflow-state.json`：当前叶子任务的强门禁阶段状态
- 真实执行状态：以 `.current-task`、叶子任务 `task.json`、`workflow-state.json`、`check.md` 等任务产物为准

### 下一步推荐输出格式

**每个命令执行完毕后，AI 必须在末尾输出「下一步推荐」区块**。

入口表达约束：

- Claude Code：继续使用 `/trellis:xxx`
- OpenCode：TUI 使用 `/trellis:xxx`；CLI 可补 `trellis/xxx`
- Codex：若同一阶段语义被复用到 skills / AGENTS / hooks 侧，必须改写为“自然语言意图 + 对应 skill 名”

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

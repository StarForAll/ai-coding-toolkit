
## Phase Router `[AI]`

### 核心逻辑

收到 `/trellis:start` 后，**先检测上下文再决定路由**：

```bash
python3 ./.trellis/scripts/get_context.py
```

### 首次嵌入后的初始化门禁

如果当前项目刚完成自定义工作流嵌入，安装器应已先通过脚本补齐需求发现基础资产，再进入常规阶段路由。

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

### 路由决策树

```
get_context.py 输出
    │
    ├── `.trellis/workflow-installed.json` 存在 + `.trellis/library-lock.yaml` 缺失或缺少最低资产集
    │   └── 先补齐安装基线；补齐后重新执行本决策树
    │
    ├── 无当前任务 + 用户描述新项目
    │   └── 路由 → /trellis:feasibility
    │
    ├── 新项目 / 新客户需求 + 已有任务，但缺少有效 `assessment.md`
    │   └── 路由 → /trellis:feasibility
    │
    ├── 有任务 + 无 PRD 或 PRD 未冻结
    │   └── 路由 → /trellis:brainstorm
    │
    ├── PRD 已冻结，但缺少 `docs/requirements/customer-facing-prd.md` 或 `docs/requirements/developer-facing-prd.md`
    │   └── 路由 → /trellis:brainstorm
    │
    ├── PRD 冻结 + 无设计文档
    │   └── 路由 → /trellis:design
    │
    ├── 设计完成 + 当前项目 `.trellis/spec/` 未完成对齐
    │   └── 先补 spec 对齐，再重新执行本决策树
    │
    ├── 设计完成 + 无 task_plan.md
    │   └── 路由 → /trellis:plan
    │
    ├── 已存在 task_plan.md，但尚未拆出真实 Trellis task / child task
    │   └── 路由 → /trellis:plan（不要直接进入实现）
    │
    ├── 已存在待执行的真实 Trellis task
    │   └── 进入实施主链：
    │       1. 选定本轮唯一 task
    │       2. 自动执行 before-dev
    │       3. 生成或刷新 `$TASK_DIR/before-dev.md`
    │       4. 根据 before-dev.md 补 task 级测试门禁
    │       5. 再进入实现
    │
    ├── 全部代码相关 task 已完成，且 PROJECT-AUDIT 未完成
    │   └── 路由 → /trellis:project-audit
    │
    ├── 代码实现完成 + 无 check.md
    │   └── 路由 → /trellis:check
    │
    ├── 质量检查完成
    │   └── 路由 → /trellis:finish-work（默认）/ /trellis:review-gate（条件触发）
    │
    └── 用户要求继续/跳到某阶段
        └── 直接跳转到指定命令
```

### 实施主链的约束

进入实现阶段后，必须遵守以下规则：

1. **一次只推进一个具体 task**
   - 不能把多个 task 混在同一上下文里一起做

2. **每次进入实现前都自动执行 before-dev**
   - 不要求用户显式输入 `/trellis:before-dev`
   - 但 `/trellis:start` 必须在真正实现前自动执行一次 before-dev 步骤

3. **before-dev 的输出落到 task 本地**
   - 自动生成或刷新：

```text
$TASK_DIR/before-dev.md
```

   - 它记录本次进入实现前的：
     - 适用 spec / guides
     - 项目级全局测试基线中当前 task 必须继承的项
     - 当前 task 新补充的测试门禁
     - 开始实现前必须满足的条件

4. **task 级测试门禁不允许提前虚构**
   - `design` / `plan` 只定义项目级全局测试基线与任务图摘要
   - 具体 task 的测试门禁，必须在进入该 task 实现前补到 `before-dev.md`

5. **串行不等于自动续跑**
   - 即使前一个 task 已完成，也不会自动开始下一个
   - 仍需再次进入 `/trellis:start`，明确当前要做哪个 task

6. **前端视觉首版落地 task 有额外执行边界**
   - 若当前选定 task 是 `UI -> 首版代码界面`，Codex 不能作为主执行器
   - 该 task 必须改由 Claude Code / OpenCode 承担主执行入口
   - 该 task 完成时，必须同步沉淀 `design/frontend-ui-spec.md`
   - 后续前端视觉相关 task 默认都应把 `design/frontend-ui-spec.md` 作为统一约束来源

### 自然语言触发词

| 用户说 | 触发命令 |
|-------|---------|
| "我有个新项目想法" "帮我评估一下这个需求" "这个项目能做吗" | `/trellis:feasibility` |
| "帮我梳理需求" "我还不太确定要做什么" "需要讨论一下方案" | `/trellis:brainstorm` |
| PRD 已冻结后说 "这个功能再加一个" "这个页面流程改一下" "这个接口字段要调整" "这个验收标准我想改" "这个功能先不做了" | [需求变更管理执行卡](../需求变更管理执行卡.md) |
| "开始设计" "画个架构图" "需要做技术选型" "出个设计方案" | `/trellis:design` |
| "拆一下任务" "做个工作计划" "把需求分解成小任务" | `/trellis:plan` |
| "先写测试" "用 TDD 方式" "测试先行" | `/trellis:test-first` |
| "开始写代码" "实现这个功能" "动手做吧" | 实施阶段（本命令 Task Workflow） |
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

> 下列 `task_plan.md` 与 `before-dev.md` 都属于“目标项目采用 Trellis 任务资产模型时”的推荐判定口径。
> 若目标项目未采用这套文件结构，应保留阶段语义与前后依赖，不应把这些文件名误写成所有项目的硬前提。

- `task_plan.md`：摘要层，不再承载实时执行矩阵
- `before-dev.md`：当前 task 进入实现前的有效门禁快照
- 真实执行状态：以 Trellis task、`.current-task`、`task.json`、`check.md` 等任务产物为准

### 下一步推荐输出格式

**每个命令执行完毕后，AI 必须在末尾输出「下一步推荐」区块**。

入口表达约束：

- Claude Code：继续使用 `/trellis:xxx`
- OpenCode：TUI 使用 `/trellis:xxx`；CLI 可补 `trellis/xxx`
- Codex：若同一阶段语义被复用到 skills / AGENTS / hooks 侧，必须改写为“自然语言意图 + 对应 skill 名”

```markdown
## 下一步推荐

**当前状态**: <一句话描述>

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| <意图> | `/trellis:xxx` | 自然语言继续该阶段，或显式触发 `xxx` skill | **默认推荐**。<说明> |
| <意图> | `/trellis:yyy` | 自然语言转入对应阶段，或显式触发 `yyy` skill | <说明> |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
```


## Phase Router `[AI]`

### 核心逻辑

收到 `/trellis:start` 后，**先检测上下文再决定路由**：

```bash
python3 ./.trellis/scripts/get_context.py
```

### 首次嵌入后的初始化门禁

如果当前项目刚完成自定义工作流嵌入，先补需求发现基础资产，再进入常规阶段路由。

默认补充 `trellis-library` 的 `pack.requirements-discovery-foundation`。

最低要求至少覆盖：

- 需求发现核心规范：
  - `spec.universal-domains.product-and-requirements.problem-definition`
  - `spec.universal-domains.product-and-requirements.scope-boundary`
  - `spec.universal-domains.product-and-requirements.requirement-clarification`
  - `spec.universal-domains.product-and-requirements.acceptance-criteria`
- PRD 文档规范：
  - `spec.universal-domains.product-and-requirements.prd-documentation-customer-facing`
  - `spec.universal-domains.product-and-requirements.prd-documentation-developer-facing`
- 配套产物：
  - `template.universal-domains.product-and-requirements.acceptance-criteria-template`
  - `template.universal-domains.product-and-requirements.customer-facing-prd-template`
  - `template.universal-domains.product-and-requirements.developer-facing-prd-template`
  - `checklist.universal-domains.product-and-requirements.acceptance-quality-checklist`
  - `checklist.universal-domains.product-and-requirements.customer-facing-prd-checklist`
  - `checklist.universal-domains.product-and-requirements.developer-facing-prd-checklist`

说明：以上 `spec.*` ID 指向 concern directory，实际展开为 `overview.md`、`scope-boundary.md`、`normative-rules.md`、`verification.md` 四个子文件。`pack.requirements-discovery-foundation` 默认还会带入示例与 `solution-comparison` 等扩展资产，但它们不是本门禁的最低集合。

### 触发门禁的具体检测信号

这一步不是 `get_context.py` 的内建字段，而是 `/trellis:start` 在读取上下文后追加的初始化检查。

当同时满足以下条件时，判定命中门禁：

- `.trellis/workflow-installed.json` 存在，说明自定义工作流已嵌入
- `.trellis/library-lock.yaml` 不存在，或其中缺少最低要求中的关键 asset id

可用下面的检查方式：

```bash
test -f .trellis/workflow-installed.json && (
  ! test -f .trellis/library-lock.yaml ||
  ! rg -q "spec.universal-domains.product-and-requirements.problem-definition" .trellis/library-lock.yaml ||
  ! rg -q "spec.universal-domains.product-and-requirements.prd-documentation-customer-facing" .trellis/library-lock.yaml ||
  ! rg -q "spec.universal-domains.product-and-requirements.prd-documentation-developer-facing" .trellis/library-lock.yaml
)
```

若目标项目已接入 `trellis-library` 组装流程，可先执行：

```bash
python3 trellis-library/cli.py assemble \
  --target <project-root> \
  --pack pack.requirements-discovery-foundation \
  --dry-run
```

确认无误后再正式执行导入，然后继续后续阶段路由。

若目标项目尚未接入 `trellis-library` CLI，则使用手动降级路径：

- 从 `trellis-library` 源库手动复制上述最低要求中的 `spec/`、`template/`、`checklist/` 资产到目标项目 `.trellis/` 对应目录
- 或由维护者先完成 `trellis-library` 接入，再重新执行本门禁

当前仓库未定义 `skip-library-gate` 一类的跳过配置；如无上述资产基线，不建议继续进入需求发现阶段。

### 路由决策树

```
get_context.py 输出
    │
    ├── `.trellis/workflow-installed.json` 存在 + `.trellis/library-lock.yaml` 缺失或缺少最低资产集
    │   └── 先补 `pack.requirements-discovery-foundation` 或手动补齐最低要求资产；补齐后重新执行本决策树
    │
    ├── 无当前任务 + 用户描述新项目
    │   └── 路由 → /trellis:feasibility（可行性评估）
    │
    ├── 有任务 + 无 PRD 或 PRD 未冻结
    │   └── 路由 → /trellis:brainstorm（需求发现）
    │
    ├── PRD 冻结 + 无设计文档
    │   └── 路由 → /trellis:design（设计阶段）
    │
    ├── 设计完成 + 技术架构已获用户确认 + 当前项目 `.trellis/spec/` 未完成对齐
    │   └── 先完成两项串行任务：
    │       1. 根据技术架构从 `trellis-library` 导入合适 spec 到项目 `.trellis/spec/`
    │       2. 基于项目作用/背景/技术架构完善当前项目 `.trellis/spec/`
    │       备注：这是补课门禁。补齐后重新执行决策树；若 `task_plan.md` 已存在，则按后续现状继续路由
    │
    ├── 设计完成 + 无 task_plan.md
    │   └── 路由 → /trellis:plan（任务拆解）
    │
    ├── task_plan.md 存在 + 无测试文件
    │   └── 路由 → /trellis:test-first（测试先行）
    │
    ├── 测试就绪 + 任务执行矩阵全部为 `已完成`
    │   └── 优先进入收尾链路：
    │       - 未完成自审/提交前检查 → /trellis:self-review 或 /trellis:finish-work
    │       - 已完成提交前检查 → /trellis:delivery
    │
    ├── 测试就绪 + 任务执行矩阵中存在 `可开始` 任务
    │   └── 路由 → 实施阶段（先读取执行矩阵，选定一个 `可开始` 任务并标记为 `进行中`）
    │
    ├── 测试就绪 + 任务执行矩阵中只剩 `等待中` 任务
    │   └── 暂不直接进入实施；先检查上游阻塞，必要时回到 /trellis:plan 调整拆分或依赖
    │
    ├── 测试就绪 + 代码未实现
    │   └── 路由 → 实施阶段（本命令 §Task Workflow；若已有任务执行矩阵，则按矩阵优先）
    │
    ├── 代码实现完成 + 无 self-review.md
    │   └── 路由 → /trellis:self-review（自审）
    │
    ├── 自审完成
    │   └── 路由 → /trellis:check → /trellis:finish-work
    │
    └── 用户要求继续/跳到某阶段
        └── 直接跳转到指定命令
```

### 自然语言触发词

| 用户说 | 触发命令 |
|-------|---------|
| "我有个新项目想法" "帮我评估一下这个需求" "这个项目能做吗" | `/trellis:feasibility` |
| "帮我梳理需求" "我还不太确定要做什么" "需要讨论一下方案" | `/trellis:brainstorm` |
| "开始设计" "画个架构图" "需要做技术选型" "出个设计方案" | `/trellis:design` |
| "拆一下任务" "做个工作计划" "把需求分解成小任务" | `/trellis:plan` |
| "先写测试" "用 TDD 方式" "测试先行" | `/trellis:test-first` |
| "开始写代码" "实现这个功能" "动手做吧" | 实施阶段（本命令 Task Workflow） |
| "自检一下" "对照 spec 看看" "有没有偏差" | `/trellis:self-review` |
| "准备交付" "跑一下验收" "整理交付物" | `/trellis:delivery` |
| "收尾" "提交前检查" "准备 commit" | `/trellis:finish-work` |
| "继续上次的工作" "上次做到哪了" | 继续现有任务 |

### 路由执行

检测到触发词后，**直接执行对应命令的完整流程**。

若命中“首次嵌入后的初始化门禁”，则不得跳过 PRD 规范基线补充动作。

若进入实施阶段，且 `task_plan.md` 已包含“任务执行矩阵”：

- 单线程模式下，先读取矩阵，定位一个 `当前状态=可开始` 的任务作为本轮实施对象
- 若采用 Git worktree 或已安装的 `/trellis:parallel` 并行实施，则可从“推荐并行组”中拆分多个 `可开始` 任务分别处理
- 将该任务状态改为 `进行中`
- 同步更新“执行安排”中的当前可开始任务、等待中任务、推荐并行组、串行主链
- 若不存在任何 `可开始` 任务，则不应盲目实现，应先分析阻塞原因

### 下一步推荐输出格式

**每个命令执行完毕后，AI 必须在末尾输出「下一步推荐」区块**。

```markdown
## 下一步推荐

**当前状态**: <一句话描述>

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| <意图> | `/trellis:xxx` | **默认推荐**。<说明> |
| <意图> | `/trellis:yyy` | <说明> |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
```

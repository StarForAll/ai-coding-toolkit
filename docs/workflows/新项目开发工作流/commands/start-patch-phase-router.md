
## Phase Router `[AI]`

### 核心逻辑

收到 `/trellis:start` 后，**先检测上下文再决定路由**：

```bash
python3 ./.trellis/scripts/get_context.py
```

### 路由决策树

```
get_context.py 输出
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
    ├── 设计完成 + 无 task_plan.md
    │   └── 路由 → /trellis:plan（任务拆解）
    │
    ├── task_plan.md 存在 + 无测试文件
    │   └── 路由 → /trellis:test-first（测试先行）
    │
    ├── 测试就绪 + 代码未实现
    │   └── 路由 → 实施阶段（本命令 §Task Workflow）
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


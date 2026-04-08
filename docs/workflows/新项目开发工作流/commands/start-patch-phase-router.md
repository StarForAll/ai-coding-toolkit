
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

若命中该门禁，说明安装不完整。优先由维护者重新执行 workflow 安装脚本；若只需修复需求发现基线，也可直接执行对应脚本：

```bash
python3 trellis-library/cli.py assemble \
  --target <project-root> \
  --pack pack.requirements-discovery-foundation \
  --auto
```

修复完成后，再继续后续阶段路由。

当前仓库未定义 `skip-library-gate` 一类的跳过配置；如无上述资产基线，不建议继续进入需求发现阶段。

### 路由决策树

```
get_context.py 输出
    │
    ├── `.trellis/workflow-installed.json` 存在 + `.trellis/library-lock.yaml` 缺失或缺少最低资产集
    │   └── 先重新执行安装脚本，或用 `trellis-library/cli.py assemble --pack pack.requirements-discovery-foundation --auto` 补齐；补齐后重新执行本决策树
    │
    ├── 无当前任务 + 用户描述新项目
    │   └── 路由 → /trellis:feasibility（可行性评估）
    │
    ├── 新项目 / 新客户需求 + 已有任务，但缺少有效 `assessment.md`
    │   └── 路由 → /trellis:feasibility（先补接单/风险评估，不直接进入 brainstorm）
    │
    ├── 新项目 / 新客户需求 + `assessment.md` 存在，但明确 `是否允许进入 brainstorm = 否`
    │   └── 路由 → /trellis:feasibility（补信息 / 谈判 / 重新评估）
    │
    ├── 有任务 + 无 PRD 或 PRD 未冻结
    │   └── 路由 → /trellis:brainstorm（需求发现）
    │
    ├── PRD 已冻结，但缺少 `docs/requirements/customer-facing-prd.md` 或 `docs/requirements/developer-facing-prd.md`
    │   └── 路由 → /trellis:brainstorm（先补项目级双需求文档，再进入下一阶段）
    │
    ├── PRD 已冻结 + 用户输入命中正式变更（新增/修改/删除）
    │   └── 进入 §2.5 需求变更管理（先做影响评估、成本/工期确认与审批；完成后回到受影响的最早阶段）
    │
    ├── PRD 已冻结 + 用户输入命中纯澄清（不改变范围/接口/验收/成本/工期）
    │   └── 保留在当前阶段直接处理
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
    │       - 未完成质量检查/提交前检查 → /trellis:check 或 /trellis:finish-work
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
    ├── 代码实现完成 + 无 check.md
    │   └── 路由 → /trellis:check（质量检查）
    │
    ├── 质量检查完成
    │   └── 路由 → /trellis:review-gate → /trellis:finish-work
    │
    └── 用户要求继续/跳到某阶段
        └── 直接跳转到指定命令
```

### 自然语言触发词

| 用户说 | 触发命令 |
|-------|---------|
| "我有个新项目想法" "帮我评估一下这个需求" "这个项目能做吗" | `/trellis:feasibility` |
| "帮我梳理需求" "我还不太确定要做什么" "需要讨论一下方案" | `/trellis:brainstorm` |
| PRD 已冻结后说 "这个功能再加一个" "这个页面流程改一下" "这个接口字段要调整" "这个验收标准我想改" "这个功能先不做了" | `§2.5 需求变更管理`（全局分支，不在当前阶段直接吸收） |
| PRD 已冻结后说 "这里我确认一下是什么意思" "这个描述对应的是不是原来那个流程" "我不是加功能，只是想确认理解" | 留在当前阶段直接澄清 |
| "开始设计" "画个架构图" "需要做技术选型" "出个设计方案" | `/trellis:design` |
| "拆一下任务" "做个工作计划" "把需求分解成小任务" | `/trellis:plan` |
| "先写测试" "用 TDD 方式" "测试先行" | `/trellis:test-first` |
| "开始写代码" "实现这个功能" "动手做吧" | 实施阶段（本命令 Task Workflow） |
| "检查一下这次改动" "对照 spec 看看" "做一轮质量检查" | `/trellis:check` |
| "补充审查一下" "让其他 CLI 看一下" "多人审查" "进入 review-gate" | `/trellis:review-gate` |
| "准备交付" "跑一下验收" "整理交付物" "项目收尾" | `/trellis:delivery` |
| "这个流程有坑" "这一步老容易漏" "这个命令说明有歧义" "先把这次踩坑记一下" "这个工作流后面得优化" | 优先触发经验反馈机制：开发中先在 `tmp/` 起草反馈草稿，用户确认后移入 `learn/`；若已进入收尾链路则路由到 `/trellis:delivery` 的 Step 9 |
| "收尾" "提交前检查" "准备 commit" | `/trellis:finish-work` |
| "继续上次的工作" "上次做到哪了" | 继续现有任务 |
| "卡住了" "反复出错" "这个 bug 改不好" "死循环" | `/trellis:break-loop` |
| "并行" "同时做两个任务" "worktree" | `/trellis:parallel` |
| "把这次踩坑记到规范" "更新 spec" "规范要改" | `/trellis:update-spec` |
| "跨层检查" "跨模块影响" "检查影响面" | `/trellis:check-cross-layer` |
| "集成这个 skill" "添加 skill" "把 skill 加进来" | `/trellis:integrate-skill` |
| "写代码前先看看规范" "读一下规范" "开发前准备" | `/trellis:before-dev` |
| "帮我了解这个项目" "新人入门" "项目介绍" "怎么用 trellis" | `/trellis:onboard` |
| "创建一个新命令" "加个命令" "新建 slash command" | `/trellis:create-command` |

### 歧义消解规则

当用户输入同时匹配多个命令时，按以下优先级排序：

1. **当前阶段上下文** — 正在 §3 design，用户说"检查" → `/trellis:check-cross-layer`（而非 `/trellis:review-gate`）
2. **精确关键词** — 用户说"TDD" → `/trellis:test-first`（精确匹配优先）
3. **阶段顺序推断** — 刚完成 brainstorm → "下一步" → `/trellis:design`
4. **模糊语义** — 根据上下文推断最合理的命令
5. **兜底** — 无法确定 → `/trellis:start`（Phase Router 自动检测）

当 top-2 候选优先级接近时，向用户确认意图而非自动选择。

### 路由执行

检测到触发词后，先据此收敛候选阶段入口；只有在前置条件满足且无明显歧义时，才进入对应命令流程。

若上下文不足、前置条件缺失，或 top-2 候选接近，则先确认意图，或回退到 `/trellis:start` 做阶段检测。

若命中“首次嵌入后的初始化门禁”，则不得跳过 PRD 规范基线补充动作。

若命中“新项目 feasibility 门禁”：

- 缺少 `assessment.md` 时，不得直接进入 `/trellis:brainstorm`
- `assessment.md` 明确写有 `是否允许进入 brainstorm = 否` 时，不得直接进入 `/trellis:brainstorm`
- 只有存在有效评估记录且允许继续时，才进入需求发现

> 下列 `task_plan.md`、测试文件、任务执行矩阵与状态枚举，属于“目标项目采用 Trellis 任务资产模型时”的推荐判定口径。
> 若目标项目未采用这套文件结构，应保留阶段语义与前后依赖，不应把这些文件名和枚举值误写成所有项目的硬前提。

若命中“经验反馈”类自然触发：

- 不要求等到项目结束再记录
- 按 `§7.3.1` 的 AI 起草规则执行：AI 在当前项目 `tmp/` 下生成草稿，提示用户移动到 `learn/`
- 若当前已经进入收尾链路，优先走 `/trellis:delivery`，在 Step 9 一并完成项目复盘和工作流经验沉淀
- 若用户同时要求“现在就优化工作流”，也先记录问题，再由人工确认是否把它升级成正式流程改动

若 AI 检测到隐式踩坑信号（非用户显式表达）：

- 同一命令连续失败或重试（如 finish-work 前忘 archive 报错后重跑）
- check 中出现“同类错误重复出现”或上下文污染迹象
- 用户表达挫败但未明确指向流程（“算了先这样”“为什么这么麻烦”）

→ AI 应主动问一句：“这次踩坑是否需要记录到 learn/？”
→ 用户确认后再按“经验反馈”类自然触发的路由执行
→ 用户跳过则不强制记录

若 PRD 已冻结且命中需求讨论：

- 只有“纯澄清”才允许留在当前阶段直接处理
- 只要属于新增 / 修改 / 删除，就进入 `§2.5 需求变更管理`
- 这里的 `§2.5` 是**全局流程分支**，不是独立 slash command
- 变更未完成评估、报价/排期确认、审批前，不得把内容直接并入当前阶段继续推进
- 变更获批后，回到受影响的最早阶段；未获批则维持当前冻结基线

若进入实施阶段，且 `task_plan.md` 已包含“任务执行矩阵”：

- 单线程模式下，先读取矩阵，定位一个 `当前状态=可开始` 的任务作为本轮实施对象
- 若采用 Git worktree 或已安装的 `/trellis:parallel` 并行实施，则可从“推荐并行组”中拆分多个 `可开始` 任务分别处理
- 将该任务状态改为 `进行中`
- 同步更新“执行安排”中的当前可开始任务、等待中任务、推荐并行组、串行主链
- 若不存在任何 `可开始` 任务，则不应盲目实现，应先分析阻塞原因

边界：

- 这里只允许更新**当前活动任务**对应的 `task_plan.md` 与执行矩阵，不得借此回填旧任务、已归档任务或其他任务目录的状态
- 若旧任务或已归档记录需要修正，应先走需求变更或人工决策，不把本轮状态推进写回历史文档

### 下一步推荐输出格式

**每个命令执行完毕后，AI 必须在末尾输出「下一步推荐」区块**。

> 这里要求的是“输出推荐区块”，不是要求框架自动跳转到下一阶段；推荐口径仍需服从当前 CLI 的原生入口协议与实际前置条件。

入口表达约束：

- Claude Code：继续使用 `/trellis:xxx`
- OpenCode：TUI 使用 `/trellis:xxx`；CLI 可补 `trellis/xxx`
- Codex：若同一阶段语义被复用到 skills / AGENTS / hooks 侧，必须改写为“自然语言意图 + 对应 skill 名”，不要把 `/trellis:xxx` 当成 Codex 的唯一入口

```markdown
## 下一步推荐

**当前状态**: <一句话描述>

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| <意图> | `/trellis:xxx` | 自然语言继续该阶段，或显式触发 `xxx` skill | **默认推荐**。<说明> |
| <意图> | `/trellis:yyy` | 自然语言转入对应阶段，或显式触发 `yyy` skill | <说明> |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
```

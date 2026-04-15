---
name: design
description: 需求冻结了？开始设计 — 先核对设计输入，再做技术选型研究，用户确认技术架构后分块落盘设计文档、项目文档和工程化联动。触发词：开始设计、画架构图、技术选型、设计方案、架构设计、技术方案、选型、接口设计
---

# /trellis:design — 强门禁设计阶段

> **Workflow Position**: §3 → 前: `/trellis:brainstorm` → 后: `/trellis:plan`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:design`） · ✅ OpenCode（TUI: `/trellis:design`；CLI: `trellis/design`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:design` 命令；见 `codex/README.md`）
>
> **Gate Rule**: 当前阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。设计阶段只能在当前已确认阶段内重入，不能因为“设计文档看起来差不多齐了”就自动进入 `/trellis:plan`。

---

## When to Use (自然触发)

- "开始设计吧"
- "画个架构图"
- "需要做技术选型"
- "出个设计方案"
- "帮我设计一下接口"
- "PRD 已经确认了，下一步怎么做"

> 若 `PRD` 已冻结后命中需求讨论，按 [需求变更管理执行卡](../需求变更管理执行卡.md) 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入变更管理，不直接在本阶段吸收。

---

## 强门禁规则

1. `/trellis:design` 只允许重入当前已确认的 design 阶段，不允许自动切到 `/trellis:plan`
2. 当前阶段判定只看：
   - `.trellis/.current-task`
   - 当前叶子任务
   - `$TASK_DIR/workflow-state.json`
3. 设计阶段完成前，AI 只能给出“下一步推荐”，不能自行推进阶段
4. 技术架构确认前，只有产品信息和功能需求允许同步到目标项目正式文档
5. 技术架构确认后，design 后半段仍需按子块执行；每完成一个子块，都必须停下来给用户确认后才能继续

---

## 前置条件与正式文档边界

进入 `/trellis:design` 前，至少应满足：

- 当前 task 已在 `.trellis/.current-task` 中明确
- 当前 task 为叶子任务
- 当前 task 已初始化 `workflow-state.json`
- 需求已冻结，且已形成目标项目的：
  - `docs/requirements/customer-facing-prd.md`

此时**不要求**已经存在：

- `docs/requirements/developer-facing-prd.md`

### 文档边界

#### 技术架构确认前，可进入目标项目正式文档的内容

- `docs/requirements/customer-facing-prd.md` 中的产品背景、目标、功能需求、范围、验收口径

#### 技术架构确认前，必须留在 task 工作底稿的内容

- 技术选型候选
- 技术架构结论
- 设计决策
- `.trellis/spec` 对齐
- 自动化检查矩阵
- `finish-work` / `record-session` 项目化适配
- README 中的技术架构部分
- `docs/requirements/developer-facing-prd.md`

---

## 流程

### Step 0: 初始化/校验 design 状态

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/workflow-state.py validate <task-dir>
```

若在目标项目内通过安装后的 helper 执行，则改用：

```bash
python3 .trellis/scripts/workflow/workflow-state.py validate <task-dir>
```

设计阶段初始化建议：

- `stage = design`
- `stage_status = in_progress`
- `current_block = input-review`
- `checkpoints.architecture_confirmed = false`

缺少 `workflow-state.json` 时，不允许自动猜当前 design 子阶段，只允许先恢复状态。

### Step 1: 设计输入核对

先做 gap review，只输出：

- 已完成
- 缺失项
- 冲突项
- 待确认项

当前步骤只允许核对：

- `customer-facing-prd.md`
- 任务工作底稿 `prd.md`
- 需求冻结状态
- 现有 UI 目录 / 原型资产位置
- 已存在的设计文档或历史草稿

当前步骤**禁止**：

- 直接生成整套正式设计文档
- 因为发现 UI 目录存在，就默认 design 已接近完成
- 未讨论就覆盖已有设计内容

### Step 2: UI/UX 设计（如有前端）

**调用 Skill**：`ui-ux-pro-max` — 生成页面布局粗稿、组件建议和交互流程。降级：手动从 PRD 提取页面目标后进入外部工具设计。

**强制提醒**：

- 只要当前项目进入了“需要页面视觉设计、页面布局设计、交互原型设计”的阶段，就必须明确提醒用户：这一步需要去外部 UI 设计工具完成，不要只停留在当前 CLI 里讨论。
- 推荐外部操作顺序固定为：
  1. 先去 [UI Prompt Styles](https://www.uiprompt.site/zh/styles) 获取接近目标风格的 UI 提示词
  2. 再在当前 CLI 中按固定骨架整理 `design/STITCH-PROMPT.md`
  3. 最后去 [Stitch](https://stitch.withgoogle.com/) 按页面 / 流程逐个生成 UI 原型
- **执行边界（强制）**：
  - `UI 原型生成` 这一步**禁止**使用 Codex 作为主执行器
  - 允许作为主执行器的 CLI 只有 Claude Code / OpenCode
  - Codex 只能参与文档整理、Prompt 文本润色、原型结果回收，不得继续推荐“用 Codex 直接完成 UI 原型”

**最小执行步骤**：

1. 从 PRD 提取页面目标、用户角色、关键流程、品牌/风格约束
2. 在 `https://www.uiprompt.site/zh/styles` 选择合适风格，整理风格提示词
3. 在当前 CLI 中生成 `design/STITCH-PROMPT.md` 草稿
4. 按页面 / 流程从 `design/STITCH-PROMPT.md` 中提取执行 Prompt，带到 `https://stitch.withgoogle.com/` 逐个生成原型
5. 把确认后的页面结构、组件清单、交互要点记录回 task 工作底稿

### Step 3: 当前步骤允许同步的正式文档

在 `checkpoints.architecture_confirmed = false` 时，design 阶段只允许继续同步：

- `docs/requirements/customer-facing-prd.md`

此时**不允许**正式生成：

- `docs/requirements/developer-facing-prd.md`
- `design/TAD.md`
- `design/DDD.md` / `IDD.md` / `AID.md`
- `.trellis/spec` 对齐结果
- 自动化检查矩阵
- `finish-work` / `record-session` 项目化补丁

### Step 4: 条件文档触发面判断（仅判断，不正式落盘）

在技术架构确认前，只允许先判断当前项目是否会涉及：

1. 数据库 / 持久化 / 缓存数据模型
2. API / 接口契约 / 第三方集成接口
3. AI / LLM 方案
4. 页面视觉原型

这一步只产出“是否需要”的判断，不正式生成完整文档。

### Step 5: 技术选型（研究阶段）

> 这是 design 阶段当前版本的**正式 Step 5**。它不是直接把实现技术写入正式文档，而是 research-first 的技术选型讨论步骤。

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 当需要参考外部开源项目时 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 当需要进行技术方案深度调研时 | 回退：`grok-search`。没有官方文档证据时，不下 API/框架细节结论，只保留待验证设计假设 |
| 复杂架构推理 | `sequential-thinking` | 当涉及 ≥3 个技术方案对比或推理步骤 >3 步时 | 复杂决策场景 |
| 架构图可视化 | `markmap` | 当需要生成架构图或模块依赖图时 | 架构图/模块依赖图 |
| 框架 / SDK API 文档 | `Context7` | 当需要查询第三方库或框架官方文档时 | 技术选型必查 |

**调用 Skill**：按下表选择对应专项 skill 输出设计建议。降级：按 PRD 与既有设计模板手动整理设计决策。

| 领域 | Skill |
|------|-------|
| 架构模式 | `architecture-patterns` |
| 后端架构 | `backend-patterns` |
| API 设计 | `api-design-principles` |
| 数据库 | `postgresql-table-design` |
| 文档撰写 | `doc-coauthoring` |

执行要求：

- 必须基于最新有效信息给出多个可行候选，而不是单一路径拍板
- 需要写清：
  - 候选方案
  - 适用场景
  - 主要优点
  - 主要缺点
  - 不选其他方案的原因
- 在用户确认前，只能写入 task 工作底稿，不能直接落到目标项目正式技术文档

### Step 6: 用户确认技术架构（硬确认点）

只有用户明确确认技术架构后，才允许进入 design 后半段。

确认前：

- `checkpoints.architecture_confirmed = false`
- `stage_status` 不得切到 `completed`
- 不得进入 `/trellis:plan`

确认后：

- `checkpoints.architecture_confirmed = true`
- `current_block` 进入后半段子块

### Step 7: 架构确认后的分块落盘

design 后半段不得一次性跑完，而要按多个子块分段执行。每完成一个子块，都必须停下来给用户确认。

#### 块 A：开发侧正式需求落盘

在当前子块中，正式生成：

- `docs/requirements/developer-facing-prd.md`

要求：

- 只承接已确认架构下的开发实现需求
- 不把尚未确认的后续工程化动作提前写成既定结论

#### 块 B：设计文档落盘

在当前子块中正式生成：

- `design/TAD.md`
- `design/ODD-dev.md`
- `design/ODD-user.md`
- 条件文档：
  - `design/DDD.md`
  - `design/IDD.md`
  - `design/AID.md`
  - `design/STITCH-PROMPT.md`
- 按需：
  - `design/specs/<module>.md`
  - `design/pages/<page>.md`

若项目包含前端视觉落地链路，进入 `/trellis:plan` 时还必须为“`UI -> 首版代码界面`”单独拆出一个前端基线 task，并约束：

- 该 task **禁止**使用 Codex 作为主执行器
- 该 task 只能由 Claude Code / OpenCode 承担主执行入口
- 该 task 完成时，必须沉淀 `design/frontend-ui-spec.md`
- 后续任意 CLI 修改前端时，默认都要以 `design/frontend-ui-spec.md` 为统一约束来源

#### 块 C：项目级文档同步

在当前子块中正式生成或更新：

- 项目根 `README.md`（最低可用版）
- 目标项目 `docs/` 下与已确认技术架构对应的正式说明文档

#### 块 D：工程化联动

在当前子块中完成：

1. 根据技术架构，使用 `trellis-library/cli.py assemble` 选择并导入合适 spec 到当前项目 `.trellis/spec/`
2. 基于当前项目作用/背景/技术架构，对当前项目 `.trellis/spec/` 做分析完善
3. 明确项目自动化检查矩阵
4. 同步适配当前项目的 `/trellis:finish-work`
5. 同步适配当前项目的 `/trellis:record-session`

自动化检查矩阵要求：

- 基于已经确认的语言、框架、包管理器、CI、部署方式、安全要求
- 写清真实会执行的 lint / typecheck / test / build / scan / delivery gate
- 不允许继续保留“默认检查”“按项目自行运行”这类空泛表述
- 必须有明确的质量平台门禁
- 采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因

采用 Sonar 的项目，`sonar-scanner` 至少应以当前项目可执行的真实命令骨架写入检查矩阵，例如：

```bash
sonar-scanner \
  -Dsonar.projectKey=<target-project-key> \
  -Dsonar.token=$SONAR_TOKEN \
  -Dsonar.host.url=https://sonarqube.xzc.com:13785 \
  -Dsonar.sources=.
```

#### 块 C / 块 D 的顺序

- 块 C 与块 D 允许按项目情况调序
- 但两者都必须留在 design 阶段内完成
- 每完成一个子块，都必须停下来给用户确认，不能一次性连续执行到底
- 若块 C 先于块 D 执行，README 或项目 `docs/` 中引用的检查矩阵、spec 结论或收尾门禁应明确标注为“待 design 阶段块 D 最终确认”，避免被误认为已经定稿

### Step 8: design 退出检查

先执行 task-local 设计文档校验：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate <design-dir>
```

再执行状态与正式文档边界校验：

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/workflow-state.py validate <task-dir>
```

退出前必须明确输出：

- 已完成
- 未完成
- 缺失项
- 当前是否仍在等待用户确认

完成退出清单后：

- 先把 `stage_status` 置为 `awaiting_user_confirmation`
- 等用户明确确认 design 阶段完成
- 确认后才允许把下一阶段切到 `/trellis:plan`

---

## 输出

### 架构确认前

- 目标项目正式文档：
  - `docs/requirements/customer-facing-prd.md`
- task 工作底稿：
  - 技术选型候选
  - UI 资产位置与原型分析
  - 条件文档触发判断

### 架构确认后

目标项目或 task 内最终会形成：

```text
docs/requirements/
├── customer-facing-prd.md
└── developer-facing-prd.md

$TASK_DIR/design/
├── index.md
├── TAD.md / ODD-dev.md / ODD-user.md
├── DDD.md / IDD.md / AID.md / STITCH-PROMPT.md
├── frontend-ui-spec.md                               （仅 UI -> 首版代码界面任务完成后必补）
├── specs/<module>.md
└── pages/<page>.md

README.md
.trellis/spec/
```

---

## 下一步推荐

**当前状态**: 仍处于 design 阶段；只有在退出清单完成且用户明确确认后，才允许进入 `/trellis:plan`。

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 继续当前 design 子块 | `/trellis:design` | 继续 design 阶段，或显式触发 `design` skill | **默认推荐**。只重入当前 design 子块，不跨阶段 |
| 在 design 内切到另一个已允许子块 | `/trellis:design` | 继续 design 阶段，或显式触发 `design` skill | 仍留在 design 阶段内 |
| design 已完成，准备进入 plan | `/trellis:plan` | 进入任务拆解，或显式触发 `plan` skill | 仅在 design 退出清单完成且用户明确确认后才允许 |
| 设计不完善，回退补讨论/补文档 | `/trellis:design` | 继续 design 阶段，或显式触发 `design` skill | 先做 gap review，不直接整批重生成内容 |
| 冻结后出现新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 不直接在当前阶段吸收 |
| 检查跨层一致性 | `/trellis:check-cross-layer` | 检查跨层影响，或显式触发 `check-cross-layer` skill | 设计涉及多层时建议执行 |
| 不确定当前任务/状态 | `/trellis:start` | 描述当前状态恢复意图，或显式触发 `start` skill | 回到当前已确认阶段的状态恢复分支 |

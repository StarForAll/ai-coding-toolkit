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

当前阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。

1. 技术架构确认前，只有产品信息和功能需求允许同步到目标项目正式文档
2. 技术架构确认后，design 后半段仍需按子块执行；每完成一个子块，都必须停下来给用户确认后才能继续

---

## 前置条件与正式文档边界

### 门禁校验

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
```

校验通过后继续当前阶段；失败时按输出的错误项逐项修复后重试。

进入 `/trellis:design` 前，需求已冻结，且已形成目标项目的：

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
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
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

**原型资产隔离（强制）**：

- 下列内容**禁止**直接带入正式实现：
  - 照片、截图、录屏、预览图
  - Figma / Stitch / HTML / Storybook 原型文件或分享链接
  - 原型工具导出的组件代码、页面源码、临时演示代码
- 下列结论允许保留，但必须先转写成结构化设计输入：
  - 页面层级、区块划分、组件清单
  - 交互流程、状态集合、反馈方式
  - 视觉方向、布局约束、可访问性 / 动效结论
- 允许保留的结论应优先沉淀到 task 工作底稿、`design/pages/*.md`、`design/specs/*.md`；若后续存在 `UI -> 首版代码界面` task，则再沉淀到 `design/frontend-ui-spec.md`
- 即使原型提供了网页源码或可导出代码，也不能把该代码直接作为正式实现输入
- 以 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 中的 design 参考资产隔离规则为准

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
5. 源码水印与归属证明基线（当 `ownership_proof_required = yes`）

这一步只产出“是否需要”的判断，不正式生成完整文档。

### Step 5: 技术选型（研究阶段）

> 这是 design 阶段当前版本的**正式 Step 5**。它不是直接把实现技术写入正式文档，而是 research-first 的技术选型讨论步骤。

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 项目内现有实现 / 代码上下文定位 | `ace.search_context` | 当需要定位项目内相似实现、受影响文件或既有约束时 | 默认优先；回退：`Read + Glob/Grep` |
| 最新版本 / 发布动态 / 今日事实 | `grok-search` | 当设计判断依赖最新版本、发布日期、官方动态时 | 默认优先；回退：`exa`，仍不足时标记 `[Evidence Gap]` |
| 参考 GitHub 开源架构 | `deepwiki` | 当需要参考外部开源项目时 | 回退：`exa_web_search_exa` |
| 技术选型深度研究 | `exa_web_search_advanced_exa(type=deep-reasoning)` | 当需要进行技术方案深度调研时 | 回退：`grok-search`。没有官方文档证据时，不下 API/框架细节结论，只保留待验证设计假设 |
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
- 若经调研后确认只有一个可信方向，必须显式写明：
  - `当前无可比方案`
  - 形成单一路径的约束条件
  - 当前方向的主要 downside / 风险
  - 为什么此时不再继续伪造多方案比较
- 无论是多候选还是单一路径，研究输出都必须补齐：
  - 系统边界与系统外部的责任边界
  - 外部依赖 / 外部系统清单
  - 主要 boundary crossing（例如 API、消息、存储、第三方服务、人工交接）
  - 在责任切换位置上的 ownership 归属
  - 哪些外部系统不能被默认视为可靠 / 可控，以及失败时的回退或兜底口径
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
- 至少要有可定位的最小章节或等价标题：
  - `依赖与约束`
  - `接口与集成`
  - `错误处理与边界情况`
- 若这些内容影响实现行为，还应明确关联：
  - 数据 / 状态模型
  - 验收标准
  - 测试期望

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
<!-- if:outsourcing -->
  - `design/source-watermark-plan.md`                      （仅当 `ownership_proof_required = yes`）
<!-- endif:outsourcing -->

若项目包含前端视觉落地链路，进入 `/trellis:plan` 时还必须为“`UI -> 首版代码界面`”单独拆出一个前端基线 task，并约束：

- 该 task **禁止**使用 Codex 作为主执行器
- 该 task 只能由 Claude Code / OpenCode 承担主执行入口
- 该 task 完成时，必须沉淀 `design/frontend-ui-spec.md`
- 后续任意 CLI 修改前端时，默认都要以 `design/frontend-ui-spec.md` 为统一约束来源

无论最终采用哪些设计文档承载，块 B 至少必须有一处权威文档明确写出：

- 系统边界与系统外部的责任边界
- 外部依赖 / 第三方系统 / 平台约束
- 主要 boundary crossing
- 在责任变化位置上的 ownership
- 外部系统失败、不可用或不受控时的默认假设与回退口径

其中 `design/TAD.md` 在 design 退出前至少必须补齐以下结构化字段：

- `## 架构冻结清单`
  - `runtime_host`
  - `application_stack`
  - `persistence_strategy`
  - `primary_processing_stack`
  - `distribution_strategy`
  - `remaining_unfrozen_items`
  - `reopen_conditions`
- `## 系统边界与外部依赖`
  - `system_boundary`
  - `external_dependencies`
  - `boundary_crossings`
  - `ownership_boundaries`
  - `fallback_assumptions`
- `## 阶段出口快照`
  - `completed_blocks`
  - `current_status`
  - `open_risks`

约束：

- 这些字段是 design 退出前的**硬冻结快照**，不能只靠口头说明或 `workflow-state.notes`
- 若某项此时仍不能冻结，必须显式写进 `remaining_unfrozen_items`，并在 `reopen_conditions` 里说明何时必须回到 design
- 对不适用的项目，不允许留空；应填写 `not_applicable` 加原因

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
<!-- if:outsourcing -->
6. 若 `ownership_proof_required = yes`，同步建立源码水印与归属证明基线

源码水印与归属证明基线要求：

- 在 `$TASK_DIR/design/source-watermark-plan.md` 冻结：
  - `WMID`
  - `source_watermark_level`
  - `source_watermark_channels`
  - `zero-width` 的允许边界与禁区
  - `subtle-markers` 的嵌入位置与禁区
  - `excluded_paths`
  - `extraction` 与 `verification` 步骤
- 零宽字符水印只能用于：
  - 注释
  - 文档字符串
  - Markdown 说明片段
- 零宽字符水印不得进入：
  - 标识符
  - 变量名
  - 函数名
  - 类名
  - import/export 路径
  - JSON/YAML/TOML key
  - SQL / shell / 正则主体
  - 任何真实执行语义位置
- 不起眼代码标识只能放在稳定、低风险、非业务关键位置；不得污染权限逻辑、接口契约、数据库值或性能热点
- 交付阶段至少需要预留两份产物：
  - `$TASK_DIR/delivery/ownership-proof.md`
  - `$TASK_DIR/delivery/source-watermark-verification.md`
- 设计边界与术语以 [源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md) 为准
<!-- endif:outsourcing -->

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
- `awaiting_user_confirmation` 在 design 阶段内部可能出现多次；只有 `completed_blocks` 已覆盖块 A/B/C/D 时，才表示“准备离开 design 的最终确认点”

### Step 8: design 退出检查

先执行 task-local 设计文档校验：

```bash
python3 <WORKFLOW_DIR>/commands/shell/design-export.py --validate <design-dir>
```

该校验现在不再只检查文件是否存在，还会检查：

- `index.md` / `TAD.md` / `ODD-dev.md` / `ODD-user.md` 是否有可审阅正文
- `TAD.md` 是否补齐架构冻结清单、系统边界、风险与回退、阶段出口快照
- `TAD.md` 是否已写出结构化冻结字段，而不是只有标题

再执行状态与正式文档边界校验：

```bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
```

退出前必须明确输出：

- 已完成
- 未完成
- 缺失项
- 当前是否仍在等待用户确认
- 当前 `TAD.md` 中哪些项已经冻结、哪些项仍待冻结
- 若未来出现哪些变化，必须回到 design

同时满足以下条件后，才允许把 `stage_status` 切到 `awaiting_user_confirmation`：

- `design-export.py --validate` 通过
- `workflow-state.py validate` 通过
- `docs/requirements/developer-facing-prd.md` 已生成
- 项目根 `README.md` 已生成或确认可复用

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
├── source-watermark-plan.md                          （仅当 `ownership_proof_required = yes`）
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

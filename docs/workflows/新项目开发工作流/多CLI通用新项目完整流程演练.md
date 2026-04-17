# 多CLI通用新项目完整流程演练

> 首次接触这套 workflow 时，优先看这份文档。它负责把 Claude Code、OpenCode、Codex 在同一个目标项目里的通用主链讲清楚，并把专项案例分流到对应文档。

想先从大局快速理解整套流程，可先看：[工作流全局流转说明（通俗版）](./工作流全局流转说明（通俗版）.md)

---

## 这份文档的定位

这不是平台安装说明，也不是某个具体业务案例。

它只做三件事：

- 说明新项目主链从 `feasibility` 到 `record-session` 应该怎么走
- 明确 Claude Code、OpenCode、Codex 的入口差异
- 给出每个阶段推荐调用的 MCP / skills、典型降级方式和退出门禁

若你需要平台原生配置细节，请按需再看：

- [工作流总纲](./工作流总纲.md)
- [命令映射](./命令映射.md)
- [双轨交付控制完整流程演练](./完整流程演练.md)
- [Claude Code 适配](./commands/claude/README.md)
- [OpenCode 适配](./commands/opencode/README.md)
- [Codex CLI 适配](./commands/codex/README.md)

---

## 如何阅读这套 Workflow

### 阅读导航表

| 场景 | 先看 | 再看 | 为什么 |
|------|------|------|--------|
| 第一次接触这套 workflow | 本文 | [工作流总纲](./工作流总纲.md) | 先建立主链，再补完整规则 |
| 已经知道阶段名，但不清楚怎么触发 | 本文 | [命令映射](./命令映射.md) | 本文讲阶段目的，映射文档讲入口和路由 |
| 需要某个 CLI 的具体承载方式 | 本文对应阶段 | 平台 README | 主链和平台细节分开，避免默认上下文过重 |
| 你做的是外包 / 定制 / 新客户交付 | 本文 | [双轨交付控制完整流程演练](./完整流程演练.md) | 本文给通用主链，专项文档给外部交付案例 |
| 你只想看某个阶段的命令正文 | 本文对应阶段 | `commands/*.md` | 先知道为什么走这一步，再看命令细则 |

### 文档角色表

| 文档 | 角色 |
|------|------|
| `多CLI通用新项目完整流程演练.md` | 第一入口，讲通用主链 |
| `工作流总纲.md` | 权威规则层，讲原则、门禁、边界 |
| `命令映射.md` | 路由层，讲阶段到命令 / skills / CLI 的映射 |
| `完整流程演练.md` | 专项案例层，讲外部项目双轨交付控制 |
| `commands/*/README.md` | 平台展开层，讲各 CLI 的原生承载方式 |

---

## 使用前提

### 这是嵌入在 Trellis 上的 workflow，不是替换 Trellis 基线

这套 workflow 的默认使用前提是：**目标项目本身已经是 Git 项目，`origin` 已至少配置两个 push URL，且已经先执行过 `trellis init`**。

也就是说，至少要同时满足：

- 项目根存在 Git 仓库标记
- `origin` 已至少配置两个 push URL
- 项目根已经有 Trellis 基线目录和对应 CLI 基线资产
- 能检测到 `trellis init` 初始化产物，例如 `.trellis/.version`

参考配置命令：

```bash
git remote set-url --add --push origin git@github.com:xxx/yyy.git
git remote set-url --add --push origin git@gitee.com:xxx/yyy.git
```

如果少了其中任意一个前提，就不应把当前 workflow 视为“已经可以直接嵌入使用”。

因此这里说的“进入某个阶段”，不等于当前 workflow 会从零分发整套阶段命令，而是分成三类：

- **Trellis 原生基线**：目标项目初始化后本来就存在的命令/技能
- **workflow 新增分发**：当前 workflow 自己额外嵌入到目标项目的阶段命令或技能
- **workflow 补丁增强**：保留 Trellis 原生命令/技能，再额外注入当前 workflow 的规则或收尾门禁

在当前这套新项目 workflow 里，至少要记住：

- `start` 是 **Trellis 原生命令 + workflow Phase Router 增强**
- `finish-work` 是 **Trellis 原生命令/技能基线 + workflow 项目化补丁**，不是当前 workflow 新增分发的独立源文件
- `record-session` 是 **Trellis 原生命令/技能基线 + workflow 元数据闭环补丁**
- `archive` 仍直接复用目标项目 Trellis 基线里的 `python3 ./.trellis/scripts/task.py archive`，不是当前 workflow 额外分发的一份 helper
- 若项目启用作者归属保护，源码水印与归属证明也应视为 workflow 的正式产物层，而不是交付前临时想起的补丁动作

如果忽略这层嵌入关系，就容易把“继承基线”误判成“workflow 漏了命令”。

对应到本次 close-out 行为，还要再加一条：若目标项目不是通过当前最新 Trellis 初始化/升级得到的，那么即使 workflow 本身已经安装成功，`record-session -> archive` 这条链路也可能仍然继承旧基线中的 archive bug。

还要额外记住一条：`finish-work` 的项目化补丁虽然会按 Claude Code / OpenCode / Codex 各自原生格式落地，但它承载的**项目检查矩阵含义必须一致**，因为这部分由项目技术架构决定，不由 CLI 类型决定。

### 安装时序

这套 workflow 的嵌入方式不是“给 AI CLI 一份目录就算装好了”，而是严格按下面时序执行：

1. 先在目标项目执行 `trellis init`
2. 再运行当前 workflow 目录里的 `commands/install-workflow.py`
3. 安装脚本把这套 workflow 嵌入到目标项目，并按各 CLI 官方原生格式完成内容适配
4. 安装脚本自动导入 `pack.requirements-discovery-foundation`，并删除 `00-bootstrap-guidelines`
5. 最后在目标项目里按原生入口直接使用

标准安装命令：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/install-workflow.py \
--project-root <target-project>
```

如果只想装部分 CLI，再加 `--cli` 过滤。

所以这里说的“嵌入”，默认指的是**`trellis init` 之后再执行安装脚本，把 workflow 直接装进目标项目**。
安装后的初始需求发现基础资产由脚本导入，不再通过手工复制或自然语言提示“补装”。

安装完成后，这套 workflow 的实际使用仍然可以是**渐进性披露**的：

- 先进入当前阶段
- 再按当前阶段按需展开命令、文档、MCP、skills

这里的渐进性披露描述的是“安装后的使用方式”，不是“是否已经安装成功”。

### 多 CLI 同装，但入口协议不同

同一个目标项目里，可以同时存在 Claude Code、OpenCode、Codex 的适配层，但三者入口协议不同：

| CLI | 阶段入口 |
|-----|---------|
| Claude Code | 项目命令：`/trellis:<phase>` |
| OpenCode | TUI: `/trellis:<phase>`；CLI: `trellis/<phase>` |
| Codex | 自然语言 + 对应 skill；不提供项目级 `/trellis:<phase>` 命令目录 |

### 能力路由基线

默认遵循以下共用规则：

- 本地代码定位：优先 `ace.search_context`
- 第三方库/框架官方文档：优先 `Context7`
- 最新事实/版本/新闻：优先 live 检索
- 需求模糊：优先 `ace.enhance_prompt`
- 复杂分支推理：优先 `sequential-thinking`
- 阶段文档列出的 MCP / skills 默认视为**先调用的主能力**，不是可有可无的装饰项；只有能力不可用时才降级
- 关键能力不可用：必须显式写 `[Evidence Gap]`

### 统一对话收尾约定

每个阶段执行完后，都应在本轮回复末尾输出「下一步推荐」。

这里的「下一步推荐」是当前 CLI 的沟通与协作输出口径，不等于框架已经自动跳转到下一阶段；若前置条件不足、候选阶段接近或上下文不清，仍应先确认。

- Claude Code：优先推荐项目命令，如 `/trellis:brainstorm`
- OpenCode：优先推荐项目命令；若是在 CLI 语境，可补充 `trellis/brainstorm`
- Codex：优先推荐“自然语言意图 + 对应 skill 名”，如“继续需求澄清，或显式触发 `brainstorm` skill”
- 不要把 `/trellis:xxx` 当作 Codex 的唯一入口协议
- 用户不确定下一步时：
  - Claude / OpenCode：推荐 `/trellis:start`
  - Codex：推荐描述当前意图，或显式触发 `start` skill

### 统一阶段模板

阅读下方每个阶段时，都只抓 6 件事：

1. 这个阶段要解决什么问题
2. 三个 CLI 分别怎么进入
3. 推荐调用什么 MCP / skills
4. 没有这些能力时怎么降级
5. 满足什么门禁后才能进入下一步
6. 本轮结束时应该如何用当前 CLI 的原生入口表达“下一步推荐”

补充总规则：

- 当前 workflow 采用 [阶段状态机与强门禁协议](./阶段状态机与强门禁协议.md)
- 当前阶段只允许按 `.current-task -> 当前叶子任务 -> workflow-state.json` 判定
- 每个阶段完成后都必须停在 `awaiting_user_confirmation`，用户确认后才允许切到下一阶段
- `/trellis:start` 只重入当前已确认阶段，不自动跨阶段推进

---

## 阶段 1：Feasibility

### 目标

确认项目是否合法、能不能做、值不值得做，以及是否允许进入需求发现。

### CLI 入口差异

- Claude Code：`/trellis:feasibility`
- OpenCode：TUI 用 `/trellis:feasibility`，CLI 用 `trellis/feasibility`
- Codex：自然语言描述或显式触发 `feasibility` skill

### 推荐 MCP / Skills

- `demand-risk-assessment`
- `exa_create_research`
- `deepwiki`
- `sequential-thinking`

### 典型降级方式

- 无法联网时，不输出“行业最新情况”或“最新政策”结论，改为本地已知风险清单，并标记 `[Evidence Gap]`
- 无法完成结构化风险评估时，至少保留“接 / 谈判后接 / 暂停 / 拒绝”的结论和原因

### 外部交付项目分支

外包、定制开发、新客户项目必须在这里明确：

- `delivery_control_track`
- `delivery_control_handover_trigger`
- `delivery_control_retained_scope`

内部项目通常不需要双轨交付字段，但仍必须写明法律/合规风险结论、红线检查结论，以及是否允许进入 `brainstorm`。

### 退出门禁

- 若是新建目标项目，则在**第一次进入 workflow** 前，本地主分支和初始分支已统一为 `main`；若此时还没有有效 `assessment.md`，就必须先进入 `feasibility`；若目标项目已存在本地提交历史，则只记录现状，不强制改分支
- 形成 `assessment.md`
- 明确是否允许进入 `brainstorm`
- 若为外部项目，交付控制轨道已定

---

## 阶段 2：Brainstorm

### 目标

先按 task-first 建立或更新 `prd.md` 工作底稿，自动读取上下文并在必要时 research-first；然后确认需求描述是否准确，统一做 `L0/L1/L2` 分类；离开 brainstorm 前必须先补齐不可跳过的项目级粗估：`task_dir/prd.md` 中的 `## 项目级粗估` 与 `customer-facing-prd.md` 中的 `## 项目级粗估摘要`；进入 design 前至少需补齐 `customer-facing-prd.md`，`developer-facing-prd.md` 等到 design 阶段技术架构确认后再正式生成；`L0` 单任务闭环可只保留 `prd.md` 轻量基线，但仍不能跳过粗估。

### CLI 入口差异

- Claude Code：`/trellis:brainstorm`
- OpenCode：TUI 用 `/trellis:brainstorm`，CLI 用 `trellis/brainstorm`
- Codex：自然语言描述或显式触发 `brainstorm` skill

### 推荐 MCP / Skills

- `brainstorm`
- `prd`
- `ace.enhance_prompt`
- `sequential-thinking`
- `markmap`

### 典型降级方式

- 无完整研究条件时，先把 repo 中已知约束、现有模式和边界写入 `prd.md`
- 无 `ace.enhance_prompt` 时，人工补齐“目标 / 范围 / 验收 / 边界”四项后再分类
- 无可视化工具时，用纯 markdown 列表表达“需求 → 功能 → 验收”

### 外部交付项目分支

若是外部项目，这一步要把对客户的交付边界说人话，而不只是写机器字段：

- 尾款前给什么
- 尾款前不交什么
- 变更如何计入下一轮

若项目启用了作者归属保护，还要在 feasibility 一并定准：

| 档位 | 含义 | 最低要求 |
|---|---|---|
| `none` | 不启用源码水印与归属证明门禁 | 不要求 |
| `basic` | 最低档：至少要求可见源码水印 | `source_watermark_channels` 至少包含 `visible` |
| `hybrid` | 默认推荐档：可见水印 + 若干隐蔽辅助层 | `source_watermark_channels` 至少包含 `visible` |
| `forensic` | 取证强化档：尽量保留多层水印与证明 | `source_watermark_channels` 至少包含 `visible`，建议启用全部已确认通道 |

这里的 level 主要表达策略强度；真正决定后续 design / plan / delivery 实际检查范围的，仍是 `source_watermark_channels`。

### 退出门禁

- 需求描述达到“已准确”
- 已完成 `L0/L1/L2` 分类
- 已在 `task_dir/prd.md` 中补齐 `## 项目级粗估`
- 若走 `L1/L2 -> design` 路径，已在目标项目 `docs/requirements/` 下生成：
  - `customer-facing-prd.md`
- 若走 `L1/L2 -> design` 路径，`customer-facing-prd.md` 已补齐 `## 项目级粗估摘要`
- 若走 `L0 -> start` / `test-first` 路径，则 `customer-facing-prd.md` 不强制，但 `task_dir/prd.md` 中的项目级粗估仍不可跳过
- `developer-facing-prd.md` 不在此时强制生成；它等到 design 阶段技术架构确认后再正式落盘
- 已决定走 `design`、`plan` 还是极小任务直进 `start`
- 若下一步进入 `design`，已明确会在 `design -> 3.7` 把 `sonar-scanner` 纳入项目自动化检查矩阵
- 已进入“等待用户确认是否切换阶段”的状态，而不是自动跳转

> 这条门禁约束的是**使用该 workflow 的目标项目**，不是当前 workflow 仓库本身必须先有这两份文档。
>
> `task_dir/prd.md` 仍然可以作为阶段内工作底稿，但它不是项目级正式需求文档的替代品。
>
> 通用新项目默认继续走 `design`。只有边界极小、单上下文可闭环的 `L0` 事项，才建议直接进 `start`。

---

## 阶段 3：Design

### 目标

冻结关键设计决策，补齐项目 spec 基线，并同步适配后续 `finish-work` / `record-session` 的项目化门禁。

当前阶段拆成两段：

- 前半段：输入核对、UI 资产核对、技术选型研究
- 后半段：技术架构确认后的正式落盘与工程化联动

后半段固定按子块理解：

- 块 A：`developer-facing-prd.md`
- 块 B：设计文档落盘
- 块 C：项目级文档同步
- 块 D：工程化联动

其中块 C 与块 D 可按项目情况调序，但每完成一个子块都必须停下来等用户确认。

### CLI 入口差异

- Claude Code：`/trellis:design`
- OpenCode：TUI 用 `/trellis:design`，CLI 用 `trellis/design`
- Codex：自然语言描述或显式触发 `design` skill

### 推荐 MCP / Skills

- `ace.search_context`
- `Context7`
- `doc-coauthoring`
- `architecture-patterns`
- `backend-patterns`
- `api-design-principles`

### 典型降级方式

- 没有官方文档证据时，不下 API / 框架细节结论，只保留待验证设计假设
- 没有完整架构样板时，先冻结接口/数据/错误矩阵，再补实现细节

### 关键设计文档矩阵

- 进入 design 前必须已存在的前置正式需求文档：
  - `docs/requirements/customer-facing-prd.md`（承担 BRD 主文档职责）
- 技术架构确认后才正式生成：
  - `docs/requirements/developer-facing-prd.md`（需求实现说明、模块拆解与任务边界、场景/规则/验收映射；接口/数据库正文以跳转链接承接）
- 设计阶段硬必选：
  - `design/TAD.md`
  - `design/ODD-dev.md`
  - `design/ODD-user.md`
  - 项目根 `README.md`（最低可用版）
- 设计阶段条件必选：
  - `design/DDD.md`
  - `design/IDD.md`
  - `design/AID.md`
  - `design/STITCH-PROMPT.md`
  - `design/specs/*.md`
- `design/pages/*.md`
- `design/source-watermark-plan.md`（若 `ownership_proof_required = yes`）

### 前端视觉落地边界

- `UI 原型生成`：Codex 不能作为主执行器，必须改用 Claude Code / OpenCode
- `UI -> 首版代码界面`：Codex 也不能作为主执行器，必须改用 Claude Code / OpenCode
- 该首版前端落地 task 完成时，必须产出 `design/frontend-ui-spec.md`
- 后续任意 CLI 再改前端时，都默认以 `design/frontend-ui-spec.md` 为统一约束来源
- UI 原型文件、原型导出代码、临时网页源码都只算参考资产，不能直接作为正式实现输入
- 真正允许带入实现的，只能是已经回收并转写好的交互 / 视觉结论

### Stitch Prompt 口径

- 先去 `uiprompt.site` 选择风格词
- 再由当前 CLI 生成固定骨架的 `design/STITCH-PROMPT.md`
- 最后按**单页面 / 单流程**给 Stitch 执行，不采用整站一次性大 Prompt
- 默认一个 `STITCH-PROMPT.md` 即可；页面复杂时再补页面级 Prompt 文件
- 必须包含“去 AI 味”全局禁止项；项目只能增补，不能删减基线项。默认基线以 [工作流总纲 §3.1.2](./工作流总纲.md) 为准

### 外部交付项目分支

这里要显式导入和对齐外部交付基线：

- 基础必选：`delivery-control` + `transfer-checklist`
- `trial_authorization`：额外补 `authorization-management`
- 涉及正式移交密钥/配置：额外补 `secrets-and-config`

同时在这里完成：

- `/trellis:finish-work` 的首次项目化适配
- `/trellis:record-session` 的基线适配
- 若 `ownership_proof_required = yes`，同步冻结：
  - `WMID`
  - 零宽字符水印边界（只允许注释 / 文档字符串 / Markdown）
  - 不起眼代码标识的允许位置与禁区
  - 后续 `ownership-proof.md` / `source-watermark-verification.md` 的最低契约

边界：

- 这里定义的是当前项目后续收尾门禁的基线，不要求回填旧任务、旧 session 或已归档记录
- 若历史任务或历史记录需要修正，应通过变更管理或人工决策处理，不在本轮 walkthrough 中顺手改历史台账

### 退出门禁

- 关键设计文档与项目 spec 已对齐
- 已完成 `DDD.md` / `IDD.md` / `AID.md` / `STITCH-PROMPT.md` 的条件判定；凡判定涉及者，已在当前阶段直接细化
- 自动化检查矩阵已明确，且已包含明确质量平台门禁（采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因）
- `finish-work` / `record-session` 的项目化基线已定
- 已完成 design 退出检查，且用户已明确确认允许进入 plan

---

## 阶段 4：Plan

### 目标

把冻结后的需求与设计拆成真实 Trellis task，并生成只保留摘要的 `task_plan.md`。

### CLI 入口差异

- Claude Code：`/trellis:plan`
- OpenCode：TUI 用 `/trellis:plan`，CLI 用 `trellis/plan`
- Codex：自然语言描述或显式触发 `plan` skill

### 推荐 MCP / Skills

- `project-planner`
- `writing-plans`
- `sequential-thinking`
- `ace.search_context`

### 典型降级方式

- 没有结构化拆解能力时，至少按“范围 / 风险 / 验收 / 依赖 / 回归”五列拆任务
- 对不确定项单独列成待补信息，不要混入已承诺任务

### 外部交付项目分支

这里必须把以下内容拆成独立任务，而不是放进一个笼统“交付”：

- 试运行版交付
- 永久授权切换
- 可见源码水印
- 零宽字符水印（若启用）
- 隐蔽代码标识（若启用）
- 水印验证
- 归属证明包
- 源码移交
- 生产权限移交
- 最终控制权移交

### 退出门禁

- `task_plan.md` 摘要已形成
- 真实 Trellis task / child task 已拆出
- 每个 task 的全局门禁来源已明确
- 已生成当前推荐执行任务说明卡，先向用户说明该 task 的目标、边界、依赖、验收与风险
- 已决定进入 `start` 主链（需要显式先测时才额外进入 `test-first`），但尚未开工
- 已明确当前要执行的叶子 task，并把状态停在“等待用户确认是否进入 implementation/test-first”
- 进入 `implementation` / `test-first` 前，必须通过 `workflow-state` 显式设置 `checkpoints.execution_authorized = true`，并记录 `last_confirmed_transition`
- `plan` 阶段未生成基础代码、未编写实现代码、未直接执行任何具体 task

---

## 阶段 5：Start 主链（可选手动 Test-First）

### 目标

先选定当前 task，先向用户说明这次要开的 task 信息，再由 `start` 自动执行 `before-dev`、补当前 task 的门禁，之后进入实现闭环。

### CLI 入口差异

- Claude Code：默认 `/trellis:start`；只有显式先测时才 `/trellis:test-first`
- OpenCode：默认 TUI 用 `/trellis:start`、CLI 用 `trellis/start`；只有显式先测时才进入 `test-first`
- Codex：默认描述当前实现意图或显式触发 `start` skill；只有显式先测时才进入 `test-first`

### 推荐 MCP / Skills

- `test-driven-development`
- `ace.search_context`
- `Context7`
- `coding-standards`
- `simplify`
- `karpathy-guidelines`

### 典型降级方式

- 无法先写自动化测试时，至少在 `before-dev.md` 中写清手工验证步骤与证据口径
- 无 `Context7` 时，只引用项目内既有模式或已确认官方文档
- 若不确定当前该进哪个阶段，用 `start` 作为 Phase Router 兜底

### 外部交付项目分支

通常不单独分支。除非实现内容直接触及试运行限制、授权切换、交付控制逻辑，此时应回看 `design` / `plan` 基线而不是临时拍脑袋修改。

### 退出门禁

- 已有测试门禁或等价验证计划
- 当前任务在单上下文内可闭环
- 实现完成并保留了可审查证据

---

## 阶段 6：Project-Audit

### 目标

当全部代码相关任务完成后，从项目全局角度统一做一次代码审查与查缺补漏。

这一步不是单任务 `check` 的重复，而是项目级总复核，固定分三步：

- 先分析项目整体代码并与用户讨论
- 再确认修正方案
- 最后统一修改

补充规则：

- `project-audit` 新发现的高风险问题留在当前阶段内处理，不回挂具体任务
- 默认先由当前 CLI 完成发现与方案讨论
- 只有当问题本身高不确定、强争议、跨模块因果难判断，或用户显式要求时，才在分析/方案阶段提前引入 `multi-cli-review`
- 若在 `project-audit` 内部使用多 CLI 审查，默认 2 个 reviewer，最多 4 个；建议优先在 3 轮内收敛，超过建议轮次需用户明确要求继续
- 修复执行阶段可继续使用 `multi-cli-review` / `multi-cli-review-action`
- 这些多 CLI 能力属于 `project-audit` 内部手段，不等于进入任务级 `review-gate`

### CLI 入口差异

- Claude Code：`/trellis:project-audit`
- OpenCode：TUI 用 `/trellis:project-audit`，CLI 用 `trellis/project-audit`
- Codex：自然语言描述或显式触发 `project-audit` skill

### 退出门禁

- 若是正式模式：全部 `代码相关` 任务已完成，且 `PROJECT-AUDIT` 任务已完成
- 若是手动预审模式：已记录本轮发现与修改，但不替代最终正式 `project-audit`

---

## 阶段 7：Check（+ 条件触发 Review-Gate）

### 目标

先做本 CLI 的质量检查，再判断是否需要进入多 CLI 补充审查门禁。

这里的 `review-gate` 仅适用于任务闭环，不属于 `project-audit` 之后的默认项目级收尾阶段。
这里展示的是项目收尾链路中的 `check`；在单任务开发循环内，每次 `start` 完成后也会执行对应任务级 `check`。

### CLI 入口差异

- Claude Code：`/trellis:check` → （默认）`/trellis:finish-work`；高风险条件触发时 → `/trellis:review-gate`
- OpenCode：TUI 用 `/trellis:check`、`/trellis:finish-work`（或条件触发 `/trellis:review-gate`）；CLI 用 `trellis/check`、`trellis/finish-work`
- Codex：自然语言描述或显式触发 `check`、`finish-work` skill；条件触发时再用 `review-gate` skill

### 推荐 MCP / Skills

- `verification-before-completion`（默认）
- `sharp-edges`（默认）
- `multi-cli-review`（条件触发，经 `review-gate` 判定后使用）
- `multi-cli-review-action`（补充审查执行阶段使用）

### 典型降级方式

- 没有 reviewer skill 时，不伪造多 CLI 审查，直接记录“未执行原因 + 当前残余风险”
- 只要出现安全、跨层 contract、数据迁移、高 blast radius，就不要把 `review-gate` 当成可有可无

### 外部交付项目分支

通常只做轻量提醒：若改动触及交付控制、授权、密钥、最终移交，审查时必须把这些边界视为高风险面。

### 退出门禁

- `check` 结果已写清
- 若触发了 `review-gate`，结果已明确为 `required` / `recommended` / `skip`
- 所有审查发现已修复或已留风险说明

---

## 阶段 8：Finish-Work

### 目标

在提交前用项目真实检查矩阵证明“这轮工作可以交给人测试或提交”。

### CLI 入口差异

- Claude Code：`/trellis:finish-work`
- OpenCode：TUI 用 `/trellis:finish-work`，CLI 用 `trellis/finish-work`
- Codex：自然语言描述或显式触发 `finish-work` skill

### 推荐 MCP / Skills

- `verification-before-completion`

### 典型降级方式

- 没法运行某项检查时，明确写 `not run` 和原因，不要说“应该没问题”
- 不用默认 `lint/test/build` 占位词替代真实项目检查矩阵

### 外部交付项目分支

这里只做轻量提醒：若本轮涉及交付控制文档、授权条款或移交 checklist，也应纳入提交前检查证据。

### 退出门禁

- 真实执行了本项目要求的检查
- 结果按 `pass / fail / not run` 记录
- 可以进入 `delivery`

---

## 阶段 9：Delivery

### 目标

做验收测试、交付物整理、变更日志与交付控制门禁检查。

### CLI 入口差异

- Claude Code：`/trellis:delivery`
- OpenCode：TUI 用 `/trellis:delivery`，CLI 用 `trellis/delivery`
- Codex：自然语言描述或显式触发 `delivery` skill

### 推荐 MCP / Skills

- `doc-coauthoring`
- `changelog-generator`
- `verification-before-completion`
- `requesting-code-review`

### 典型降级方式

- 没有自动 changelog 时，手工按“用户可感知变化 / 风险 / 验证结果”整理
- 没有专项交付脚本时，至少执行 checklist，而不是跳过交付门禁

### 外部交付项目分支

这是必须显式分支的阶段：

- `retained-control delivery`：交付材料，但不移交最终控制权
- `final control transfer`：只有触发条件满足后，才移交源码、永久授权、密钥、管理员权限

### 退出门禁

- 验收结果清晰
- 交付物已整理
- 若为外部项目，当前交付事件类型与允许移交范围已写清
- 若 `ownership_proof_required = yes`，已通过：

```bash
python3 <WORKFLOW_DIR>/commands/shell/ownership-proof-validate.py --phase delivery --task-dir <task-dir>
```

---

## 阶段 10：Record-Session

### 目标

完成当前任务的最终收尾记录，关闭元数据闭环。

边界：这里只围绕**当前活动任务**的最终收尾，不借 `archive` 或 `record-session` 顺手回填旧任务、旧会话记录或已归档目录。

### CLI 入口差异

- Claude Code：`/trellis:record-session`
- OpenCode：TUI 用 `/trellis:record-session`，CLI 用 `trellis/record-session`
- Codex：自然语言描述或显式触发 `record-session` skill

### 推荐 MCP / Skills

- `record-session`

### 典型降级方式

- helper 或自动提交失败时，不把 session 记为完成
- 若 `.trellis/tasks`、`.trellis/.current-task`、staged 区仍脏，先处理元数据问题，不直接记录

### 外部交付项目分支

通常只做轻量提醒：若本轮完成的是交付事件任务，session 应明确记下“当前交付事件类型”和“是否已触发最终移交”。

### 退出门禁

- 通过 `record-session-helper.py` 完成收尾记录（最终收尾入口，不要直接调用 `add_session.py`）
- session 已记录成功
- 元数据闭环完成
- 然后再执行 archive（顺序永远是 record-session → archive）

---

## 从这份文档再往下怎么走

- 要看权威规则与门禁：去 [工作流总纲](./工作流总纲.md)
- 要看阶段到命令 / skills 的映射：去 [命令映射](./命令映射.md)
- 要看外部项目双轨交付案例：去 [双轨交付控制完整流程演练](./完整流程演练.md)
- 要看具体 CLI 的原生承载方式：去 `commands/*/README.md`

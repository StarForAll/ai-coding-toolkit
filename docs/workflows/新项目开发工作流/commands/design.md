---
name: design
description: 需求冻结了？开始设计 — UI/UX、架构选型、接口设计、文档输出。触发词：开始设计、画架构图、技术选型、设计方案、架构设计、技术方案、选型、接口设计
---

# /trellis:design — 设计阶段引导

> **Workflow Position**: §3 → 前: `/trellis:brainstorm` → 后: `/trellis:plan`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:design`） · ✅ OpenCode（TUI: `/trellis:design`；CLI: `trellis/design`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:design` 命令；见 `codex/README.md`）

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

## 流程

### Step 1: UI/UX 设计（如有前端）

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

**建议引导话术**：

> 现在已经进入需要外部 UI 设计的阶段。请先去 `https://www.uiprompt.site/zh/styles` 选择合适的 UI 风格提示词，再在当前 CLI 中按固定模板整理 `design/STITCH-PROMPT.md`，然后把其中对应页面/流程的 Prompt 带到 `https://stitch.withgoogle.com/` 逐个生成 UI 原型。注意：`UI 原型生成` 这一步不能使用 Codex 作为主执行 CLI，必须改用 Claude Code 或 OpenCode。完成后，再回到当前工作流继续补齐设计说明和技术方案。

**最小执行步骤**：

1. 从 PRD 提取页面目标、用户角色、关键流程、品牌/风格约束
2. 在 `https://www.uiprompt.site/zh/styles` 选择合适风格，整理风格提示词
3. 在当前 CLI 中生成 `design/STITCH-PROMPT.md`
4. 按页面 / 流程从 `design/STITCH-PROMPT.md` 中提取执行 Prompt，带到 `https://stitch.withgoogle.com/` 逐个生成原型
5. 回到当前任务，把确认后的页面结构、组件清单、交互要点沉淀到 `design/specs/` 与 `design/pages/`

### Step 1.5: Stitch Prompt 固定模板（如有前端）

`design/STITCH-PROMPT.md` 必须采用固定骨架，而不是每次临时拼 Prompt。

固定要求：

- 一个文件同时包含：
  - 项目级总上下文 Prompt
  - 各页面 / 各流程的执行 Prompt 小节
- 默认以**单页面 / 单流程**方式给 Stitch 执行，不使用“整站一次性大 Prompt”
- 仅当页面明显复杂时，才允许拆出额外页面级 Prompt 文件
- 必须包含全局“去 AI 味”反例约束，且项目级只允许增补，不允许删除全局基线项

模板至少要覆盖：

1. 产品 / 页面目标
2. 目标用户与使用场景
3. 页面 / 模块清单
4. 核心流程
5. 必要功能与组件要求
6. 来自 `uiprompt.site` 的风格提示词
7. 贴近主题、避免 AI 味的反例禁止项
8. Stitch 执行范围（当前页面 / 当前流程）

建议默认的全局禁止项至少包括：

- 不要通用 SaaS 模板感
- 不要廉价渐变和无意义炫光装饰
- 不要过度圆角、过度玻璃拟态、过度悬浮阴影
- 不要无信息密度的卡片堆砌
- 不要与业务无关的装饰性图形或占位文案
- 不要“英雄区 + 三栏卖点 + 泛化插画”的通用 AI 生成组合

### Step 2: 设计文档矩阵

设计阶段不再把 `BRD.md` 放在 `design/` 目录中。业务需求主文档由目标项目的 `docs/requirements/customer-facing-prd.md` 承担；开发实现需求主文档由 `docs/requirements/developer-facing-prd.md` 承担。

在技术架构确认后，设计文档应按三层来组织：

| 类型 | 文档 | 规则 |
|------|------|------|
| 前置正式需求文档 | `docs/requirements/customer-facing-prd.md` | **必需**；承担 BRD 主文档职责 |
| 前置正式需求文档 | `docs/requirements/developer-facing-prd.md` | **必需**；需求实现说明、模块拆解与任务边界、场景/规则/验收映射；接口/数据库正文改为跳转链接 |
| 设计阶段硬必选 | `design/TAD.md` | **必需** |
| 设计阶段硬必选 | `design/ODD-dev.md` | **必需** |
| 设计阶段硬必选 | `design/ODD-user.md` | **必需** |
| 设计阶段硬必选 | 项目根 `README.md` | **必需**；此阶段只要求最低可用版 |
| 设计阶段条件必选 | `design/DDD.md` | 涉及数据库 / 持久化 / 缓存数据模型 / 迁移时创建 |
| 设计阶段条件必选 | `design/IDD.md` | 涉及 API / 接口契约 / 第三方集成接口时创建 |
| 设计阶段条件必选 | `design/AID.md` | 涉及 AI / LLM 方案时创建 |
| 设计阶段条件必选 | `design/STITCH-PROMPT.md` | 涉及页面视觉原型时创建 |
| 设计阶段条件必选 | `design/specs/<module>.md` | 复杂模块时创建 |
| 设计阶段条件必选 | `design/pages/<page>.md` | 页面复杂时创建 |

### Step 3: 条件文档判定（技术架构确认后立即执行）

在输出 `TAD.md` 时，必须同步完成以下判断，不能拖到实现阶段再补：

1. 是否涉及数据库 / 持久化 / 缓存数据模型
2. 是否涉及 API / 接口契约 / 第三方集成接口
3. 是否涉及 AI / LLM 方案
4. 是否涉及页面视觉原型

若判断“涉及”，则在当前 design 阶段直接创建并细化对应文档：

- `design/DDD.md`
- `design/IDD.md`
- `design/AID.md`
- `design/STITCH-PROMPT.md`

### Step 4: 功能规格说明

为每个模块生成 `design/specs/<module>.md`

### Step 5: 可执行原型验证

覆盖 1 主流程 + 1 异常 + 1 空数据

### Step 6: 页面与交互说明

为每个页面生成 `design/pages/<page>.md`

### Step 6.5: MCP 能力路由

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 当需要参考外部开源项目时 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 当需要进行技术方案深度调研时 | 回退：`grok-search` |
| 复杂架构推理 | `sequential-thinking` | 当涉及 ≥3 个技术方案对比或推理步骤 >3 步时 | 复杂决策场景 |
| 架构图可视化 | `markmap` | 当需要生成架构图或模块依赖图时 | 模块依赖图、技术栈确认 |
| 框架 / SDK API 文档 | `Context7` | 当需要查询第三方库或框架官方文档时 | 技术选型必查；无法获取时标记 `[Evidence Gap]` |

### Step 7: 技术方案设计

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

### Step 8: 文档输出与后续前端基线任务

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate <design-dir>
```

若在目标项目内通过安装后的 helper 执行，则改用目标项目对应的 helper 路径；当前源仓库内维护 workflow 内容时，以上命令可直接使用。

输出文档体系：

- `design/index.md` `TAD.md` `ODD-dev.md` `ODD-user.md`（必需）
- `DDD.md` `IDD.md` `AID.md` `STITCH-PROMPT.md`（条件文档）
- `specs/<module>.md` `pages/<page>.md`（按需）
- 项目根 `README.md`（最低可用版，单独维护）

若项目包含前端视觉落地链路，进入 `/trellis:plan` 时还必须为“`UI -> 首版代码界面`”单独拆出一个前端基线 task，并约束：

- 该 task **禁止**使用 Codex 作为主执行器
- 该 task 只能由 Claude Code / OpenCode 承担主执行入口
- 该 task 完成时，必须沉淀 `design/frontend-ui-spec.md`
- 后续任意 CLI 修改前端时，默认都要以 `design/frontend-ui-spec.md` 为统一约束来源

---

## 输出

```
$TASK_DIR/design/
├── index.md
├── TAD.md / ODD-dev.md / ODD-user.md                 （必需）
├── DDD.md / IDD.md / AID.md / STITCH-PROMPT.md       （条件文档）
├── frontend-ui-spec.md                               （仅 UI -> 首版代码界面任务完成后必补）
├── specs/<module>.md                                 （复杂模块时补）
└── pages/<page>.md                                   （页面复杂时补）
```

目标项目根目录：

```
docs/requirements/
├── customer-facing-prd.md    # 承担 BRD 主文档职责
└── developer-facing-prd.md   # 开发实现需求主文档（需求实现说明、模块拆解与任务边界、场景/规则/验收映射）

README.md                     # design 阶段最低可用版
```

## 下一步推荐

**当前状态**: 设计文档已输出，`design/` 目录已就绪。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

技术架构已经过用户明确确认后，必须先完成 `工作流总纲 §3.7 技术架构确认后的项目 Spec 对齐`，才能进入 `/trellis:plan`。下列内容是执行摘要；若与总纲不一致，以 `§3.7` 为准。

1. **根据技术架构，使用 `trellis-library/cli.py assemble` 选择并导入合适 spec 到当前项目 `.trellis/spec/`**
   - 所有项目至少应覆盖与当前项目直接相关的三类基线约束：
     - `product-and-requirements` 相关 spec：保证需求、范围、验收口径有约束
     - `architecture` 相关 spec：保证系统边界、模块结构、依赖方向等与当前架构一致
     - `verification` 相关 spec：保证 DoD、证据要求、验证门禁可落地
   - 这里要求通过脚本导入，不靠人工复制资产或口头提示“补装”
   - 这里强调的是“选择适配当前项目的最小充分集合”，不是把 `product-and-requirements.*`、`architecture.*`、`verification.*` 整个命名空间全部导入
   - 若为**外部项目**（外包、定制开发、新客户），**额外基础必选**：
     - `spec.universal-domains.project-governance.delivery-control`
     - `checklist.universal-domains.project-governance.transfer-checklist`
   - 若 `assessment.md` 中 `delivery_control_track = trial_authorization`，**额外条件必选**：
     - `spec.universal-domains.project-governance.authorization-management`
   - 若本项目会在正式移交时交付密钥、环境变量、第三方平台配置，**额外条件必选**：
     - `spec.universal-domains.security.secrets-and-config`
   - 根据技术栈按需选择：`spec.universal-domains.security.*`、`spec.universal-domains.data.*` 等

2. **基于当前项目作用/背景/技术架构，对当前项目 `.trellis/spec/` 做分析完善，删除错误内容并补齐缺失内容**

3. **明确项目自动化检查矩阵**
   - 基于已经确认的语言、框架、包管理器、CI、部署方式、安全要求
   - 写清真实会执行的 lint / typecheck / test / build / scan / delivery gate
   - 不允许继续保留”默认检查””按项目自行运行”这类空泛表述
   - 必须有明确的质量平台门禁；采用 Sonar 的项目必须写真实命令，未采用时必须写替代门禁和原因
   - 采用 Sonar 的项目，`sonar-scanner` 至少应以当前项目可执行的真实命令骨架写入检查矩阵，例如：

     ```bash
     sonar-scanner \
       -Dsonar.projectKey=<target-project-key> \
       -Dsonar.token=$SONAR_TOKEN \
       -Dsonar.host.url=https://sonarqube.xzc.com:13785 \
       -Dsonar.sources=.
     ```

   - 未采用 Sonar 的项目，必须显式写出替代质量门禁（如 ESLint strict / CodeQL / 其他 SAST 工具）及其未采用 Sonar 的原因

4. **在技术架构确认后，明确项目级全局测试基线**
   - 这里只确认“所有 task 都统一强制适用”的全局测试/验证要求
   - 例如：统一的测试框架、测试目录约定、必须执行的全局 test / lint / typecheck / build / quality gate
   - 不在当前阶段替每个具体 task 预造测试门禁
   - 每个 task 的具体测试门禁，必须在进入该 task 实现前，由 `/trellis:start` 自动执行 `before-dev` 后补到 `$TASK_DIR/before-dev.md`

5. **同步适配当前项目的 `/trellis:finish-work`**
   - 这是 `finish-work` 的主适配阶段
   - 必须基于任务 3 中已经写清的自动化检查矩阵完成项目化改写
   - `finish-work` 中记录的质量平台门禁必须与任务 3 保持一致（采用 Sonar 的项目写真实命令，未采用时写替代门禁和原因）

6. **同步适配当前项目的 `/trellis:record-session` 基线**
   - 先明确当前项目的记录入口、是否必须走 helper、归档前置条件、哪些元数据允许自动提交
   - 先写清“什么情况下允许进入 record-session”

7. **标记 `§4 plan` 之后是否需要对 `record-session` 做轻量校正**
   - 若任务拆解后，发现“完成任务”的定义、归档节点、交付节点、会话记录粒度和 `§3.7` 基线不一致，再补一次轻量修正
   - 一般不需要在 `§4` 后再次大改 `finish-work`，除非计划阶段新增了新的强制检查门禁

### 双轨资产导入映射表

| 上游字段 / 场景 | 必选资产 | 条件资产 | 设计文档里至少要体现 |
|---|---|---|---|
| 内部项目 | 按项目实际选择的 `product-and-requirements` / `architecture` / `verification` 基线 spec 集合 | 按技术栈补 `security.*` `data.*` | `customer-facing-prd` / `developer-facing-prd` + `TAD` + `ODD-dev` / `ODD-user`；`DDD` / `IDD` / `AID` / `STITCH-PROMPT` 视是否涉及而定 |
| 外部项目 + `delivery_control_track = hosted_deployment` | `delivery-control` `transfer-checklist` | 若正式移交含密钥/配置，再加 `secrets-and-config` | TAD 中写清 retained-control 边界；IDD 与 ODD-dev / ODD-user 中写清交付事件与环境边界 |
| 外部项目 + `delivery_control_track = trial_authorization` | `delivery-control` `transfer-checklist` `authorization-management` | 若正式移交含密钥/配置，再加 `secrets-and-config` | `customer-facing-prd` / IDD 中写清授权状态与到期行为；TAD 与 ODD-dev / ODD-user 中写清正式授权切换与最终移交门禁 |

最低对齐要求：

- `assessment.md` 里的 `delivery_control_track` 必须能在设计文档中找到对应交付模型。
- 若导入了 `authorization-management`，设计文档里必须出现试运行有效期、到期行为、永久授权触发条件。
- 若判断需要 `secrets-and-config`，设计文档里必须明确哪些密钥/配置属于最终移交范围，不能只在 checklist 再补。

阶段结论：

- `/trellis:finish-work` 的项目化适配主阶段是当前 `design -> spec 对齐` 阶段
- 当前阶段只定义项目级全局测试基线；task 级具体测试门禁延后到实施前补充
- `/trellis:record-session` 的基线适配也在当前阶段完成，`§4 plan` 后仅允许做一次轻量校正
- 进入 `/trellis:plan` 前，至少要完成上述 1-6；第 7 项只负责标记是否需要在 `plan` 后补一次轻量修正，不阻止进入 `plan`

根据你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 拆解任务 | `/trellis:plan` | 进入任务拆解，或显式触发 `plan` skill | **默认推荐**。前提是已完成项目 `.trellis/spec/` 对齐门禁，再将设计转化为可执行任务 |
| 项目简单，不需要拆任务 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | 直接进入实施；start 会自动执行 before-dev 并补 task 门禁。若当前 task 是 `UI -> 首版代码界面`，主执行 CLI 仍必须改用 Claude Code / OpenCode |
| 需要显式先测某个 task | `/trellis:test-first` | 进入手动测试驱动，或显式触发 `test-first` skill | 非默认主链；仅在明确要先测/补测试证据时进入 |
| 更简单，直接写代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | 跳过显式 test-first；但不跳过 before-dev 自动前置。若属于视觉前端首版落地 task，Codex 不能作为主执行器 |
| 设计不完善，回退修改 | `/trellis:design` | 继续补设计，或显式触发 `design` skill | 重新执行某一步骤 |
| 冻结后出现新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 不直接吸收，获批后再回到受影响的最早阶段 |
| 冻结后仅需纯澄清 | 留在当前阶段 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 检查跨层一致性 | `/trellis:check-cross-layer` | 检查跨层影响，或显式触发 `check-cross-layer` skill | 设计涉及多层时建议执行 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |

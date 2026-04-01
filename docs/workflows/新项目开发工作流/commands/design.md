---
name: design
description: 需求冻结了？开始设计 — UI/UX、架构选型、接口设计、文档输出。触发词：开始设计、画架构图、技术选型、设计方案
---

# /trellis:design — 设计阶段引导

> **Workflow Position**: §3 → 前: `/trellis:brainstorm` → 后: `/trellis:plan`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:design`） · ✅ Cursor（命令名: design） · ✅ OpenCode（TUI: `/trellis:design`；CLI: `trellis/design`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:design` 命令；见 `codex/README.md`） · ⚠️ Gemini（兼容层；见 `gemini/README.md`）

---

## When to Use (自然触发)

- "开始设计吧"
- "画个架构图"
- "需要做技术选型"
- "出个设计方案"
- "帮我设计一下接口"
- "PRD 已经确认了，下一步怎么做"

> 若 `PRD` 已冻结后命中需求讨论，按 `§2.5` 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入需求变更管理，不直接在本阶段吸收。

---

## 流程

### Step 1: UI/UX 设计（如有前端）

**调用 Skill**：使用 Skill 工具执行 `ui-ux-pro-max`，生成页面布局粗稿、组件建议、交互流程。若该 skill 不可用，手动从 PRD 提取页面目标后直接进入外部工具设计。

**强制提醒**：

- 只要当前项目进入了“需要页面视觉设计、页面布局设计、交互原型设计”的阶段，就必须明确提醒用户：这一步需要去外部 UI 设计工具完成，不要只停留在当前 CLI 里讨论。
- 推荐外部操作顺序：
  1. 先去 [UI Prompt Styles](https://www.uiprompt.site/zh/styles) 获取接近目标风格的 UI 提示词
  2. 再去 [Stitch](https://stitch.withgoogle.com/) 粘贴整理后的提示词，生成页面级 UI 原型

**建议引导话术**：

> 现在已经进入需要外部 UI 设计的阶段。请先去 `https://www.uiprompt.site/zh/styles` 选择合适的 UI 风格提示词，再把页面目标、关键模块、交互要求和风格提示词整理后带到 `https://stitch.withgoogle.com/` 生成 UI 原型。完成后，再回到当前工作流继续补齐设计说明和技术方案。

**最小执行步骤**：

1. 从 PRD 提取页面目标、用户角色、关键流程、品牌/风格约束
2. 在 `https://www.uiprompt.site/zh/styles` 选择合适风格，生成或整理可直接复用的 UI 提示词
3. 将页面需求和 UI 提示词一起带到 `https://stitch.withgoogle.com/`，生成首版页面原型
4. 回到当前任务，把确认后的页面结构、组件清单、交互要点沉淀到 `design/specs/` 与 `design/pages/`

### Step 2: 功能规格说明

为每个模块生成 `design/specs/<module>.md`

### Step 3: 可执行原型验证

覆盖 1 主流程 + 1 异常 + 1 空数据

### Step 4: 页面与交互说明

为每个页面生成 `design/pages/<page>.md`

### Step 4.5: MCP 能力路由

| 场景 | 调用能力 | 调用级别 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 按需 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 按需 | 回退：`grok-search` |
| 复杂架构推理 | `sequential-thinking` | 按需 | 当架构决策涉及 ≥3 个技术方案对比或推理步骤 >3 步时触发 |
| 架构图可视化 | `markmap` | 按需 | 模块依赖图、技术栈确认 |
| 框架 / SDK API 文档 | `Context7` | 默认 | 技术选型时必须查阅官方文档作为决策依据，不依赖训练数据中的过时信息。无法获取时标记 `[Evidence Gap]` |

### Step 5: 技术方案设计

**MCP 能力路由**

| 场景 | 调用能力 | 调用级别 | 说明 |
|------|---------|---------|------|
| 参考 GitHub 开源架构 | `deepwiki` | 按需 | 回退：`exa_search` |
| 技术选型深度研究 | `exa_create_research` | 按需 | 回退：`grok-search`。没有官方文档证据时，不下 API/框架细节结论，只保留待验证设计假设 |
| 复杂架构推理 | `sequential-thinking` | 按需 | 当架构决策涉及 ≥3 个技术方案对比或推理步骤 >3 步时触发 |
| 架构图可视化 | `markmap` | 按需 | 架构图/模块依赖图 |

**按需调用 Skill**（根据领域选择，使用 Skill 工具执行对应 skill）：

| 领域 | Skill |
|------|-------|
| 架构模式 | `architecture-patterns` |
| 后端架构 | `backend-patterns` |
| API 设计 | `api-design-principles` |
| 数据库 | `postgresql-table-design` |
| 文档撰写 | `doc-coauthoring` |

### Step 6: 文档输出

```bash
python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate
```

输出文档体系：`design/BRD.md` `TAD.md` `DDD.md` `IDD.md` `AID.md` `ODD.md`

---

## 输出

```
$TASK_DIR/design/
├── index.md
├── BRD/TAD/DDD/IDD/ODD.md
├── specs/<module>.md
└── pages/<page>.md
```

## 下一步推荐

**当前状态**: 设计文档已输出，`design/` 目录已就绪。

技术架构已经过用户明确确认后，必须先完成 `工作流总纲 §3.7 技术架构确认后的项目 Spec 对齐`，才能进入 `/trellis:plan`。下列内容是执行摘要；若与总纲不一致，以 `§3.7` 为准。

1. **根据技术架构，从 `trellis-library` 选择并导入合适 spec 到当前项目 `.trellis/spec/`**
   - 所有项目至少应覆盖与当前项目直接相关的三类基线约束：
     - `product-and-requirements` 相关 spec：保证需求、范围、验收口径有约束
     - `architecture` 相关 spec：保证系统边界、模块结构、依赖方向等与当前架构一致
     - `verification` 相关 spec：保证 DoD、证据要求、验证门禁可落地
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
   - 不允许继续保留“默认检查”“按项目自行运行”这类空泛表述

4. **同步适配当前项目的 `/trellis:finish-work`**
   - 这是 `finish-work` 的主适配阶段
   - 必须基于任务 3 中已经写清的自动化检查矩阵完成项目化改写

5. **同步适配当前项目的 `/trellis:record-session` 基线**
   - 先明确当前项目的记录入口、是否必须走 helper、归档前置条件、哪些元数据允许自动提交
   - 先写清“什么情况下允许进入 record-session”

6. **标记 `§4 plan` 之后是否需要对 `record-session` 做轻量校正**
   - 若任务拆解后，发现“完成任务”的定义、归档节点、交付节点、会话记录粒度和 `§3.7` 基线不一致，再补一次轻量修正
   - 一般不需要在 `§4` 后再次大改 `finish-work`，除非计划阶段新增了新的强制检查门禁

### 双轨资产导入映射表

| 上游字段 / 场景 | 必选资产 | 条件资产 | 设计文档里至少要体现 |
|---|---|---|---|
| 内部项目 | 按项目实际选择的 `product-and-requirements` / `architecture` / `verification` 基线 spec 集合 | 按技术栈补 `security.*` `data.*` | 常规 BRD/TAD/DDD/IDD/AID/ODD |
| 外部项目 + `delivery_control_track = hosted_deployment` | `delivery-control` `transfer-checklist` | 若正式移交含密钥/配置，再加 `secrets-and-config` | TAD 中写清 retained-control 边界；IDD/ODD 中写清交付事件与环境边界 |
| 外部项目 + `delivery_control_track = trial_authorization` | `delivery-control` `transfer-checklist` `authorization-management` | 若正式移交含密钥/配置，再加 `secrets-and-config` | BRD/IDD 中写清授权状态与到期行为；TAD/ODD 中写清正式授权切换与最终移交门禁 |

最低对齐要求：

- `assessment.md` 里的 `delivery_control_track` 必须能在设计文档中找到对应交付模型。
- 若导入了 `authorization-management`，设计文档里必须出现试运行有效期、到期行为、永久授权触发条件。
- 若判断需要 `secrets-and-config`，设计文档里必须明确哪些密钥/配置属于最终移交范围，不能只在 checklist 再补。

阶段结论：

- `/trellis:finish-work` 的项目化适配主阶段是当前 `design -> spec 对齐` 阶段
- `/trellis:record-session` 的基线适配也在当前阶段完成，`§4 plan` 后仅允许做一次轻量校正
- 进入 `/trellis:plan` 前，至少要完成上述 1-5；第 6 项只负责标记是否需要在 `plan` 后补一次轻量修正，不阻止进入 `plan`

根据你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 拆解任务 | `/trellis:plan` | 进入任务拆解，或显式触发 `plan` skill | **默认推荐**。前提是已完成项目 `.trellis/spec/` 对齐门禁，再将设计转化为可执行任务 |
| 项目简单，不需要拆任务 | `/trellis:test-first` | 直接进入测试驱动，或显式触发 `test-first` skill | 直接进入测试驱动 |
| 更简单，直接写代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | 跳过 plan + test-first |
| 设计不完善，回退修改 | `/trellis:design` | 继续补设计，或显式触发 `design` skill | 重新执行某一步骤 |
| 冻结后出现新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 同上 | 不直接吸收，获批后再回到受影响的最早阶段 |
| 冻结后仅需纯澄清 | 留在当前阶段 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 检查跨层一致性 | `/trellis:check-cross-layer` | 检查跨层影响，或显式触发 `check-cross-layer` skill | 设计涉及多层时建议执行 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由自动检测 |

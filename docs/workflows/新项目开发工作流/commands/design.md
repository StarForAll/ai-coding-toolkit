---
name: design
description: 需求冻结了？开始设计 — UI/UX、架构选型、接口设计、文档输出。触发词：开始设计、画架构图、技术选型、设计方案
---

# /trellis:design — 设计阶段引导

> **Workflow Position**: §3 → 前: `/trellis:brainstorm` → 后: `/trellis:plan`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: design) · ⚠️ OpenCode · ⚠️ Codex/Gemini

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

**Skill**: `ui-ux-pro-max` — AI 生成页面布局粗稿、组件建议、交互流程

### Step 2: 功能规格说明

为每个模块生成 `design/specs/<module>.md`

### Step 3: 可执行原型验证

覆盖 1 主流程 + 1 异常 + 1 空数据

### Step 4: 页面与交互说明

为每个页面生成 `design/pages/<page>.md`

### Step 5: 技术方案设计

按需加载 Skills：

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

技术架构已经过用户明确确认后，必须先完成以下前置任务，才能进入 `/trellis:plan`：

1. **根据技术架构，从 `trellis-library` 选择并导入合适 spec 到当前项目 `.trellis/spec/`**
   - 必选基础 spec（所有项目）：
     - `spec.universal-domains.product-and-requirements.*`（PRD 相关）
     - `spec.universal-domains.architecture.*`（架构相关）
     - `spec.universal-domains.verification.*`（验证相关）
   - 若为**外部项目**（外包、定制开发、新客户），**额外基础必选**：
     - `spec.universal-domains.project-governance.delivery-control`
     - `checklist.universal-domains.project-governance.transfer-checklist`
   - 若 `assessment.md` 中 `delivery_control_track = trial_authorization`，**额外条件必选**：
     - `spec.universal-domains.project-governance.authorization-management`
   - 若本项目会在正式移交时交付密钥、环境变量、第三方平台配置，**额外条件必选**：
     - `spec.universal-domains.security.secrets-and-config`
   - 根据技术栈按需选择：`spec.universal-domains.security.*`、`spec.universal-domains.data.*` 等

2. **基于当前项目作用/背景/技术架构，对当前项目 `.trellis/spec/` 做分析完善，删除错误内容并补齐缺失内容**

3. **同步做收尾命令的项目化适配**
   - **`/trellis:finish-work`：在本阶段一次定准**
     - 基于已经确认的语言、框架、包管理器、CI、部署方式、安全要求
     - 把当前项目真实会执行的 lint / typecheck / test / build / scan / delivery gate 写进对应项目的 `finish-work`
     - 不允许继续保留“默认检查”“按项目自行运行”这类空泛表述
   - **`/trellis:record-session`：在本阶段先定基线**
     - 先明确当前项目的记录入口、是否必须走 helper、归档前置条件、哪些元数据允许自动提交
     - 先写清“什么情况下允许进入 record-session”
     - 如果后续 `§4 plan` 拆解任务后，任务归档边界、里程碑节点、记录粒度变得更明确，可以再做一次**轻量校正**，但不应推迟到开发结束才第一次处理

4. **确认 `§4 plan` 之后是否需要对 `record-session` 做轻量校正**
   - 若任务拆解后，发现“完成任务”的定义、归档节点、交付节点、会话记录粒度和 `§3.7` 基线不一致，再补一次轻量修正
   - 一般不需要在 `§4` 后再次大改 `finish-work`，除非计划阶段新增了新的强制检查门禁

### 双轨资产导入映射表

| 上游字段 / 场景 | 必选资产 | 条件资产 | 设计文档里至少要体现 |
|---|---|---|---|
| 内部项目 | `product-and-requirements.*` `architecture.*` `verification.*` | 按技术栈补 `security.*` `data.*` | 常规 BRD/TAD/DDD/IDD/AID/ODD |
| 外部项目 + `delivery_control_track = hosted_deployment` | `delivery-control` `transfer-checklist` | 若正式移交含密钥/配置，再加 `secrets-and-config` | TAD 中写清 retained-control 边界；IDD/ODD 中写清交付事件与环境边界 |
| 外部项目 + `delivery_control_track = trial_authorization` | `delivery-control` `transfer-checklist` `authorization-management` | 若正式移交含密钥/配置，再加 `secrets-and-config` | BRD/IDD 中写清授权状态与到期行为；TAD/ODD 中写清正式授权切换与最终移交门禁 |

最低对齐要求：

- `assessment.md` 里的 `delivery_control_track` 必须能在设计文档中找到对应交付模型。
- 若导入了 `authorization-management`，设计文档里必须出现试运行有效期、到期行为、永久授权触发条件。
- 若判断需要 `secrets-and-config`，设计文档里必须明确哪些密钥/配置属于最终移交范围，不能只在 checklist 再补。

阶段结论：

- `/trellis:finish-work` 的项目化适配主阶段是当前 `design -> spec 对齐` 阶段
- `/trellis:record-session` 的基线适配也在当前阶段完成，`§4 plan` 后仅允许做一次轻量校正

根据你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 拆解任务 | `/trellis:plan` | **默认推荐**。前提是已完成项目 `.trellis/spec/` 对齐门禁，再将设计转化为可执行任务 |
| 项目简单，不需要拆任务 | `/trellis:test-first` | 直接进入测试驱动 |
| 更简单，直接写代码 | `/trellis:start` | 跳过 plan + test-first |
| 设计不完善，回退修改 | `/trellis:design` | 重新执行某一步骤 |
| 冻结后出现新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 不直接吸收，获批后再回到受影响的最早阶段 |
| 冻结后仅需纯澄清 | 留在当前阶段 | 仅限不改变范围、接口契约、验收标准、成本、工期 |
| 检查跨层一致性 | `/trellis:check-cross-layer` | 设计涉及多层时建议执行 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |

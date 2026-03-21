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

根据你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 拆解任务 | `/trellis:plan` | **默认推荐**。将设计转化为可执行任务 |
| 项目简单，不需要拆任务 | `/trellis:test-first` | 直接进入测试驱动 |
| 更简单，直接写代码 | `/trellis:start` | 跳过 plan + test-first |
| 设计不完善，回退修改 | `/trellis:design` | 重新执行某一步骤 |
| 需求可能需要调整 | `/trellis:brainstorm` | 回到需求层重新讨论 |
| 检查跨层一致性 | `/trellis:check-cross-layer` | 设计涉及多层时建议执行 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |

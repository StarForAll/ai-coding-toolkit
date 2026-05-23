# Research: 工作流嵌入对原生 Trellis 框架的修改对比分析

- **Query**: 对比纯 trellis 框架项目与嵌入了"新项目开发工作流"项目的核心配置文件差异
- **Scope**: internal
- **Date**: 2026-05-23

## Findings

### 对比项目

| 项目 | 路径 | 描述 |
|---|---|---|
| 原生 Trellis | `/tmp/trellis-0.5.17-1/` | 纯 trellis-0.5.17 初始化项目 |
| 嵌入工作流 | `/tmp/trellis-0.5.17-2/` | 嵌入"新项目开发工作流"(v0.1.28, outsourcing profile)的项目 |

---

## 1. `workflow.md` - 工作流主文件

**性质**: 覆盖/替换了原生文件（原生内容已备份至 `.backup-original/workflow.md`）

### 1.1 删除的原生内容

| 原生 section | 描述 | 修改类型 |
|---|---|---|
| `WORKFLOW-STATE BREADCRUMB CONTRACT` 注释块 | 原生 breadcrumb 契约文档 | **覆盖** - 整段删除，被新契约取代 |
| `Phase Index` 的三阶段模型 (`Phase 1: Plan / Phase 2: Execute / Phase 3: Finish`) | 原生三阶段编号系统 | **覆盖** - 被九阶段门禁模型取代 |
| `[workflow-state:no_task]` 原生内容 | 原生无任务入口指引 | **覆盖** - 被强门禁版本取代，新增 A/A+/B/C 分层 |
| `[workflow-state:planning]` | 原生规划阶段 breadcrumb | **覆盖** - 完全移除 |
| `[workflow-state:planning-inline]` | 原生 codex inline 规划 breadcrumb | **覆盖** - 完全移除 |
| `[workflow-state:in_progress]` | 原生执行阶段 breadcrumb | **覆盖** - 完全移除 |
| `[workflow-state:in_progress-inline]` | 原生 codex inline 执行 breadcrumb | **覆盖** - 完全移除 |
| `[workflow-state:completed]` | 原生完成阶段 breadcrumb | **覆盖** - 完全移除 |
| `Phase 1: Plan` 完整内容 (1.0-1.5) | 含任务创建、需求探索、研究、jsonl 配置、激活等 | **覆盖** - 被简化兼容层取代 |
| `Phase 2: Execute` 完整内容 (2.1-2.3) | 含实现、质检、回滚 | **覆盖** - 被简化兼容层取代 |
| `Phase 3: Finish` 完整内容 (3.1-3.5) | 含质检验证、调试回顾、spec更新、提交、收尾 | **覆盖** - 被简化兼容层取代 |
| `Skill Routing` 表 + `DO NOT skip skills` 表 | 原生技能路由和跳过警告 | **覆盖** - 完全移除 |
| `Loading Step Detail` | 原生步骤详情加载指引 | **覆盖** - 移除 |
| `Customizing Trellis` 中 "All customization is done by editing this file; the scripts are parsers only" | 原生声明脚本仅解析器 | **覆盖** - 替换为更复杂的定制指引（含 runtime scripts 和 patch templates） |

### 1.2 新增的内容

| 新增 section | 描述 | 修改类型 |
|---|---|---|
| `<!-- workflow-projectization-patch -->` 标记 | 开发流程 section 的补丁标记 | **纯新增** |
| `Task Development Flow` | 强门禁六步流程：route -> create/reuse -> confirm gates -> execute authorized -> verify+commit -> close-out | **纯新增** |
| `Code Quality Checklist` | 新增 Trellis 相关同步要求（同步 .claude/.opencode/.agents/skills/.codex） | **纯新增** |
| `Session End` section | 新增两阶段收尾：Phase A (delivery) + Phase B (native finish-work) | **纯新增** |
| `Pre-end Checklist` | delivery 阶段检查项（冻结验证、验收、所有权证明） | **纯新增** |
| `<!-- workflow-projectization-phase-index-patch -->` 标记 | Phase Index section 的补丁标记 | **纯新增** |
| 九阶段模型 | `feasibility -> brainstorm -> design -> plan -> implementation -> project-audit -> check -> review-gate -> delivery` | **覆盖** - 替代原生三阶段 |
| `Stage Transition Quick Reference` | 完整的阶段转换两步协议表（18+行转换规则） | **纯新增** |
| `Baseline Step Compatibility` | 1.0-3.5 的兼容层（简化版，指向 workflow-state.py） | **覆盖** - 替代原生详细步骤 |
| `Customizing Trellis` 中新内容 | 新增 "runtime contract also lives in workflow-state.py, installer patchers, and carrier patches" 约束 | **覆盖** - 替代原生 "scripts are parsers only" 声明 |
| `<!-- workflow-projectization-breadcrumb-patch -->` 标记 | breadcrumb 补丁标记 | **纯新增** |
| 9 个强门禁阶段 breadcrumb blocks | `[workflow-state:feasibility]` / `brainstorm` / `design` / `plan` / `implementation` / `project-audit` / `check` / `review-gate` / `delivery` | **覆盖** - 替代原生 4 个 breadcrumb |
| 7 个路由动作 breadcrumb blocks | `awaiting_confirmation` / `awaiting_confirmation_with_blockers` / `blocked` / `context_needed` / `recovery_needed` / `repair_needed` / `embed_invalid` / `workflow-state.route_failed` | **纯新增** |
| `<!-- workflow-projectization-no-task-patch -->` 标记 | no_task section 的补丁标记 | **纯新增** |
| `[workflow-state:no_task]` 强门禁版 | 新增 A(A+深度分析)/B/C 分层，含 outsourcing/personal 双入口路径 | **覆盖** - 替代原生 A/B/C 分层 |

### 1.3 原生 Task System 描述的覆盖

| 原生段落 | 原生内容 | 嵌入后修改 |
|---|---|---|
| `task.py start` 行为 | "`task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`" | **覆盖** - 改为 "patched `task.py start` refreshes the active-task pointer... does **not** perform the legacy `planning -> in_progress` flip" |
| `workflow-state.json` 角色 | 无提及 | **覆盖** - 新增 "Runtime stage routing is determined by `.trellis/.runtime/sessions/<context>.json -> $TASK_DIR/workflow-state.json.stage`" |
| `strong-gate task views` | 无 | **覆盖** - 新增 "If `workflow-state.json` is missing... strong-gate task views surface `repair_needed` instead of reusing legacy planning semantics" |
| 降级行为 | "`task.py start` fails with a session identity hint" | **覆盖** - 改为 "follows the Trellis baseline degraded behavior and does not persist an active-task pointer for that shell" |

---

## 2. `workflow-state.json` - 工作流状态

**性质**: 纯新增

原生项目无此文件。嵌入项目在每个活跃任务目录下会生成 `workflow-state.json`，由 `workflow-state.py` 管理。文件包含 stage、stage_status、checkpoints、allowed_next 等强门禁状态字段。这是工作流嵌入的**核心新增机制**，取代了原生 `task.json.status` 作为阶段路由唯一来源的地位。

---

## 3. `scripts/` 目录 - 脚本文件

### 3.1 新增脚本（全部纯新增）

| 文件路径 | 功能 |
|---|---|
| `scripts/workflow/workflow-state.py` | **核心新增** - 强门禁状态机管理器(2734行)，含 route/set/init/validate/repair 命令 |
| `scripts/workflow/check-quality.py` | 质量检查辅助脚本 |
| `scripts/workflow/delivery-control-validate.py` | 双轨交付控制验证 |
| `scripts/workflow/design-export.py` | 设计目录文档脚手架与验证 |
| `scripts/workflow/feasibility-check.py` | 可行性评估模板与合规审查 |
| `scripts/workflow/ownership-proof-validate.py` | 源码水印与归属证明验证 |
| `scripts/workflow/plan-validate.py` | 任务拆解摘要结构验证 |
| `scripts/workflow/source-watermark-guard.py` | 源码水印保护片段验证与修复 |

### 3.2 新增补丁脚本（用于修改原生脚本，全部纯新增载体）

| 文件路径 | 功能 | 补丁目标 |
|---|---|---|
| `scripts/workflow/patch-inject-workflow-state.py` | 修改 hook carriers 使用 workflow-state.py route 作为面包屑来源 | inject-workflow-state hook |
| `scripts/workflow/patch-session-start-strong-gate.py` | 修改 session-start.py 使用强门禁路由 | session-start carrier |
| `scripts/workflow/patch-task-create-preserve-active.py` | 修改 task_store.py 创建流程，保留当前活跃任务 | task_store.py cmd_create() |
| `scripts/workflow/patch-task-start-strong-gate.py` | 修改 task.py cmd_start() 跳过状态翻转 | task.py cmd_start() |
| `scripts/workflow/patch-task-status-view-strong-gate.py` | 修改任务运行时视图显示强门禁阶段 | tasks.py Task class |
| `scripts/workflow/patch-workflow-phase.py` | 修改 workflow_phase.py 拒绝旧 step 查询 | workflow_phase.py get_step() |
| `scripts/workflow/patch-workflow-phase-strong-gate.py` | patch-workflow-phase.py 的兼容包装器 | 同上 |

### 3.3 修改的原生脚本

#### 3.3.1 `scripts/task.py`

**性质**: 覆盖/替换了原生行为

| 修改位置 | 原生内容 | 修改后 | 修改类型 |
|---|---|---|---|
| `cmd_start()` 状态翻转 (degraded path) | `data["status"] = "in_progress"` + 打印成功 | **覆盖** - 跳过翻转，打印 "Strong-gate mode: skipping legacy task.json status flip" | **破坏性修改** - 禁用了原生状态推进 |
| `cmd_start()` 状态翻转 (正常 path) | `data["status"] = "in_progress"` + 打印成功 | **覆盖** - 同上跳过翻转 | **破坏性修改** - 禁用了原生状态推进 |
| 注释行 | "Still flip task.json status: planning -> in_progress so downstream phases proceed." | **覆盖** - "Strong-gate mode keeps workflow-state.py route as the only stage authority." | **覆盖** - 改变语义 |
| `cmd_list()` 输出格式 | `({t.status})` | 新增 `_workflow_display_extra` 字段和显示 | **修改** - 增强输出 |
| `--status` 帮助文本 | "Filter by status (planning, in_progress, review, completed)" | **覆盖** - "Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)" | **覆盖** - 改变参数语义 |
| 帮助示例 | `--status in_progress` | **覆盖** - `--status check` | **覆盖** |

#### 3.3.2 `scripts/common/tasks.py`

**性质**: 覆盖/替换了原生行为 + 纯新增

| 修改内容 | 修改类型 |
|---|---|
| 新增 `WORKFLOW_STATE_FILE_NAME`、`TERMINAL_TASK_STATUSES` 常量 | **纯新增** |
| 新增 `_shorten_status_detail()` 函数 | **纯新增** |
| 新增 `_workflow_state_summary()` 函数 | **纯新增** |
| 新增 `_display_status()` 函数 - 读取 workflow-state.json 并决定展示用状态 | **覆盖** - 替代原生 `task.json.status` 直接展示 |
| Task 构造函数：新增 `_workflow_display_extra` 字段计算 | **纯新增** |
| Task 构造函数：`status` 字段从 `data.get("status")` 改为 `display_status` | **破坏性修改** - 不再使用 task.json.status 作为展示状态，改用 workflow-state.json.stage |

#### 3.3.3 `scripts/common/task_store.py`

**性质**: 修改了原生行为

| 修改内容 | 修改类型 |
|---|---|
| `cmd_create()` 中活跃任务切换逻辑：新增 `TRELLIS_PRESERVE_ACTIVE_TASK` 环境变量检查 | **纯新增** - 可选行为，仅在 env var 设置时生效 |
| 当 `TRELLIS_PRESERVE_ACTIVE_TASK=1` 且 `args.parent` 存在时，跳过自动激活 | **纯新增** - 不影响默认行为 |

#### 3.3.4 `scripts/common/task_queue.py`

**性质**: 覆盖/替换了原生行为

| 修改内容 | 修改类型 |
|---|---|
| `pending_tasks()`: 原来只列出 `status=planning` 的任务 | **覆盖** - 改为 `list_tasks_by_status(None, repo_root)` 列出所有非归档任务 | **破坏性修改** - 改变了 "pending" 的语义 |

#### 3.3.5 `scripts/common/workflow_phase.py`

**性质**: 覆盖/替换了原生行为

| 修改内容 | 修改类型 |
|---|---|
| `get_step()` 末尾新增 42 行强门禁补丁：当检测到 workflow-state.json 存在且 stage 为强门禁阶段时，打印警告并返回空字符串 | **破坏性修改** - 禁用了原生 `get_context.py --mode phase --step X.Y` 功能 |

---

## 4. `config.yaml` - 配置文件

**性质**: 无差异

两个项目的 `config.yaml` 内容完全相同。

---

## 5. `spec/` 目录 - 规约文件

### 5.1 修改的原生文件

| 文件路径 | 原生内容 | 嵌入后修改 | 修改类型 |
|---|---|---|---|
| `spec/backend/quality-guidelines.md` | "Overview" section + "To be filled by the team" 占位符 | **覆盖** - "Verification Matrix" section + "Defined during design stage §3.7; not pre-populated." | **覆盖** - 替代了团队自填模式 |
| `spec/frontend/quality-guidelines.md` | 同上 | **覆盖** - 同上 | **覆盖** |
| `spec/guides/cross-layer-thinking-guide.md` | `/trellis:check-cross-layer` 命令引用 | **覆盖** - 改为 `/trellis:check` 并手动指定跨层范围 | **覆盖** |

### 5.2 新增的 spec 文件（全部纯新增）

**`spec/universal-domains/`** - 11 个子目录，每目录 4 文件(overview/normative-rules/scope-boundary/verification):

- `product-and-requirements/problem-definition/`
- `product-and-requirements/scope-boundary/`
- `product-and-requirements/requirement-clarification/`
- `product-and-requirements/acceptance-criteria/`
- `product-and-requirements/prd-documentation/`
- `product-and-requirements/prd-documentation-customer-facing/`
- `product-and-requirements/prd-documentation-developer-facing/`
- `project-governance/readme-governance/`
- `verification/evidence-requirements/`
- `architecture/system-boundaries/`

**`spec/scenarios/`** - 1 个子目录:

- `discovery-and-planning/solution-comparison/` (4 文件)

---

## 6. `checklists/` 目录 - 检查清单

**性质**: 纯新增

原生项目无 checklists 目录。嵌入项目新增：

| 文件路径 | 描述 |
|---|---|
| `checklists/universal-domains/product-and-requirements/acceptance-quality-checklist.md` | 验收质量检查清单 |
| `checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md` | 面向客户 PRD 检查清单 |
| `checklists/universal-domains/product-and-requirements/developer-facing-prd-checklist.md` | 面向开发者 PRD 检查清单 |

---

## 7. `templates/` 目录 - 模板

**性质**: 纯新增

原生项目无 templates 目录。嵌入项目新增：

| 文件路径 | 描述 |
|---|---|
| `templates/universal-domains/product-and-requirements/acceptance-criteria-template.md` | 验收标准模板 |
| `templates/universal-domains/product-and-requirements/customer-facing-prd-template.md` | 面向客户 PRD 模板 |
| `templates/universal-domains/product-and-requirements/developer-facing-prd-template.md` | 面向开发者 PRD 模板 |

---

## 8. `hooks/` 目录 - Hook 文件

**性质**: 无差异

两个项目均无 `.trellis/hooks/` 目录。Hook 相关修改是通过 patch 脚本作用于平台侧 hooks（如 `.claude/`、`.opencode/` 等），而非 `.trellis/hooks/` 内部。

---

## 9. `commands/` 目录 - 命令文件

**性质**: 无差异

两个项目均无 `.trellis/commands/` 目录。根据 `workflow-installed.json`，工作流通过 `overlay_commands`（brainstorm/check）和 `added_commands`（feasibility/design/plan/project-audit/review-gate/delivery）在平台侧提供命令。

---

## 10. `skills/` 目录 - 技能文件

**性质**: 无差异

两个项目均无 `.trellis/skills/` 目录。

---

## 11. 其他新增文件

| 文件路径 | 描述 | 修改类型 |
|---|---|---|
| `workflow-installed.json` | 工作流安装记录，含版本、profile、命令列表、补丁列表等 | **纯新增** |
| `library-lock.yaml` | library 资产锁文件，记录所有导入的 spec/template/checklist/example 资产 | **纯新增** |
| `library-assets/examples/` | 示例文档目录 | **纯新增** |
| `workflow-docs/需求变更管理执行卡.md` | 需求变更管理可执行载体 | **纯新增** |
| `workflow-docs/源码水印与归属证据链执行卡.md` | 源码水印与归属证据链可执行载体 | **纯新增** |
| `.backup-original/workflow.md` | 原生 workflow.md 的备份 | **纯新增** - 保留原始文件副本 |

---

## 破坏性修改汇总

| 文件 | 破坏性修改 | 影响 |
|---|---|---|
| `workflow.md` | 完全覆盖原生三阶段模型，替换为九阶段门禁模型 | 原生 Phase 1/2/3 工作流不再可用 |
| `workflow.md` | 删除原生 4 个 breadcrumb blocks，替换为 16+ 个新 blocks | 依赖原生 breadcrumb 的 hook 解析行为彻底改变 |
| `workflow.md` | 覆盖 Task System 段落中 `task.py start` 的行为描述 | 原生状态翻转语义被声明为无效 |
| `scripts/task.py` | `cmd_start()` 不再翻转 `task.json.status` | 依赖 `planning -> in_progress` 状态变化的下游逻辑断裂 |
| `scripts/common/tasks.py` | `Task.status` 不再使用 `task.json.status`，改用 `workflow-state.json.stage` | 所有读取 Task.status 的代码获得的是阶段名而非原生状态 |
| `scripts/common/task_queue.py` | `pending_tasks()` 返回所有非归档任务而非仅 `status=planning` | "pending" 语义变化，可能影响过滤/统计逻辑 |
| `scripts/common/workflow_phase.py` | `get_step()` 在强门禁模式下返回空字符串 | 原生 `get_context.py --mode phase --step X.Y` 功能被禁用 |
| `spec/backend/quality-guidelines.md` | "To be filled by the team" 替换为 "Defined during design stage §3.7" | 原生团队自填质量标准的能力被禁用 |
| `spec/frontend/quality-guidelines.md` | 同上 | 同上 |

## 冗余修改汇总

| 文件 | 冗余点 | 说明 |
|---|---|---|
| `scripts/common/tasks.py` + `scripts/task.py` | 任务状态展示逻辑 | 原生 `task.json.status` 仍存在但不再用于展示，`_display_status()` 读取 `workflow-state.json` 作为替代来源，两套状态体系并存 |
| `workflow.md` Baseline Step Compatibility | 1.0-3.5 编号步骤 | 作为兼容层保留，但 `workflow_phase.py` 的 `get_step()` 已被补丁禁用，这些编号步骤实际上不可通过 `get_context.py --mode phase --step` 访问 |
| `workflow.md` Customizing Trellis | 仍提及 `[workflow-state:STATUS]` block 编辑 | 但新增约束要求同步修改 `workflow-state.py` 和 patch templates，原生的"只编辑此文件"模式不再成立 |

## Caveats / Not Found

- `workflow-state.json` 在项目根 `.trellis/` 下不存在，它存在于任务子目录中
- hooks/commands/skills 目录在两个项目中均不存在于 `.trellis/` 下，工作流通过平台侧（.claude/ 等）分发命令和技能
- 补丁脚本（patch-*.py）是安装时执行的载体，运行后修改目标文件并嵌入标记；嵌入项目的原生脚本已经包含了补丁结果

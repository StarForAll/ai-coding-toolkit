# Research: 工作流嵌入脚本与模板对原生 trellis 框架的影响分析

- **Query**: 深度分析工作流嵌入的脚本和模板对原生 trellis 框架的影响
- **Scope**: mixed (internal code comparison + external pattern analysis)
- **Date**: 2026-05-23

## Findings

### 1. 文件清单

#### 原生框架脚本 (7,481 行)

| 文件路径 | 行数 | 描述 |
|---|---|---|
| `scripts/task.py` | 500 | 主任务管理 CLI |
| `scripts/add_session.py` | 547 | 日志/会话管理 |
| `scripts/init_developer.py` | 51 | 开发者初始化 |
| `scripts/get_context.py` | 16 | git 上下文 thin wrapper |
| `scripts/get_developer.py` | 26 | 开发者名 thin wrapper |
| `scripts/common/active_task.py` | 626 | 活动任务解析 |
| `scripts/common/cli_adapter.py` | 811 | CLI 适配层 |
| `scripts/common/config.py` | 445 | 配置管理 |
| `scripts/common/developer.py` | 190 | 开发者信息 |
| `scripts/common/git_context.py` | 106 | Git 上下文 |
| `scripts/common/io.py` | 37 | JSON I/O |
| `scripts/common/packages_context.py` | 238 | 包上下文 |
| `scripts/common/paths.py` | 447 | 路径常量与解析 |
| `scripts/common/safe_commit.py` | 285 | 安全提交 |
| `scripts/common/session_context.py` | 821 | 会话上下文 |
| `scripts/common/task_context.py` | 223 | 任务上下文 JSONL |
| `scripts/common/task_queue.py` | 188 | 任务队列 |
| `scripts/common/tasks.py` | 112 | 任务遍历/展示 |
| `scripts/common/task_store.py` | 666 | 任务 CRUD |
| `scripts/common/task_utils.py` | 274 | 任务工具函数 |
| `scripts/common/workflow_phase.py` | 215 | 工作流步骤提取 |
| `scripts/hooks/linear_sync.py` | 243 | Linear 同步 |

#### 嵌入新增脚本 (7,690 行) + 模板 (800 行)

| 文件路径 | 行数 | 类型 | 描述 |
|---|---|---|---|
| `scripts/workflow/workflow-state.py` | 2,734 | 核心状态机 | 强门禁状态管理中枢 |
| `scripts/workflow/patch-inject-workflow-state.py` | 828 | 补丁 | 修改 Python/JS 注入钩子 |
| `scripts/workflow/feasibility-check.py` | 627 | 验证 | 可行性评估模板/验证 |
| `scripts/workflow/plan-validate.py` | 608 | 验证 | 任务计划结构验证 |
| `scripts/workflow/ownership-proof-validate.py` | 568 | 验证 | 源水印/所有权验证 |
| `scripts/workflow/delivery-control-validate.py` | 554 | 验证 | 双轨交付控制验证 |
| `scripts/workflow/design-export.py` | 270 | 工具 | 设计文档脚手架/验证 |
| `scripts/workflow/source-watermark-guard.py` | 279 | 验证 | 水印保持性检查/修复 |
| `scripts/workflow/check-quality.py` | 160 | 工具 | 质量检查运行器 |
| `scripts/workflow/patch-task-status-view-strong-gate.py` | 233 | 补丁 | 修改3个文件的任务视图 |
| `scripts/workflow/patch-session-start-strong-gate.py` | 194 | 补丁 | 修改 session-start.py |
| `scripts/workflow/patch-workflow-phase.py` | 125 | 补丁 | 修改 workflow_phase.py |
| `scripts/workflow/patch-task-start-strong-gate.py` | 83 | 补丁 | 修改 task.py 状态翻转 |
| `scripts/workflow/patch-task-create-preserve-active.py` | 88 | 补丁 | 修改 task_store.py |
| `scripts/workflow/patch-workflow-phase-strong-gate.py` | 41 | 包装器 | 兼容性包装 |
| `templates/.../developer-facing-prd-template.md` | 383 | 模板 | 技术PRD模板 |
| `templates/.../customer-facing-prd-template.md` | 272 | 模板 | 业务PRD模板 |
| `templates/.../acceptance-criteria-template.md` | 145 | 模板 | 验收标准模板 |

#### 被修改的原生文件 (5 个)

| 文件路径 | 被哪些补丁修改 | 修改性质 |
|---|---|---|
| `scripts/task.py` | patch-task-start-strong-gate, patch-task-status-view-strong-gate | 移除状态翻转 + 更新CLI帮助文本/展示逻辑 |
| `scripts/common/tasks.py` | patch-task-status-view-strong-gate | 新增 _display_status / _workflow_state_summary 函数 |
| `scripts/common/task_queue.py` | patch-task-status-view-strong-gate | 改变 pending 任务列表逻辑 |
| `scripts/common/task_store.py` | patch-task-create-preserve-active | 新增 preserve-active 分支 |
| `scripts/common/workflow_phase.py` | patch-workflow-phase | 在 get_step() 中注入强门禁拦截 |

---

### 2. 脚本逐项分析

#### 2.1 workflow-state.py (2,734 行) — 侵入性: **高**

**与原生功能重叠:**
- 完全取代 `task.json` 的 `status` 字段权威性。原生 trellis 使用 `planning` / `in_progress` / `review` / `completed` 四态，此脚本定义了 9 阶段 (`feasibility`, `brainstorm`, `design`, `plan`, `implementation`, `check`, `review-gate`, `project-audit`, `delivery`) + 4 状态 (`in_progress`, `awaiting_user_confirmation`, `exit_ready`, `completed`) 的状态机。
- `cmd_route()` 替代了原生的 `task.py current` + `workflow_phase.py get_step()` 的组合路由功能。
- `resolve_active_task()`, `resolve_task_ref()`, `session_runtime_has_any_current_task()` 重复了 `common/active_task.py` 的核心逻辑。

**行为修改:**
- 此脚本是"唯一真相源"的执行者——所有补丁脚本都依赖它。它的存在改变了整个框架的语义模型：task.json.status 变成遗留字段。

**硬编码路径/常量:**
- `MIN_KICKOFF_PAYMENT_RATIO = 30.0` (line 25 in feasibility-check.py, line 25 in delivery-control-validate.py, 也硬编码在 workflow-state.py 的 validate_external_project_controls)
- `INSTALL_RECORD = ".trellis/workflow-installed.json"` (line 1781)
- `LIBRARY_LOCK = ".trellis/library-lock.yaml"` (line 1782)
- `REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"` (line 1783)
- 文件路径: `assessment.md`, `prd.md`, `check.md`, `task_plan.md`, `task_creation_checklist.md`, `finish-work-checklist.md`, `project-audit.md`, `context7-review.md` 全部硬编码
- 跨平台路径: `.claude/hooks/`, `.codex/hooks/`, `.opencode/plugins/`, `.agents/skills/` (line 1886-1930)
- `CUSTOMER_PRD = "docs/requirements/customer-facing-prd.md"`, `DEVELOPER_PRD = "docs/requirements/developer-facing-prd.md"` 硬编码

**错误处理:**
- `resolve_task_dir()` 抛出 `FileNotFoundError`，上层用 try/except 处理 ✓
- `read_json()` 静默返回 None（与原生 common/io.py 一致）✓
- `cmd_route()` 的 embed_invalid 路径正确返回 exit code 0 但 action=embed_invalid ✓
- `detect_embed_invalid()` 不抛异常，返回 string 或 None ✓
- **缺陷**: `validate_stage_transition_gates()` 在 stage not in STAGES 时不会拒绝（只有 canonical transition 校验），而是 fall through 到后续校验；如果 stage 非法但满足后续条件，可能产生虚假的 "通过" 判断。

**伪需求判断:**
- 外包项目付款门禁 (`kickoff_payment_ratio`, `kickoff_payment_received`) 是真实的业务需求，但对非外包项目（personal profile）完全无用，且校验逻辑遍布整个文件。
- `source_watermark_level` / `source_watermark_channels` / `zero_width_watermark_enabled` / `subtle_code_marker_enabled` / `ownership_proof_required` 这些水印/所有权字段在 personal profile 项目中不适用，但代码仍然要求它们存在（只是 `is_personal_brainstorm_bootstrap_allowed` 提供了部分豁免）。
- `context7_review_completed` 检查点——依赖外部服务 Context7，但校验逻辑硬编码为必须存在，对不使用 Context7 的项目构成伪需求。

---

#### 2.2 patch-inject-workflow-state.py (828 行) — 侵入性: **极高**

**与原生功能重叠:**
- 替换了原生 `inject-workflow-state.py` hook 的 `get_active_task()` 和 `build_breadcrumb()` 两个核心函数。
- 同时修改 Python (Claude) 和 JavaScript (OpenCode) 两个平台的钩子载体——这是唯一一个跨语言补丁。

**行为修改:**
- 原 `get_active_task()` 只读 `task.json.status`；补丁后优先调 `workflow-state.py route`。
- 原 `build_breadcrumb()` 只查 workflow.md 模板；补丁后增加 `extra_lines` 传递 route 产出的 blockers/warnings/reason。
- Python 载体用 `importlib.util` 在进程内加载 workflow-state.py 并缓存模块，JS 载体用 `execFileSync` 子进程调用。

**硬编码路径/常量:**
- `timeout=5000` (JS execFileSync, line 237) — 5秒超时对复杂项目的 route 计算可能不够
- `PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"` — 未验证 python3 可用性
- `_ACTION_BREADCRUMB_KEYS` (8个键) 硬编码了两份（Python + JS），必须手动保持同步

**错误处理:**
- Python `_load_route_data()` 的 try/except 捕获所有异常返回 `(None, f"{type(exc).__name__}: {exc}")` ✓
- JS carrier 的 catch 块设置 `status = "workflow-state.route_failed"` 并输出最后一行 ✓
- **缺陷**: Python in-process 模块缓存 (`_module_cache`) 没有失效机制——如果 `workflow-state.py` 被更新，缓存的旧模块仍会继续使用，路由结果可能过时。

**伪需求判断:**
- 此补丁解决的是真实问题（原生 breadcrumb 不反映强门禁状态），但实现方式（进程内导入外部脚本作为模块并缓存）引入了与原生 hook 生命周期不匹配的隐式状态。

---

#### 2.3 patch-session-start-strong-gate.py (194 行) — 侵入性: **高**

**与原生功能重叠:**
- 替换了 `_get_task_status()` 的整个 tail logic（从 `task_status = task_data.get(...)` 到函数结尾）。
- 原生逻辑按 `PLANNING` / `READY` / `COMPLETED` / 其他 路由；补丁后统一走 `workflow-state.py route`。

**行为修改:**
- 移除了 "If a task is READY, execute its Next required action without asking whether to continue" 的自动继续指令。
- 替换为 "Do NOT auto-continue across blockers or confirmation gates" 的显式阻止指令。

**硬编码路径/常量:**
- `timeout=10` (subprocess.run, line 67) — 10 秒超时
- 硬编码了两个脚本查找路径: `scripts/workflow/workflow-state.py` 和 `scripts/workflow-state.py`（向后兼容）

**错误处理:**
- PATCH_BLOCK 的 try/except 捕获所有异常后 fall back 到 `Status: ACTIVE` ✓
- **缺陷**: fall back 到 `ACTIVE` 是原生遗留语义，与强门禁模型矛盾——如果 route 因异常失败，会话启动可能在不该继续时继续。

**伪需求判断:**
- 移除 READY 自动继续是真实的——强门禁模型确实需要用户显式确认阶段切换。此补丁合理。

---

#### 2.4 patch-task-start-strong-gate.py (83 行) — 侵入性: **中**

**与原生功能重叠:**
- 移除了 `task.py cmd_start()` 中的 `planning → in_progress` 状态翻转。

**行为修改:**
- 原生 `cmd_start()` 在两个位置翻转状态（degraded mode + normal mode），补丁用 regex 匹配并替换为黄色警告打印。
- 状态翻转被完全移除——task.json.status 永远不更新为 in_progress。

**硬编码路径/常量:**
- 无额外路径

**错误处理:**
- regex 匹配失败时打印警告并返回 False ✓
- **风险**: 下游依赖 `task.json.status == "in_progress"` 的任何外部工具（CI、看板、统计）将永远看不到此状态，产生行为变化但无文档说明。

**伪需求判断:**
- 在强门禁模型下，task.json.status 确实不应是权威源——此修改逻辑自洽。但彻底移除状态翻转而非保持兼容性更新，属于激进决策。

---

#### 2.5 patch-task-status-view-strong-gate.py (233 行) — 侵入性: **高**

**与原生功能重叠:**
- 修改 3 个文件：`tasks.py`, `task_queue.py`, `task.py`。
- `tasks.py`: 新增 `_display_status()` 和 `_workflow_state_summary()` 函数，完全替代原生的 `data.get("status")` 读取。
- `task_queue.py`: 将 `list_tasks_by_status("planning")` 改为 `list_tasks_by_status(None)`，pending 视图从 "status=planning" 变为 "所有非归档任务"。
- `task.py`: 更新 `--status` 帮助文本，新增 `_workflow_display_extra` 显示。

**行为修改:**
- `task.py list` 的输出从 `(in_progress)` 变为 `(implementation)` 等阶段名。
- pending 队列语义变化：原来只有 planning 状态的任务算 pending，现在所有非归档任务都算。

**硬编码路径/常量:**
- `WORKFLOW_STATE_FILE_NAME = "workflow-state.json"` 硬编码
- `TERMINAL_TASK_STATUSES = {"completed", "done", "archived"}` — 新增 "done" 不在原生 task.py 的状态集中

**错误处理:**
- `_display_status()` 在 workflow-state.json 缺失时返回 `("repair_needed", "workflow-state.json missing")` ✓
- `read_json()` 失败时走 repair_needed 路径 ✓

**伪需求判断:**
- 改变 pending 语义是必要的——强门禁模型下 "planning" 不再存在，但改为 "所有非归档" 可能包含已在执行/审核中的任务，语义过宽。

---

#### 2.6 patch-workflow-phase.py (125 行) — 侵入性: **高**

**与原生功能重叠:**
- 在 `workflow_phase.py get_step()` 函数开头注入拦截逻辑。

**行为修改:**
- 当检测到强门禁阶段时，`get_step()` 返回空字符串并打印 stderr 警告，使旧版 `#### X.Y` 步骤查询完全失效。
- 拦截逻辑通过 subprocess 调用 `task.py current`，再检查 `workflow-state.json`——这意味着 `get_step()` 从纯文本解析函数变成了带 I/O 副作用的函数。

**硬编码路径/常量:**
- `_STRONG_GATE_STAGES` 9 个阶段硬编码在补丁字符串中
- `timeout=10` (subprocess.run, line 37)

**错误处理:**
- try/except 捕获所有异常后 pass（静默放行旧版查询）✓
- **缺陷**: 此补丁在 `get_step()` 内调用 `task.py current` 子进程。如果 `task.py` 内部也依赖 `workflow_phase.py`（例如某个 hook 间接调用），可能产生循环依赖。实际上原生 `task.py` 不直接调用 `workflow_phase.py`，但 `get_context.py` 通过 `common/git_context.py` 间接调用 `workflow_phase.py`，而 `cmd_route()` 内部不调用 `get_context.py`，因此当前不存在循环。但这种脆弱的依赖关系容易在未来被打破。

**伪需求判断:**
- 在强门禁模式下禁用旧步骤查询是自洽的，但通过子进程调用来检测是否处于强门禁模式，是一个过度工程化的做法。更简单的方案：检查 `workflow-state.json` 文件是否存在即可。

---

#### 2.7 patch-task-create-preserve-active.py (88 行) — 侵入性: **低**

**与原生功能重叠:**
- 在 `task_store.py cmd_create()` 的 auto-activate 分支前插入条件判断。

**行为修改:**
- 当 `TRELLIS_PRESERVE_ACTIVE_TASK=1` 且 `--parent` 被使用时，跳过自动激活。

**硬编码路径/常量:**
- `TRELLIS_PRESERVE_ACTIVE_TASK` 环境变量名硬编码

**错误处理:**
- `__import__("os")` 直接在补丁字符串中使用——不优雅但功能正确

**伪需求判断:**
- 此补丁解决的是真实问题：创建子任务时不应切换活动任务离开父任务。设计合理且侵入性低。

---

#### 2.8 feasibility-check.py (627 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 没有可行性评估功能。

**行为修改:**
- 纯增量——生成模板、验证 assessment.md 字段。

**硬编码路径/常量:**
- `MIN_KICKOFF_PAYMENT_RATIO = 30.0` 硬编码
- `VALID_ENGAGEMENT_TYPES`, `VALID_EXTERNAL_TRACKS`, `VALID_SOURCE_WATERMARK_LEVELS` 硬编码
- ASSESSMENT_TEMPLATE 约 230 行硬编码在 Python 字符串中

**错误处理:**
- `--step validate` 在 assessment.md 不存在时正确报告 ✓

**伪需求判断:**
- 合规清单、评估模板生成对特定业务场景（外包项目）是真实的。但 ASSESSMENT_TEMPLATE 包含大量外包/付款/水印字段，对 personal profile 项目是伪需求噪声。
- `--step risk-analysis` 依赖 `demand-risk-assessment` skill——如果该 skill 未安装，功能无意义但不会崩溃（只是跳过）。

---

#### 2.9 delivery-control-validate.py (554 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 无交付控制功能。

**行为修改:**
- 纯增量——验证 assessment.md / task_plan.md / delivery/ 中的双轨字段。

**硬编码路径/常量:**
- `MIN_KICKOFF_PAYMENT_RATIO = 30.0` (重复定义)
- `VALID_ENGAGEMENT_TYPES`, `VALID_EXTERNAL_TRACKS` (重复定义)
- `trial_authorization_terms.*` 5 个子字段名硬编码

**错误处理:**
- `_find_assessment_in_lineage()` 有循环检测 (visited set) ✓

**伪需求判断:**
- 对外包项目真实需求；对非外包项目提前返回（`engagement_type != "external_outsourcing"` 时跳过）✓
- **但**: 此脚本被 `workflow-state.py` 的 `validate_plan_gate()` 和 `validate_delivery_gate()` 通过 `run_gate_validator()` 调用——如果脚本不存在，只报告"缺少脚本"而不阻塞，这是合理的降级。

---

#### 2.10 ownership-proof-validate.py (568 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 无所有权验证功能。

**行为修改:**
- 纯增量——验证水印级别/通道/所有权证明产物。

**硬编码路径/常量:**
- `VALID_LEVELS = {"none", "basic", "hybrid", "forensic"}` 硬编码
- `WMID_PATTERN = re.compile(r"\bwm_[A-Za-z0-9_-]{4,}\b")` 硬编码
- `_find_assessment_in_lineage()` 重复定义（与 delivery-control-validate.py 相同）

**错误处理:**
- lineage 遍历有 visited set ✓

**伪需求判断:**
- 对 `ownership_proof_required = yes` 的外包项目是真实需求。
- 对 `source_watermark_level = none` 的项目提前跳过 ✓
- **但**: 对 personal profile 项目，assessment.md 可能不存在 `_find_assessment_in_lineage()` 返回不存在路径，脚本会报告"缺少文件"但不崩溃。

---

#### 2.11 plan-validate.py (608 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 无计划结构验证。

**行为修改:**
- 纯增量——验证 `task_plan.md` 的 12 个必填章节、任务卡片字段、粒度字段等。

**硬编码路径/常量:**
- 12 个 `REQUIRED_SECTIONS` 硬编码
- `TASK_CARD_MARKERS` 8 个字段名硬编码
- `GRANULARITY_FIELDS`, `EARLY_PROBE_FIELDS`, `AUTOMATION_FIELDS`, `SCOPE_FIELDS`, `EXIT_SNAPSHOT_FIELDS` 各若干字段硬编码
- `LEGACY_MARKERS` 6 个旧版标记硬编码

**错误处理:**
- 文件不存在时明确报告 ✓

**伪需求判断:**
- 对严格计划驱动的外包项目合理；对轻量 personal 项目过度。
- `LEAF_PRD_REQUIRED_SECTIONS` 包含 `Preferred CLI / 推荐主执行 CLI` 字段——这是工作流特定概念，与原生 trellis 无关。
- `PROJECT_AUDIT_ORDER_MARKERS` ("不得早于", "不早于") 是中文硬编码的正则模式。

---

#### 2.12 design-export.py (270 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 无设计文档脚手架。

**行为修改:**
- 纯增量——脚手架和验证 design/ 目录文档。

**硬编码路径/常量:**
- `REQUIRED_FILES = ["index.md", "TAD.md", "ODD-dev.md", "ODD-user.md"]` 硬编码
- `SCAFFOLD_FILES` 8 个文件名硬编码
- `STITCH_PROMPT_BASELINE_TERMS` 包含 9 条 UI 设计偏好（"不要通用 SaaS 模板感" 等）——这是设计偏好而非结构契约

**错误处理:**
- 文件存在时 `--scaffold` 跳过不覆盖 ✓

**伪需求判断:**
- `STITCH_PROMPT_BASELINE_TERMS` 中的 UI 审美偏好（如"不要廉价渐变和无意义炫光装饰"）不应出现在验证脚本中——这是设计指导而非结构验证。
- 对没有 UI 设计需求的项目，AID.md/STITCH-PROMPT.md 是伪需求。

---

#### 2.13 source-watermark-guard.py (279 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。

**行为修改:**
- 纯增量——验证/修复受保护水印片段。

**硬编码路径/常量:**
- `PROTECTED_SOURCES = ("design/source-watermark-plan.md", "source-watermark-plan.md")` 硬编码

**错误处理:**
- `--mode check` 只检测不修改 ✓
- `--mode repair` 有修复逻辑，修复失败时报告 ✓

**伪需求判断:**
- 对 `source_watermark_level != "none"` 的项目是真实需求。
- repair 模式的存在表明设计者预期水印可能被意外删除——但这也暗示对源代码有修改行为，需要谨慎授权。

---

#### 2.14 check-quality.py (160 行) — 侵入性: **低（独立工具）**

**与原生功能重叠:**
- 无直接重叠。原生 trellis 无质量检查运行器。

**行为修改:**
- 纯增量——运行用户确认的测试/lint/类型检查命令。

**硬编码路径/常量:**
- 无硬编码路径

**错误处理:**
- 命令不存在时报告 "not configured" ✓
- git status dirty 时报告 ✓

**伪需求判断:**
- 通用工具，无伪需求。设计简洁。

---

### 3. 模板逐项分析

#### 3.1 developer-facing-prd-template.md (383 行) — 过度复杂

**与原生一致性:**
- 原生 trellis 无模板系统，此模板完全独立。
- 不引用 workflow.md 中的任何阶段定义。

**引用不存在字段:**
- 引用 `spec.universal-domains.product-and-requirements.developer-facing-prd` 路径记法——这是 Trellis spec 层路径，但模板本身不保证 spec 层存在。
- JSON Schema 示例 (`"$schema"`, `"additionalProperties"`) 对 Markdown PRD 而言过于形式化。

**过度复杂:**
- 14 个必填章节，部分章节嵌套 3 层以上。
- "Data/State Model" 章节要求 Mermaid ER 图——这是架构文档的职责，不应强制在 PRD 中出现。
- "Error Handling" 章节要求完整错误矩阵——对早期阶段 PRD 过度。
- 整体 383 行的模板长度对于"模板"而言过重；更像是一份完整的架构设计规范。

---

#### 3.2 customer-facing-prd-template.md (272 行) — 中度复杂

**与原生一致性:**
- 独立模板，不依赖原生。
- 结构与 workflow.md 的 feasibility/design 阶段产物对应。

**引用不存在字段:**
- 无无效引用。

**过度复杂:**
- 11 个章节对业务 PRD 而言偏多，但可接受。
- "Timeline" 和 "Dependencies" 章节对早期 feasibility 阶段可能无法填写。
- 整体合理，但部分章节可合并。

---

#### 3.3 acceptance-criteria-template.md (145 行) — 合理

**与原生一致性:**
- 独立模板，结构清晰。
- 引用 PRD specs 和 checklists——这些是 workflow 产物，存在合理。

**引用不存在字段:**
- 无无效引用。

**过度复杂:**
- 6 个章节，结构简洁，合理。

---

### 4. 总体判断

#### 4.1 补充性 vs 侵入性

| 类别 | 补充性 | 侵入性 | 说明 |
|---|---|---|---|
| workflow-state.py | 部分 | **高** | 新增权威状态机但完全取代原生 task.json.status 语义 |
| 6 个 patch-* 脚本 | 无 | **极高** | 运行时修改原生脚本源代码，不可逆（除非手动回退） |
| 5 个验证脚本 | **高** | 低 | 纯增量工具，无原生功能重叠 |
| check-quality.py | **高** | 低 | 通用工具，设计简洁 |
| 3 个模板 | **高** | 低 | 纯增量模板，原生无模板 |

**总体定性**: 半补充半侵入。工具类脚本和模板是补充性的；patch 类脚本和 workflow-state.py 是侵入性的。侵入性部分的代码量占嵌入脚本总量的 56%（4,405/7,690 行），且影响 5 个原生文件。

#### 4.2 伪需求问题

| 伪需求 | 出现位置 | 影响 |
|---|---|---|
| 外包付款门禁 (kickoff_payment_ratio/received) 对 personal profile | workflow-state.py, feasibility-check.py, delivery-control-validate.py | 对非外包项目产生无效校验步骤；虽有 `engagement_type != "external_outsourcing"` 提前返回，但代码路径仍被执行 |
| 源水印/所有权证明对 level=none 项目 | workflow-state.py, ownership-proof-validate.py | `validate_ownership_policy_controls()` 对 `level=none` 仍要求字段存在但值可为 no；这是最低侵入但仍增加了不必要字段 |
| Context7 review 检查点 | workflow-state.py line 1470-1523 | `context7_review_completed` 对不使用 Context7 的项目是硬性伪需求；personal profile 无法自然满足此检查点 |
| STITCH_PROMPT UI 审美偏好 | design-export.py line 37-49 | 将主观设计偏好嵌入验证脚本，对非 UI 项目完全无意义 |
| developer-facing-prd 的 14 章节强制 | developer-facing-prd-template.md | 对简单项目过度，但模板本身是建议性的，影响有限 |

#### 4.3 与原生能力的冗余

| 冗余 | 原生 | 嵌入 | 说明 |
|---|---|---|---|
| 任务状态管理 | task.json status (4态) | workflow-state.json stage+status (9+4态) | 完全取代，非冗余而是替代 |
| 任务列表展示 | tasks.py iter_active_tasks | patch-task-status-view _display_status | 补丁注入后原生展示逻辑变不可达代码 |
| 工作流步骤路由 | workflow_phase.py get_step | workflow-state.py cmd_route + patch | 补丁使 get_step 返回空字符串，原生路由变死代码 |
| 活动任务解析 | active_task.py resolve_active_task | workflow-state.py 内部重复调用 | 冗余：workflow-state.py 重新 import 并调用，未提取共享逻辑 |

#### 4.4 代码重复

- `_find_assessment_in_lineage()` 在 delivery-control-validate.py 和 ownership-proof-validate.py 中完全相同（约 30 行）。
- `extract_backticked_field()` 在 feasibility-check.py, delivery-control-validate.py, ownership-proof-validate.py, workflow-state.py 中各有独立定义（实现略有差异）。
- `PLACEHOLDER_MARKERS` 在 4 个文件中重复定义。
- `MIN_KICKOFF_PAYMENT_RATIO = 30.0` 在 3 个文件中硬编码。
- `VALID_ENGAGEMENT_TYPES` 在 3 个文件中重复定义。

---

### 5. 关键风险

1. **补丁不可逆**: 6 个 patch 脚本直接修改原生文件源代码，没有回退机制（没有 unpatch 命令）。一旦补丁应用，原生脚本不再可独立运行。

2. **模块缓存过时**: patch-inject-workflow-state.py 的 Python in-process 模块缓存 (`_module_cache`) 在 workflow-state.py 更新后不会失效，可能导致路由结果与实际状态不一致。

3. **循环依赖风险**: patch-workflow-phase.py 在 `get_step()` 内调用 `task.py current` 子进程；虽然当前不构成循环，但依赖链脆弱。

4. **JS 超时过短**: patch-inject-workflow-state.py 的 JS 载体用 `timeout=5000` 调用 `workflow-state.py route`；对复杂项目（外包项目多层校验），5 秒可能不够。

5. **fallback 语义矛盾**: patch-session-start-strong-gate.py 在 route 失败时 fallback 到 `Status: ACTIVE`，这与强门禁模型"不允许自动继续"的设计矛盾。

6. **pending 语义过宽**: patch-task-status-view-strong-gate.py 将 pending 改为"所有非归档任务"，导致 `task.py list --status planning` 失效但无替代查询。

7. **task.json.status 永远不更新**: patch-task-start-strong-gate.py 移除了所有状态翻转，依赖 task.json.status 的外部工具（CI/看板）将看不到任何进度更新。

## Caveats / Not Found

- 原生模板目录不存在——嵌入模板是纯增量，无需对比。
- `patch-inject-workflow-state.py` 的完整 diff 逻辑（baseline fixture patch 部分）因文件过长未完全逐行分析，但已阅读关键替换块。
- 工作流源目录 (`docs/workflows/新项目开发工作流/scripts/` 和 `templates/`) 为空——可能文件已被移动或路径有误，无法对比源文件与嵌入版本的差异。

# Research: 工作流修复点二次审计

- **Query**: 对临时项目 /tmp/trellis-0.5.9-2 的已安装工作流做完整复查，重点关注上次审计标记为"部分满足"的 #14 和 #20
- **Scope**: mixed (internal code + external docs)
- **Date**: 2026-05-09

## Findings

### 修复点 1: 前置校验: Git + 多 remote + 参考命令

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `install-workflow.py` | L8, L20, L112, L113 | 文档声明 + 常量定义: `_ORIGIN_REMOTE_NAME = "origin"`, `_MIN_ORIGIN_PUSH_URLS = 2` |
| `install-workflow.py` | L550-580 `count_origin_push_urls()` | 完整解析 `.git/config` 中 `[remote "origin"]` 块的 `pushurl` 数量 |
| `install-workflow.py` | L631-653 `ensure_project_prereqs()` | 依次校验: `.git` 存在 -> `.trellis/` 存在 -> `.trellis/.version` 存在 -> origin push URL >= 2 |
| `install-workflow.py` | L647-650 | 失败时输出完整参考命令: `git remote add origin`, `git remote set-url --add --push origin` 两条 |

安装后产物验证:
- `workflow-installed.json` 存在且包含 `trellis_version: "0.5.9"`，说明 `ensure_project_prereqs` 全部通过后才写入了安装记录

**缺口描述**: 无

**与上次对比变化**: 无变化，维持已满足状态

---

### 修复点 2: 初始阶段 spec 通过脚本导入

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `install-workflow.py` | L110, L1344-1378 `import_requirements_foundation()` | 调用 `trellis-library/cli.py assemble --pack pack.requirements-discovery-foundation --auto` |
| `install-workflow.py` | L1647-1656 | 在主流程中调用 `import_requirements_foundation`，失败则 fail embed |
| `workflow-installed.json` | `initial_pack: "pack.requirements-discovery-foundation"` | 安装记录确认初始包名 |
| `/tmp/.../library-lock.yaml` | 文件存在 (22615 bytes) | 实际导入产物存在 |
| `/tmp/.../spec/universal-domains/` | 目录存在 | 通用域 spec 资产已落盘 |

**缺口描述**: 无

**与上次对比变化**: 无变化，维持已满足状态

---

### 修复点 3: bootstrap 删除 + pnpm 校验删除

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `install-workflow.py` | L111, L1473-1498 `remove_bootstrap_task()` | 删除 `.trellis/tasks/00-bootstrap-guidelines` |
| `install-workflow.py` | L611-628 `clear_bootstrap_current_task_if_needed()` | 若 `.current-task` 仍指向 bootstrap task，则清空该引用 |
| `workflow-installed.json` | `bootstrap_task_removed: true, bootstrap_cleanup_status: "removed"` | 安装记录确认已删除 |
| `/tmp/.../tasks/` | 目录为空 (仅含 `.` 和 `..`) | bootstrap task 已实际删除 |
| `/tmp/.../current-task` | 文件不存在 | 无悬空 `.current-task` 引用 |

pnpm 校验删除:
| 文件路径 | 说明 |
|---|---|
| `/tmp/.../finish-work.md` | grep 搜索 "pnpm" 返回 NO_PNPM_FOUND |
| `/tmp/.../finish-work.md` L73-100 | Code Quality 区块已被项目化补丁替换，明确写着"不要继续沿用 Trellis 基线里的默认包管理器占位命令"，且要求填写"当前项目在 design 阶段已经明确的真实自动化检查矩阵" |

**缺口描述**: 无

**与上次对比变化**: 无变化，维持已满足状态

---

### 修复点 6: main 分支校验 + 真实/替代门禁

**是否满足**: ✅ 已满足

**证据**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `install-workflow.py` | L114 `_PRIMARY_BRANCH_NAME = "main"` | 常量定义 |
| `install-workflow.py` | L427-519 `resolve_git_dir()`, `read_head_reference()`, `resolve_head_branch()`, `git_ref_exists()`, `has_local_commit_history()` | 完整 Git 元数据解析链: 兼容 `.git` 目录和 gitdir 文件，读 HEAD 引用，解析 packed-refs |
| `install-workflow.py` | L522-547 `enforce_initial_main_branch_policy()` | 新项目硬阻断 (sys.exit)；已有历史项目仅 warn |
| `install-workflow.py` | L652 | `ensure_project_prereqs()` 最后调用 `enforce_initial_main_branch_policy(root)` |

替代门禁 (已有历史项目):
- `has_local_commit_history()` 通过 HEAD 引用 + packed-refs 判断是否有本地提交
- 有历史时仅输出 `warn()` 提醒，不强制 `sys.exit`

**缺口描述**: 无

**与上次对比变化**: 无变化，维持已满足状态

---

### 修复点 14: feasibility 不可跳过性

**是否满足**: 📈 较上次显著改善，但仍有残留缺口

**证据 - 脚本级硬门禁 (新增)**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `workflow-state.py` | L29 `ASSESSMENT_FILE = Path("assessment.md")` | 常量定义 |
| `workflow-state.py` | L356-372 `collect_route_readiness_blockers()` brainstorm 分支 | `assessment_file` 不存在时追加 blocker "缺少 assessment.md；必须先完成 feasibility 才允许继续 brainstorm"；`是否允许进入 brainstorm` 字段缺失或不为"是"时也追加 blocker |
| `workflow-state.py` | L543-548 `validate_external_project_controls()` | 非 feasibility 阶段缺少 `assessment.md` 时追加 error "缺少 assessment.md；任何项目都必须先经过 feasibility 并完成项目类别判断" |
| `workflow-state.py` | L633-706 `validate_ownership_policy_controls()` | 非 feasibility 阶段校验 `source_watermark_*` / `ownership_proof_required` 字段完整性 |
| `workflow-state.py` | L876-879 `cmd_validate()` | 校验链包含 `validate_external_project_controls` + `validate_ownership_policy_controls` |
| `workflow-state.py` | L986-987 `cmd_route()` | 无 `assessment.md` 时路由到 `first_entry` → feasibility |
| `feasibility-check.py` | L239-463 `step_validate()` | 完整的 assessment.md 字段校验脚本，双轨字段全覆盖 |
| `feasibility.md` | L11-12 "Gate Rule" | 文档声明: feasibility 是进入 brainstorm 前的强制前置门禁 |

**证据 - 命令级前置校验 (新增)**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `brainstorm.md` | L80-96 "Gate 0: Assessment Gate (ALWAYS)" | brainstorm 入口先确认 feasibility 已完成且 assessment.md 仍有效 |
| `brainstorm.md` | L86-89 门禁校验代码块 | `python3 .trellis/scripts/workflow/workflow-state.py validate <task-dir>` |
| `brainstorm.md` | L96 | "若不满足以上任一条件，停止当前 brainstorm，先回 /trellis:feasibility 重新评估" |
| `continue.md` | L88-89 | `action = first_entry` 时路由到 `/trellis:feasibility` |
| `continue.md` | L91 | `action = resume_with_assessment` 时路由到 `/trellis:brainstorm` (需有效 assessment) |

**残留缺口**:

1. **feasibility 阶段自身的 assessment.md 内容完整性硬校验未被 `workflow-state.py validate` 覆盖**:
   - `validate_external_project_controls()` 在 `stage == "feasibility"` 时直接 `return` (L543-544)，跳过所有 assessment 字段检查
   - `validate_ownership_policy_controls()` 同理在 `stage == "feasibility"` 时直接 `return` (L640-641)
   - 这意味着: 在 feasibility 阶段内部，`workflow-state.py validate` 不会校验 assessment.md 是否已填写完整
   - feasibility 阶段的 assessment 完整性校验仍依赖 `feasibility-check.py --step validate` 的单独调用，而非 `workflow-state.py validate` 的统一门禁链

2. **brainstorm.md 的 Gate 0 是文档级约束 + 脚本辅助，不是不可绕过的硬阻断**:
   - brainstorm.md 告诉 AI "先确认 feasibility 已完成"，但 AI 可以选择不执行 `workflow-state.py validate` 而直接开始 brainstorm
   - `workflow-state.py validate` 只在 AI 主动调用时才生效；如果 AI 跳过调用，assessment 缺失不会被自动检测
   - 对比: `workflow-state.py route` 命令的 `cmd_route()` 确实会在无 assessment 时强制路由到 feasibility (L986-987)，但这仅在走 `/trellis:continue` 入口时生效

3. **无独立自动化 hook 拦截**:
   - 没有 `PreToolUse` 或 `UserPromptSubmit` hook 在进入 brainstorm 前自动校验 assessment 存在性
   - 当前 `.claude/settings.json` 的 hooks 仅包含 `SessionStart` + `PreToolUse(Task/Agent)` + `UserPromptSubmit(inject-workflow-state.py)`
   - `inject-workflow-state.py` 只注入 breadcrumb，不执行阶段门禁检查

**与上次对比变化**:
- 上次: "仅文档级约束（brainstorm.md 的 Gate Rule），缺脚本硬门禁自动检测 assessment.md"
- 本次: `workflow-state.py` 的 `cmd_validate()` 和 `cmd_route()` 已增加 assessment.md 存在性和字段完整性校验；brainstorm.md 增加了 Gate 0 和门禁校验代码块；`feasibility-check.py --step validate` 提供了独立字段完整性校验
- 改善幅度: 从纯文档约束升级到"脚本可校验 + 命令级路由硬门禁 + 独立校验脚本"，但仍存在 feasibility 阶段内部 validate 避开和 AI 绕过调用两个缺口

---

### 修复点 20: .current-task 空 + 无双 remote 提示

**是否满足**: 📈 较上次改善，语义更清晰

**证据 - .current-task 空的处理**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `workflow-state.py` | L293-307 `validate_current_task_pointer()` | `.current-task` 不存在时追加 error；为空时追加 error "不能为空，必须明确当前执行任务" |
| `workflow-state.py` | L976-1012 `cmd_route()` | 无 `.current-task` 时扫描 `assessment.md` 决定路由: 有 assessment 允许进入 brainstorm；无 assessment 路由到 feasibility；都无则 `recovery_needed` |
| `阶段状态机与强门禁协议.md` | L36-41 `.current-task` 约束 | "不能为空" / "不允许识别当前阶段" / "只能进入恢复当前任务 / 明确当前任务分支" |
| `continue.md` | L84-85 | `route` 命令: 无 task-dir 时可省略，自动检测 |
| `task.py` | L95-109 `cmd_start()` | 无 session identity 时 degraded mode 仍翻转 status，但 active-task pointer 不持久化 |

**证据 - 无双 remote 提示**:

| 文件路径 | 行号/关键字 | 说明 |
|---|---|---|
| `install-workflow.py` | L643-650 | origin push URL < 2 时 `sys.exit` 硬阻断，输出完整修复命令 |
| `install-workflow.py` | L8, L20 | 文档注释明确声明 "origin 至少有两个 push URL" |

**语义差异分析**:

`.current-task` 为空时:
- **workflow-state.py validate**: 硬阻断 (追加 error，返回 exit code 1)
- **workflow-state.py route**: 软路由 (扫描 assessment.md 后给出路由建议，但 `recovery_needed` 时 action 不是 `blocked` 而是 `recovery_needed`，意味着 continue 命令会停在"要求用户明确当前任务"而不是阻断)
- **阶段状态机文档**: 硬阻断语义 ("不允许识别当前阶段"、"不允许自动重入")
- **task.py start**: degraded mode (黄色警告但仍然执行 status 翻转)

存在三级语义梯度:
1. `validate` 子命令: 硬阻断 (返回 1)
2. `route` 子命令: 软恢复 (`recovery_needed` action)
3. `task.py start`: degraded mode (允许继续但提示)

`route` 的 `recovery_needed` 不是 `blocked`，但 continue.md 的 Phase Router 表中 `recovery_needed` 对应"要求用户明确当前任务"（L96），实际上也阻止了自动推进。从用户视角看，效果等同于阻断，但语义标签不同。

**与上次对比变化**:
- 上次: "实测通过但有语义差异（硬阻断 vs 软提示）"
- 本次: `workflow-state.py` 的 `validate` 和 `route` 子命令对 `.current-task` 为空的处理已更加完整；`route` 用 `recovery_needed` action 代替了 `blocked`，但 continue.md 正确处理了这两种 action 的路由差异；语义差异仍然存在（validate 硬阻断 vs route 软恢复 vs task.py degraded mode），但三者从不同角度保证安全，不会导致静默跳过

---

## 汇总表

| # | 修复点标题 | 是否满足 | 与上次对比 |
|---|---|---|---|
| 1 | 前置校验: Git + 多 remote + 参考命令 | ✅ 已满足 | 无变化 |
| 2 | 初始阶段 spec 通过脚本导入 | ✅ 已满足 | 无变化 |
| 3 | bootstrap 删除 + pnpm 校验删除 | ✅ 已满足 | 无变化 |
| 6 | main 分支校验 + 真实/替代门禁 | ✅ 已满足 | 无变化 |
| 14 | feasibility 不可跳过性 | 📈 较上次显著改善 | 从纯文档约束升级到脚本+路由+独立校验，但 feasibility 阶段内部 validate 避开和 AI 绕过调用仍有缺口 |
| 20 | .current-task 空 + 无双 remote 提示 | 📈 较上次改善 | 语义差异仍存在（validate 硬阻断 / route 软恢复 / task.py degraded mode），但三者从不同角度保证安全 |

## 关键文件清单

| 文件路径 | 描述 |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | 安装后 workflow 主文档，含 workflow-state breadcrumb 和项目化补丁 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow-installed.json` | 安装记录 JSON |
| `/tmp/trellis-0.5.9-2/.trellis/library-lock.yaml` | requirements-discovery-foundation 导入产物 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/brainstorm.md` | brainstorm 命令，含 Gate 0 Assessment Gate |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/feasibility.md` | feasibility 命令，含 Gate Rule 和 Step 0/0.5 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/continue.md` | continue 命令，含 Phase Router 和 route 集成 |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/finish-work.md` | finish-work 命令，含项目化补丁 |
| `/tmp/trellis-0.5.9-2/.claude/settings.json` | hooks 配置 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/feasibility-check.py` | assessment.md 字段完整性校验脚本 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/workflow-state.py` | 阶段状态机 helper，含 validate/route/repair 子命令 |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/task.py` | 任务管理脚本 |
| `/ops/.../commands/install-workflow.py` | 安装器源码 |
| `/ops/.../commands/workflow_assets.py` | 资产定义模块 |
| `/ops/.../阶段状态机与强门禁协议.md` | 阶段状态机协议文档 |

## Caveats / Not Found

1. **#14 残留缺口**: `workflow-state.py validate` 在 `stage == "feasibility"` 时跳过 assessment 字段检查 (L543-544, L640-641)，导致 feasibility 阶段内部的 assessment 完整性仍需依赖单独调用 `feasibility-check.py --step validate`，而非 `workflow-state.py validate` 的统一门禁链
2. **#14 AI 绕过风险**: brainstorm.md 的 Gate 0 要求 AI 主动调用 `workflow-state.py validate`，但没有 hook 级别的自动拦截机制，AI 理论上可以跳过校验直接开始 brainstorm
3. **#20 语义梯度**: `.current-task` 为空时，`validate`(硬阻断) / `route`(软恢复) / `task.py start`(degraded mode) 三者的语义不一致，但不会导致静默跳过

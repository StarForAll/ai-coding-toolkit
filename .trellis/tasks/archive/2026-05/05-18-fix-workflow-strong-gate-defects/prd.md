# 修复新项目开发工作流 strong-gate 结构性缺陷

## 背景

新项目开发工作流已迁移到 strong-gate 模型（`workflow-state.json` + `workflow-state.py route/set`），但多处代码和文档仍残留旧的三阶段模型（planning/in_progress/completed），导致嵌入后的目标项目运行时出现路由错误、死路径、双源真相等问题。

## 修复范围

源文件位于 `docs/workflows/新项目开发工作流/commands/`，修复后由 `install-workflow.py` 安装到目标项目。

### P1 — 阻断性问题

1. **Codex trellis-start SKILL.md 死路径**
   - 嵌入后目标文件：`.agents/skills/trellis-start/SKILL.md`
   - 问题：Step 4 引用 `Phase 2.1`，但 workflow.md 无 `#### 2.1` 步骤；`get_context.py --mode phase --step 2.1` 会报错退出
   - 修复：确保 installer 用 `start-skill-patch-phase-router.md` 完整替换旧 Steps 1-4，不留残余

2. **task.py start 双源真相**
   - 嵌入后目标文件：`.trellis/scripts/task.py`
   - 问题：`cmd_start()` 将 `task.json.status` 从 planning→in_progress，与 workflow-state.json 声明的单一真相源冲突
   - 修复：在工作流 patch 中新增一个 patch 脚本，修改 `cmd_start()` 不再翻转 status，而是调用 `workflow-state.py set` 或直接跳过 status 翻转

3. **Claude session-start.py 旧路由**
   - 嵌入后目标文件：`.claude/hooks/session-start.py`
   - 问题：`_get_task_status()` 使用旧 PLANNING/READY 逻辑和 Phase 2.1 引用
   - 修复：更新 `patch-session-start-strong-gate.py` 使其完整替换 `_get_task_status()` 为 strong-gate 版本

### P2 — 功能性问题

4. **delivery.md 混入 archive 步骤**
   - 源文件：`commands/delivery.md`
   - 问题：Step 10 "收尾记录校验" 包含 archive + add_session 命令，与 record-session 职责重叠
   - 修复：删除 delivery Step 10 中的 archive 和 add_session 命令，改为引用 record-session

5. **OpenCode session-utils.js 旧面包屑标记**
   - 嵌入后目标文件：`.opencode/lib/session-utils.js`
   - 问题：line 236 用 `"## Workflow State Breadcrumbs"` 匹配，但当前 workflow.md 用 `"## Strong-Gate Breadcrumb Blocks"`
   - 修复：确认 install-workflow.py 的 patch 逻辑正确替换该字符串；若已有正确逻辑则验证即可

6. **patch 脚本 CLI 参数过时**
   - 源文件：`commands/shell/patch-session-start-strong-gate.py`
   - 问题：line 44 用 `--task-dir` flag，line 71 用 `advance --stage`，但当前 workflow-state.py 用位置参数和 `set --stage`
   - 修复：更新 patch 脚本中的 CLI 调用匹配当前 workflow-state.py 接口

7. **patch-workflow-phase.py 扫描全部 task**
   - 源文件：`commands/shell/patch-workflow-phase.py`
   - 问题：遍历 `.trellis/tasks/` 下所有目录找 workflow-state.json，应只检查 active task
   - 修复：改为通过 `task.py current` 获取 active task 后只检查该 task

### P3 — 一致性问题

8. **workflow-state.py 不区分 profile 路由**
   - 源文件：`commands/shell/workflow-state.py`
   - 问题：`cmd_route` 对 first_entry 始终路由到 feasibility，profile_hint 只做提示不影响路由
   - 修复：在 cmd_route 中实现 profile-aware 路由：personal profile + first_entry 跳过 feasibility 直接到 design/plan

9. **trellis-meta 参考文档过时**
   - 源文件由 install-workflow.py 生成/复制到目标项目
   - 问题：`local-architecture/workflow.md` 仍教旧三阶段模型；`task-system.md` 无 workflow-state.json 引用；`context-injection.md` 用旧状态名
   - 修复：更新 install-workflow.py 中相关文档生成逻辑，或在工作流 commands/ 下新增参考文档覆盖源

## 约束

- 修复目标：`docs/workflows/新项目开发工作流/` 下的源文件
- 不直接修改 `/tmp/trellis-0.5.16-2/` 下的嵌入文件
- 若修复需 patch trellis 原生文件（如 task.py），在 workflow 的 shell/ 下新增或更新 patch 脚本
- 保持与 install-workflow.py 安装流程的兼容性

# PRD: 工作流升级兼容性修改深度分析（第三轮 — 最终）

## Goal

基于最新文件内容，最终确认升级兼容性修改的完整性。

## 测试状态

```
test_workflow_phase_contracts.py:       5/5  OK
test_runtime_active_task_convergence.py: 12/12 OK
test_template_hash_semantics.py:        2/2  OK
Total: 19/19 PASS
```

---

## 变更清单（11 个文件，+210 / -13）

| 文件 | 变更内容 |
|---|---|
| `active_task.py` | degraded fallback 解析、写入、清理、交叉清理 |
| `task.py` | `cmd_start` degraded fallback 写入 + 替换警告 |
| `statusline.py` | stale 可见性、degraded 标识、source 字段 |
| `inject-workflow-state.py` (×4) | breadcrumb `· degraded` display status |
| `inject-workflow-state.js` | breadcrumb `· degraded` display status |
| `trellis-context.js` | `_resolveDegradedActiveTask` + `getActiveTask` 集成 |
| `workflow.md` | degraded fallback 行为文档更新 |
| `test_workflow_phase_contracts.py` | 新增 degraded header 测试 |
| `test_runtime_active_task_convergence.py` | 环境隔离修复 + degraded 测试 |
| `test_template_hash_semantics.py` | 哈希分类更新 |

---

## 逐项验证

### A. 跨平台解析一致性

| 步骤 | Python | JS (OpenCode) | 一致性 |
|---|---|---|---|
| 1 | context key → session | context key → session | ✅ |
| 2 | single-session fallback | single-session fallback | ✅ |
| 3 | degraded (if no key) | degraded (if no key) | ✅ |
| 4 | return None | return null | ✅ |

### B. degraded 可见性

| 表面 | 表现 | 验证 |
|---|---|---|
| Claude statusline | `· degraded` 后缀 | ✅ `_render_task_line` |
| Claude breadcrumb | `in_progress · degraded` | ✅ `build_breadcrumb` + 测试 |
| Codex breadcrumb | 同 Claude | ✅ 相同代码 |
| Qoder breadcrumb | 同 Claude | ✅ 相同代码 |
| OpenCode breadcrumb | `in_progress · degraded` | ✅ `buildBreadcrumb` |

### C. 生命周期清理

| 场景 | 清理行为 | 验证 |
|---|---|---|
| `set_active_task` (session) | 清除指向不同任务的 degraded | ✅ `clear_degraded_active_task(keep_task_path)` |
| `clear_active_task` (无 key) | 清除 degraded | ✅ 直接删除 |
| `clear_active_task` (有 key) | 清除指向同任务的 degraded | ✅ `_same_task_reference` 检查 |
| `clear_task_from_sessions` | 清除指向目标任务的 degraded | ✅ canonical 比较 |
| `task.py archive` | 通过 `clear_task_from_sessions` | ✅ 调用链正确 |

### D. 测试覆盖

| 测试 | 覆盖场景 |
|---|---|
| `test_cmd_start_without_session_identity_persists_degraded_fallback` | degraded 写入 |
| `test_resolve_active_task_uses_degraded_fallback_when_no_session_context` | degraded 解析 |
| `test_clear_active_task_without_session_identity_clears_degraded_fallback` | degraded 清理 |
| `test_statusline_keeps_stale_task_visible` | stale 可见性 |
| `test_statusline_marks_degraded_tasks_in_output` | statusline degraded |
| `test_python_hook_maps_stale_pseudo_status_to_stale_block` | stale breadcrumb |
| `test_python_hook_maps_codex_inline_stale_pseudo_status_to_stale_block` | codex stale |
| `test_python_hook_surfaces_degraded_mode_in_header` | degraded breadcrumb |
| `test_opencode_js_uses_degraded_fallback_when_no_session_context` | JS degraded |

### E. 文档一致性

- `workflow.md` 第 76 行：Current-task mechanism 描述包含 degraded fallback ✅
- `workflow.md` 第 440 行：Phase 1.4 degraded mode 说明 ✅
- `active_task.py` docstring：包含 degraded fallback 说明 ✅

---

## 结论

**所有第一轮和第二轮发现的问题均已修复。无新缺漏、无残留问题。**

升级兼容性修改已完全收敛：
- 功能实现完整（degraded fallback 全链路）
- 跨平台一致（Python / JS 解析顺序、breadcrumb 可见性）
- 清理机制健全（5 种清理场景全覆盖）
- 测试覆盖充分（9 个针对性测试，19/19 通过）
- 文档同步更新

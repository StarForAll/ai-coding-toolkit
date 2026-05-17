# PRD: 修复 install-workflow.py 中 Issue 7 补丁导致的 Codex hook 语法错误

## 问题背景

在 `/tmp/trellis-0.5.16-2` 临时项目中使用 Codex 时，UserPromptSubmit hook 因 SyntaxError 导致 exit code 1，完全无法工作。

## 根因分析

### Bug 1（Critical）：Issue 7 补丁插入位置错误，导致 Codex hook 语法崩溃

**文件**：`docs/workflows/新项目开发工作流/commands/install-workflow.py`
**位置**：`patch_inject_workflow_state_hook()` 函数，第 1153-1160 行

`install-workflow.py` 在嵌入工作流时，通过文本锚点替换方式给 `.codex/hooks/inject-workflow-state.py` 打补丁。Issue 7 补丁的目标是在 `load_breadcrumbs()` 的 `try` 块内、`read_text` 行之后插入 `re.sub` 代码块剥离行。

**问题**：锚点行 `read_text_anchor` 使用 8 空格缩进（`try` 块内），但插入行 `code_block_strip_line` 使用 4 空格缩进（函数体层级）。插入后产生：

```python
    try:
        content = workflow.read_text(encoding="utf-8")
    content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)  # ← 在 try body 和 except 之间
    except OSError:
        return {}
```

Python 解析器在 `try` 体之后期望 `except`/`finally`，却遇到一条缩进不匹配的赋值语句，导致 `SyntaxError: expected 'except' or 'finally' block`。

**修复方案**：将 `code_block_strip_line` 的缩进从 4 空格改为 8 空格，使其正确位于 `try` 块内部：

```python
code_block_strip_line = '        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)\n'
```

修复后生成代码：
```python
    try:
        content = workflow.read_text(encoding="utf-8")
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    except OSError:
        return {}
```

### Bug 2（Moderate）：Issue 7 补丁仅应用于 `.codex/` hook，未应用于 `.claude/` hook

**文件**：`docs/workflows/新项目开发工作流/commands/install-workflow.py`
**位置**：`patch_inject_workflow_state_hook()` 函数，第 1141 行

当前 `patch_inject_workflow_state_hook()` 仅处理 `.codex/hooks/inject-workflow-state.py`，不处理 `.claude/hooks/inject-workflow-state.py`。

经验证，`.claude/hooks/inject-workflow-state.py` 的 `load_breadcrumbs()` 同样缺少代码块剥离逻辑，导致从 `workflow.md` 代码块内错误匹配 `[workflow-state:my-status]` 标签（1 个误报）。

**修复方案**：扩展 `patch_inject_workflow_state_hook()` 使其对 `.claude/hooks/inject-workflow-state.py` 也执行相同的 Issue 7 补丁（代码块剥离）。仅插入代码块剥离行，不插入 Issue 1 的 `workflow-state.json` 补丁（Claude 的状态解析路径与 Codex 不同，Issue 1 仅适用于 Codex）。

### Bug 3（Low）：Issue 1 补丁仅应用于 `.codex/` hook

Issue 1（`workflow-state.json.stage` 优先级覆盖）仅对 `.codex/hooks/inject-workflow-state.py` 应用。`.claude/hooks/inject-workflow-state.py` 的 `get_active_task()` 不读取 `workflow-state.json`。

经分析，Claude Code 通过 `session-start.py` 注入上下文，其状态解析路径使用 `active_task.py` 的 `resolve_active_task()`，不经过 `inject-workflow-state.py` 的 `get_active_task()`。因此 Claude 的 `inject-workflow-state.py` 中 `get_active_task()` 的返回值对 Claude Code 的行为没有影响，Issue 1 不需要扩展到 `.claude/` hook。

**结论**：Bug 3 不是实际问题，不在本次修复范围内。

## 修复范围

仅修改 `docs/workflows/新项目开发工作流/commands/install-workflow.py`：

1. **Bug 1 修复**：将第 1156 行 `code_block_strip_line` 的缩进从 4 空格改为 8 空格
2. **Bug 2 修复**：在 `patch_inject_workflow_state_hook()` 中增加对 `.claude/hooks/inject-workflow-state.py` 的 Issue 7 补丁逻辑

## 验证方案

1. 对修复后的 `install-workflow.py` 执行 `python3 -c "import ast; ast.parse(open('install-workflow.py').read())"` 确认无语法错误
2. 在 `/tmp/trellis-0.5.16-2` 上用修复后的 `install-workflow.py --dry-run` 验证补丁输出
3. 对修复后生成的 `.codex/hooks/inject-workflow-state.py` 和 `.claude/hooks/inject-workflow-state.py` 分别做 AST 解析验证无语法错误
4. 运行现有的 `test_workflow_installers.py` 确认无回归

## 约束

- 修改范围仅限 `docs/workflows/新项目开发工作流/commands/install-workflow.py`
- 不修改其他目录下的任何文件
- 不引入新的补丁位置错误或缩进问题

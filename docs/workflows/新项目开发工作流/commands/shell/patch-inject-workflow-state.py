#!/usr/bin/env python3
"""Patch inject-workflow-state hooks to prefer workflow-state.json.stage as breadcrumb tag.

When installed into a target project, this patch modifies the inject-workflow-state
hook (Python or JS) so that it reads workflow-state.json.stage first and only
falls back to task.json.status when no workflow-state.json exists.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PY_PATCH_MARKER = "# strong-gate-breadcrumb-patch-applied"
JS_PATCH_MARKER = "// strong-gate-breadcrumb-patch-applied"


def patch_python_hook(target_path: Path) -> bool:
    """Patch a Python inject-workflow-state.py to prefer workflow-state.json.stage."""
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")

    if PY_PATCH_MARKER in content:
        print(f"✅ {target_path} 已包含强门禁面包屑补丁，跳过")
        return True

    # Find the section where task.json status is read and add workflow-state.json
    # preference before it. We look for the pattern where status is read from task.json.
    # Inject a block that checks workflow-state.json first.

    # Look for a line like: status = task_data.get("status", ...)
    # or similar status reading from task.json
    pattern = re.compile(r'(\s+)(status\s*=\s*(?:task_data|task_json|data)\.get\(\s*["\']status["\'])')

    match = pattern.search(content)
    if not match:
        print(f"⚠️ {target_path} 中未找到 status 读取逻辑，跳过补丁")
        return False

    indent = match.group(1)
    original_line = match.group(0)

    patch_block = f'''{indent}{PY_PATCH_MARKER}
{indent}# Prefer workflow-state.json.stage over task.json.status for strong-gate model
{indent}_ws_path = task_dir / "workflow-state.json" if 'task_dir' in dir() else None
{indent}if _ws_path is not None and _ws_path.is_file():
{indent}    try:
{indent}        import json as _json
{indent}        _ws = _json.loads(_ws_path.read_text(encoding="utf-8"))
{indent}        _stage = _ws.get("stage", "")
{indent}        _STRONG_GATE_STAGES = {{"feasibility", "brainstorm", "design", "plan", "implementation", "test-first", "project-audit", "check", "review-gate", "finish-work", "delivery", "record-session"}}
{indent}        if _stage in _STRONG_GATE_STAGES:
{indent}            status = _stage
{indent}    except Exception:
{indent}        pass
{indent}if 'status' not in dir() or not status:
{indent}    '''

    new_content = content[:match.start()] + patch_block + original_line + content[match.end():]
    target_path.write_text(new_content, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用强门禁面包屑补丁")
    return True


def patch_js_hook(target_path: Path) -> bool:
    """Patch a JS inject-workflow-state.js to prefer workflow-state.json.stage."""
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过")
        return False

    content = target_path.read_text(encoding="utf-8")

    if JS_PATCH_MARKER in content:
        print(f"✅ {target_path} 已包含强门禁面包屑补丁，跳过")
        return True

    # Similar approach for JS - find where status is read from task.json
    # and inject workflow-state.json preference before it
    pattern = re.compile(r'(\s+)(const\s+status\s*=\s*(?:taskData|task_json|data)\[?["\']status["\']\]?)')

    match = pattern.search(content)
    if not match:
        print(f"⚠️ {target_path} 中未找到 status 读取逻辑，跳过补丁")
        return False

    indent = match.group(1)
    original_line = match.group(0)

    patch_block = f'''{indent}{JS_PATCH_MARKER}
{indent}// Prefer workflow-state.json.stage over task.json.status for strong-gate model
{indent}let status;
{indent}try {{
{indent}  const wsPath = path.join(taskDir, "workflow-state.json");
{indent}  if (fs.existsSync(wsPath)) {{
{indent}    const ws = JSON.parse(fs.readFileSync(wsPath, "utf-8"));
{indent}    const strongGateStages = new Set(["feasibility", "brainstorm", "design", "plan", "implementation", "test-first", "project-audit", "check", "review-gate", "finish-work", "delivery", "record-session"]);
{indent}    if (strongGateStages.has(ws.stage)) {{
{indent}      status = ws.stage;
{indent}    }}
{indent}  }}
{indent}}} catch (e) {{}}
{indent}if (!status) {{
{indent}  '''

    new_content = content[:match.start()] + patch_block + original_line + content[match.end():]
    target_path.write_text(new_content, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用强门禁面包屑补丁 (JS)")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: patch-inject-workflow-state.py <target_hook_path> [<target_hook_path2> ...]")
        return 1

    success = True
    for path_str in sys.argv[1:]:
        target_path = Path(path_str).resolve()
        if target_path.suffix == ".py":
            if not patch_python_hook(target_path):
                success = False
        elif target_path.suffix == ".js":
            if not patch_js_hook(target_path):
                success = False
        else:
            print(f"⚠️ 不支持的文件类型: {target_path.suffix}")
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

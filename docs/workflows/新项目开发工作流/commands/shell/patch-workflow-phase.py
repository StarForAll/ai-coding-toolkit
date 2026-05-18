#!/usr/bin/env python3
"""Patch workflow_phase.py to reject old #### X.Y step lookups when strong-gate model is active.

When installed into a target project, this patch modifies workflow_phase.py's
get_step() so that it refuses to return old Phase 1/2/3 steps if a
workflow-state.json with a valid strong-gate stage is detected.
"""

from __future__ import annotations

import sys
from pathlib import Path

PATCH_MARKER = "# strong-gate-phase-patch-applied"

PATCH_BLOCK = '''
    # --- strong-gate phase patch ---
    # When a workflow-state.json with a valid strong-gate stage exists,
    # refuse to return old #### X.Y step matches and direct to route instead.
    try:
        import json as _json
        import subprocess as _sp
        from pathlib import Path as _Path
        import sys as _sys
        _ws_path = None
        # Walk up to find trellis root
        for _p in _Path(__file__).resolve().parents:
            _trellis = _p / ".trellis"
            if _trellis.is_dir():
                _task_script = _trellis / "scripts" / "task.py"
                if _task_script.is_file():
                    _r = _sp.run(
                        [_sys.executable, str(_task_script), "current"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=10,
                    )
                    if _r.returncode == 0 and _r.stdout.strip():
                        _active_task_dir = _Path(_r.stdout.strip())
                        if _active_task_dir.is_dir() and (_active_task_dir / "workflow-state.json").is_file():
                            _ws_path = _active_task_dir / "workflow-state.json"
                break
        if _ws_path is not None and _ws_path.is_file():
            _ws_data = _json.loads(_ws_path.read_text(encoding="utf-8"))
            _stage = _ws_data.get("stage", "")
            _STRONG_GATE_STAGES = {
                "feasibility", "brainstorm", "design", "plan",
                "implementation", "test-first", "project-audit",
                "check", "review-gate", "finish-work", "delivery", "record-session",
            }
            if _stage in _STRONG_GATE_STAGES:
                print("⚠️ 强门禁模式下旧 step 查询已禁用，请使用 workflow-state.py route", file=_sys.stderr)
                return ""
    except Exception:
        pass
    # --- end strong-gate phase patch ---
'''


def patch_workflow_phase(target_path: Path) -> bool:
    """Apply the strong-gate patch to workflow_phase.py.

    Returns True if the patch was applied or was already present.
    """
    if not target_path.is_file():
        print(f"⚠️ {target_path} 不存在，跳过补丁")
        return False

    content = target_path.read_text(encoding="utf-8")

    if PATCH_MARKER in content:
        print(f"✅ {target_path} 已包含强门禁补丁，跳过")
        return True

    # Find the get_step function and inject the patch at its start
    # Look for the first return statement in get_step
    import re
    # Insert patch after the function def line and initial setup
    pattern = re.compile(r'(def get_step\([^)]*\)[^:]*:\n)')
    match = pattern.search(content)
    if not match:
        print(f"⚠️ {target_path} 中未找到 get_step 函数定义，跳过补丁")
        return False

    insert_pos = match.end()
    patch_with_marker = f"    {PATCH_MARKER}\n{PATCH_BLOCK}\n"

    new_content = content[:insert_pos] + patch_with_marker + content[insert_pos:]
    target_path.write_text(new_content, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用强门禁阶段补丁")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: patch-workflow-phase.py <target_workflow_phase.py_path>")
        return 1

    target_path = Path(sys.argv[1]).resolve()
    if patch_workflow_phase(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

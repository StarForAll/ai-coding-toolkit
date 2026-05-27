#!/usr/bin/env python3
"""Patch workflow_phase.py to preserve step-level compatibility under strong-gate mode.

When installed into a target project, this patch keeps workflow_phase.py's
get_step() compatible with the strong-gate workflow by preserving step-level
lookup for the baseline `get_context.py --mode phase --step <X.Y>` contract.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

PATCH_MARKER = "# strong-gate-phase-patch-applied"

PATCH_BLOCK = '''
    # --- strong-gate phase patch ---
    # When a workflow-state.json with a valid strong-gate stage exists,
    # keep the step-level compatibility layer available for baseline
    # get_context.py --mode phase --step lookups.
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
                "implementation", "check", "review-gate",
                "project-audit", "delivery",
            }
            if _stage in _STRONG_GATE_STAGES:
                pass
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

    try:
        module = ast.parse(content)
    except SyntaxError:
        print(f"⚠️ {target_path} 不是合法 Python 文件，跳过补丁")
        return False

    get_step_node = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "get_step":
            get_step_node = node
            break

    if get_step_node is None:
        print(f"⚠️ {target_path} 中未找到 get_step 函数定义，跳过补丁")
        return False

    insert_line = get_step_node.lineno
    if (
        get_step_node.body
        and isinstance(get_step_node.body[0], ast.Expr)
        and isinstance(getattr(get_step_node.body[0], "value", None), ast.Constant)
        and isinstance(get_step_node.body[0].value.value, str)
    ):
        insert_line = get_step_node.body[0].end_lineno or insert_line

    lines = content.splitlines(keepends=True)
    patch_with_marker = f"    {PATCH_MARKER}\n{PATCH_BLOCK}\n"
    new_content = "".join(lines[:insert_line]) + patch_with_marker + "".join(lines[insert_line:])
    target_path.write_text(new_content, encoding="utf-8")
    print(f"✅ 已为 {target_path} 应用强门禁阶段补丁")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the strong-gate workflow_phase.py patch to a target workflow_phase.py file."
    )
    parser.add_argument("target_path", help="Path to the target workflow_phase.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    if patch_workflow_phase(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

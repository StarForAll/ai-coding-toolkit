#!/usr/bin/env python3
"""Patch session-start.py _get_task_status() to use strong-gate workflow-state routing.

When installed into a target project, this patch replaces session-start.py's
_get_task_status() routing logic with strong-gate `workflow-state.py route`
routing. The injected block always returns, making the old PLANNING/READY case
logic unreachable.

The patched session-start carrier delegates to `workflow-state.py route`
whenever the helper script exists, even if `workflow-state.json` is missing or
invalid. That lets the authoritative router surface `repair_needed`,
`context_needed`, `awaiting_confirmation_with_blockers`, or other formal strong-
gate actions instead of collapsing them into a misleading `ACTIVE` fallback.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATCH_MARKER = "# strong-gate-session-start-patch-applied"
ROUTE_FIRST_MARKER = "# [workflow-embed-patch:session-start-route-first]"

PATCH_BLOCK = '''
    # --- strong-gate session-start patch ---
    # Route through workflow-state.py even when workflow-state.json is missing;
    # the router itself decides repair_needed vs reenter vs blocked.
    try:
        _ws_script = trellis_dir / "scripts" / "workflow" / "workflow-state.py"
        if not _ws_script.is_file():
            _ws_script = trellis_dir / "scripts" / "workflow-state.py"
        if _ws_script.is_file():
            import subprocess as _sp
            import json as _json
            _route_result = _sp.run(
                [
                    sys.executable,
                    str(_ws_script),
                    "route",
                    str(task_dir),
                    "--project-root",
                    str(trellis_dir.parent),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if _route_result.returncode == 0 and _route_result.stdout.strip():
                _route_data = _json.loads(_route_result.stdout.strip())
                _action = _route_data.get("action", "")
                _r_stage = _route_data.get("stage", "")
                _r_stage_status = _route_data.get("stage_status", "")
                _r_blockers = _route_data.get("blockers", [])
                _r_reason = _route_data.get("reason", "")
                _r_target = _route_data.get("target", "")
                _r_warnings = _route_data.get("warnings", [])
                _status_label = _r_stage or _action or "active"
                _lines = [
                    f"Status: STRONG-GATE ({_status_label})",
                    f"Task: {task_title}",
                    "Source: workflow-state.route",
                ]
                if _r_stage_status:
                    _lines.append(f"Stage-Status: {_r_stage_status}")
                if _action:
                    _lines.append(f"Action: {_action}")
                if _r_target:
                    _lines.append(f"Target-Stage: {_r_target}")
                if _r_reason:
                    _lines.append(f"Reason: {_r_reason}")
                if isinstance(_r_blockers, list) and _r_blockers:
                    _lines.append(f"Blockers: {'; '.join(str(item) for item in _r_blockers)}")
                if isinstance(_r_warnings, list) and _r_warnings:
                    _lines.append(f"Warnings: {'; '.join(str(item) for item in _r_warnings)}")
                _lines.append(
                    "Next-Action: Follow the action above. Use `workflow-state.py route` "
                    "to re-check routing at any time. Use `workflow-state.py set --stage <stage>` "
                    "to transition stages when gate conditions are met."
                )
                return "\\n".join(_lines)
        return f"Status: ACTIVE\\nTask: {task_title}\\nSource: {active.source}"
    except Exception:
        return f"Status: ACTIVE\\nTask: {task_title}\\nSource: {active.source}"
    # --- end strong-gate session-start patch ---
'''


def patch_session_start(target_path: Path) -> bool:
    """Apply the strong-gate patch to session-start.py's _get_task_status().

    Returns True if the patch was applied or was already present.
    """
    if not target_path.is_file():
        print(f"Warning: {target_path} does not exist, skipping patch")
        return False

    content = target_path.read_text(encoding="utf-8")

    if PATCH_MARKER in content and ROUTE_FIRST_MARKER in content:
        print(f"OK: {target_path} already contains strong-gate patch, skipping")
        return True

    if PATCH_MARKER in content and ROUTE_FIRST_MARKER not in content:
        start_idx = content.find(f"    {PATCH_MARKER}")
        block_start = content.find("    # --- strong-gate session-start patch ---", start_idx)
        block_end = content.find("    # --- end strong-gate session-start patch ---", block_start)
        if start_idx != -1 and block_start != -1 and block_end != -1:
            block_end = content.find("\n", block_end)
            if block_end == -1:
                block_end = len(content)
            replacement = f"    {PATCH_MARKER}\n    {ROUTE_FIRST_MARKER}\n{PATCH_BLOCK}\n"
            new_content = content[:start_idx] + replacement + content[block_end:]
            target_path.write_text(new_content, encoding="utf-8")
            print(f"OK: Upgraded strong-gate session-start patch in {target_path}")
            return True

    # Find the _get_task_status function and the point where task_dir and
    # task_title are both resolved. We need to inject AFTER the task_title
    # is known (because the patch references task_title) but BEFORE the
    # old PLANNING/READY routing cases.
    #
    # Strategy: find the line "task_title = task_data.get("task_title" ..."
    # and inject after the next blank line, or find the stale-pointer return
    # block and inject after it (before the old case logic starts).
    #
    # Most reliable: insert right after the task_title assignment and the
    # task_status assignment, which are both available before Case 3.

    # Look for the task_status assignment line that precedes the case logic
    # Pattern: task_status = task_data.get("status", "unknown")
    pattern = re.compile(
        r'(task_status\s*=\s*task_data\.get\(\s*["\']status["\']\s*,\s*["\']unknown["\']\s*\)\s*\n)'
    )

    match = pattern.search(content)
    if not match:
        # Fallback: try to find the completed-task check and insert before it
        # This means we need to be after task_title is available
        pattern2 = re.compile(r'(\s+# Case 3: Task completed)')
        match2 = pattern2.search(content)
        if not match2:
            print(f"Warning: {target_path} does not contain expected _get_task_status structure, skipping patch")
            return False
        # Insert before "# Case 3:" but we need task_title to be available
        # Check if task_title is defined above this point
        task_title_check = re.compile(r'task_title\s*=')
        pre_content = content[:match2.start()]
        if not task_title_check.search(pre_content):
            print(f"Warning: {target_path} task_title not resolved before insertion point, skipping patch")
            return False
        insert_pos = match2.start()
    else:
        insert_pos = match.end()

    patch_with_marker = f"    {PATCH_MARKER}\n    {ROUTE_FIRST_MARKER}\n{PATCH_BLOCK}\n"

    new_content = content[:insert_pos] + patch_with_marker + content[insert_pos:]
    target_path.write_text(new_content, encoding="utf-8")
    print(f"OK: Applied strong-gate session-start patch to {target_path}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: patch-session-start-strong-gate.py <target_session_start.py_path>")
        return 1

    target_path = Path(sys.argv[1]).resolve()
    if patch_session_start(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Patch task.py cmd_start() to skip status flip under strong-gate model.

When installed into a target project, this patch modifies task.py's cmd_start()
so that when a workflow-state.json exists in the active task directory, it does
NOT flip task.json status from planning → in_progress. Under the strong-gate
model, workflow-state.json.stage is the single source of truth; flipping
task.json.status creates a dual-truth conflict.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"

PATCH_BLOCK = '''
        # --- strong-gate no-status-flip patch ---
        # Under strong-gate model, workflow-state.json.stage is the single
        # source of truth. Do not flip task.json status when workflow-state.json
        # exists, as that creates a dual-truth conflict.
        try:
            _ws_check = Path(task_dir) / "workflow-state.json"
            if _ws_check.is_file():
                print(colored("⏭ Strong-gate mode: skipping task.json status flip (workflow-state.json is source of truth)", Colors.YELLOW))
            else:
                task_data["status"] = "in_progress"
                write_json(task_json_path, task_data)
        except Exception:
            task_data["status"] = "in_progress"
            write_json(task_json_path, task_data)
        # --- end strong-gate no-status-flip patch ---
'''


def patch_task_start(target_path: Path) -> bool:
    """Apply the strong-gate no-status-flip patch to task.py's cmd_start().

    Returns True if the patch was applied or was already present.
    """
    if not target_path.is_file():
        print(f"Warning: {target_path} does not exist, skipping patch")
        return False

    content = target_path.read_text(encoding="utf-8")

    if PATCH_MARKER in content:
        print(f"OK: {target_path} already contains strong-gate no-status-flip patch, skipping")
        return True

    # Look for the status flip line in cmd_start:
    #   task_data["status"] = "in_progress"
    # preceded by the comment about flipping
    pattern = re.compile(
        r'(# Still flip task\.json status: planning → in_progress so downstream phases proceed\.\n)'
        r'(\s*)(task_data\["status"\]\s*=\s*"in_progress"\s*\n)'
    )

    match = pattern.search(content)
    if not match:
        # Try alternate pattern without the comment
        pattern2 = re.compile(
            r'(\s*)(task_data\["status"\]\s*=\s*"in_progress"\s*\n)'
        )
        match2 = pattern2.search(content)
        if not match2:
            print(f"Warning: {target_path} does not contain expected status flip in cmd_start, skipping patch")
            return False
        # Check we're inside cmd_start, not some other function
        func_check = content[:match2.start()]
        if "def cmd_start" not in func_check.rsplit("def ", 1)[-1]:
            print(f"Warning: {target_path} status flip not inside cmd_start, skipping patch")
            return False
        insert_pos = match2.start()
        # Replace the single status flip line
        new_content = content[:insert_pos] + f"    {PATCH_MARKER}\n{PATCH_BLOCK}\n" + content[match2.end():]
    else:
        # Replace the comment + status flip line with the patch block
        new_content = content[:match.start()] + f"    {PATCH_MARKER}\n{PATCH_BLOCK}\n" + content[match.end():]

    target_path.write_text(new_content, encoding="utf-8")
    print(f"OK: Applied strong-gate no-status-flip patch to {target_path}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: patch-task-start-strong-gate.py <target_task.py_path>")
        return 1

    target_path = Path(sys.argv[1]).resolve()
    if patch_task_start(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

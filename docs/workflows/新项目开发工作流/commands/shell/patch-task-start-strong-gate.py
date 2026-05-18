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

    pattern = re.compile(
        r'(?P<indent>\s*)if (?P<var>[A-Za-z_][A-Za-z0-9_]*) and (?P=var)\.get\("status"\) == "planning":\n'
        r'(?P=indent)    (?P=var)\["status"\] = "in_progress"\n'
        r'(?P=indent)    if write_json\(task_json_path, (?P=var)\):\n'
        r'(?P=indent)        print\(colored\("(?P<msg>[^"]+)", Colors\.GREEN\)\)\n'
    )

    def _replace(match: re.Match[str]) -> str:
        indent = match.group("indent")
        var_name = match.group("var")
        message = match.group("msg")
        return (
            f"{indent}{PATCH_MARKER}\n"
            f"{indent}if {var_name} and {var_name}.get(\"status\") == \"planning\":\n"
            f"{indent}    if (full_path / \"workflow-state.json\").is_file():\n"
            f"{indent}        print(colored(\"⏭ Strong-gate mode: skipping task.json status flip "
            f"(workflow-state.json is source of truth)\", Colors.YELLOW))\n"
            f"{indent}    else:\n"
            f"{indent}        {var_name}[\"status\"] = \"in_progress\"\n"
            f"{indent}        if write_json(task_json_path, {var_name}):\n"
            f"{indent}            print(colored(\"{message}\", Colors.GREEN))\n"
        )

    new_content, replacements = pattern.subn(_replace, content)
    if replacements == 0:
        print(f"Warning: {target_path} does not contain expected status flip blocks in cmd_start, skipping patch")
        return False

    target_path.write_text(new_content, encoding="utf-8")
    print(f"OK: Applied strong-gate no-status-flip patch to {target_path} ({replacements} block(s))")
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

#!/usr/bin/env python3
"""Patch task_store.py create flow to preserve the current active task on demand.

When installed into a target project, this patch modifies common/task_store.py's
cmd_create() so workflow commands can create child tasks without silently
switching the session's active task away from the parent coordinator task.

The patched behavior is opt-in: when `TRELLIS_PRESERVE_ACTIVE_TASK=1` and
`args.parent` is truthy, the auto-activate block is skipped for that create
invocation only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"

PATCH_BLOCK = """\
_preserve_active = bool(getattr(args, "parent", None)) and __import__("os").environ.get(
    "TRELLIS_PRESERVE_ACTIVE_TASK"
) == "1"
if _preserve_active:
    print(
        colored(
            "⏭ Preserving current active task while creating child task "
            "(TRELLIS_PRESERVE_ACTIVE_TASK=1)",
            Colors.YELLOW,
        ),
        file=sys.stderr,
    )
elif resolve_context_key():
"""


def patch_task_store(target_path: Path) -> bool:
    """Apply the preserve-active patch to common/task_store.py."""
    if not target_path.is_file():
        print(f"Warning: {target_path} does not exist, skipping patch")
        return False

    content = target_path.read_text(encoding="utf-8")
    if PATCH_MARKER in content:
        print(f"OK: {target_path} already contains preserve-active patch, skipping")
        return True

    pattern = re.compile(
        r"(?P<indent>\s*)from \.active_task import resolve_context_key, set_active_task\n"
        r"(?P=indent)if resolve_context_key\(\):\n"
    )
    match = pattern.search(content)
    if not match:
        print(f"Warning: {target_path} does not contain expected auto-activate block, skipping patch")
        return False

    indent = match.group("indent")
    patch = (
        f"{indent}from .active_task import resolve_context_key, set_active_task\n"
        f"{indent}{PATCH_MARKER}\n"
        + "\n".join(f"{indent}{line}" if line else "" for line in PATCH_BLOCK.rstrip("\n").splitlines())
        + "\n"
    )
    new_content = content[: match.start()] + patch + content[match.end() :]
    target_path.write_text(new_content, encoding="utf-8")
    print(f"OK: Applied preserve-active patch to {target_path}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: patch-task-create-preserve-active.py <target_task_store.py_path>")
        return 1

    target_path = Path(sys.argv[1]).resolve()
    if patch_task_store(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

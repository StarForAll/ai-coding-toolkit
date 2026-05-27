#!/usr/bin/env python3
"""Patch task.py cmd_start() to skip status flip under strong-gate model.

When installed into a target project, this patch modifies task.py's cmd_start()
so it no longer flips task.json status from planning → in_progress at all.
Under the strong-gate model, workflow-state.json.stage is the single source of
truth; continuing to mutate task.json progress values keeps producing legacy
semantics after startup even when routing has already moved to stage-based
authority.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"
LEGACY_STATUS_COMMENT = "# Still flip task.json status: planning → in_progress so downstream phases proceed.\n"
UPDATED_STATUS_COMMENT = "# Strong-gate mode keeps workflow-state.py route as the only stage authority.\n"
START_HELP_OLD = 'p_start = subparsers.add_parser("start", help="Set active task")\n'
START_HELP_NEW = (
    'p_start = subparsers.add_parser("start", help="Set active task '
    '(strong-gate: refresh pointer only; does not flip task.json status or advance workflow stage)")\n'
)
START_USAGE_PRINT_OLD = 'print("  python3 task.py start <dir>                        Set active task\\n")\n'
START_USAGE_PRINT_NEW = (
    'print("  python3 task.py start <dir>                        Set active task '
    '(strong-gate: pointer only; stage changes still go through workflow-state.py)\\n")\n'
)
START_DOC_OLD = "    python3 task.py start <dir>                 # Set active task\n"
START_DOC_NEW = (
    "    python3 task.py start <dir>                 # Set active task pointer only; "
    "stage changes still go through workflow-state.py\n"
)


def patch_task_start(target_path: Path) -> bool:
    """Apply the strong-gate no-status-flip patch to task.py's cmd_start().

    Returns True if the patch was applied or was already present.
    """
    if not target_path.is_file():
        print(f"Warning: {target_path} does not exist, skipping patch")
        return False

    content = target_path.read_text(encoding="utf-8")
    content = content.replace(LEGACY_STATUS_COMMENT, UPDATED_STATUS_COMMENT)
    content = content.replace(START_HELP_OLD, START_HELP_NEW)
    content = content.replace(START_USAGE_PRINT_OLD, START_USAGE_PRINT_NEW)
    content = content.replace(START_DOC_OLD, START_DOC_NEW)

    if PATCH_MARKER in content:
        if START_HELP_NEW not in content or START_USAGE_PRINT_NEW not in content:
            target_path.write_text(content, encoding="utf-8")
            print(f"OK: Refreshed strong-gate task.py start help text in {target_path}")
            return True
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
        return (
            f"{indent}{PATCH_MARKER}\n"
            f"{indent}if {var_name} and {var_name}.get(\"status\") == \"planning\":\n"
            f"{indent}    print(colored(\"⏭ Strong-gate mode: skipping legacy task.json status flip "
            f"(workflow-state.py route is authoritative)\", Colors.YELLOW))\n"
        )

    new_content, replacements = pattern.subn(_replace, content)
    if replacements == 0:
        print(f"Warning: {target_path} does not contain expected status flip blocks in cmd_start, skipping patch")
        return False

    target_path.write_text(new_content, encoding="utf-8")
    print(f"OK: Applied strong-gate no-status-flip patch to {target_path} ({replacements} block(s))")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the strong-gate task.py start patch to a target task.py file."
    )
    parser.add_argument("target_path", help="Path to the target task.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    if patch_task_start(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

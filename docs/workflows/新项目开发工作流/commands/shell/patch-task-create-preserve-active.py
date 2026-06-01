#!/usr/bin/env python3
"""Patch task_store.py create/archive flows for strong-gate projects.

When installed into a target project, this patch modifies common/task_store.py's
cmd_create() so workflow commands can create child tasks without silently
switching the session's active task away from the parent coordinator task.

The patched behavior is opt-in: when `TRELLIS_PRESERVE_ACTIVE_TASK=1` and
`args.parent` is truthy, the auto-activate block is skipped for that create
invocation only.

It also patches cmd_archive() so native archive cannot bypass workflow close-out
gates after the workflow is embedded.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"
ARCHIVE_PATCH_MARKER = "# [workflow-embed-patch:archive-closeout-gate]"

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
    changed = False

    pattern = re.compile(
        r"(?P<indent>\s*)from \.active_task import resolve_context_key, set_active_task\n"
        r"(?P=indent)if resolve_context_key\(\):\n"
    )
    if PATCH_MARKER not in content:
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
        content = content[: match.start()] + patch + content[match.end() :]
        changed = True

    if "import subprocess\n" not in content:
        if "import sys\n" in content:
            content = content.replace("import sys\n", "import sys\nimport subprocess\n", 1)
        else:
            content = "import sys\nimport subprocess\n" + content
        changed = True

    if ARCHIVE_PATCH_MARKER not in content:
        archive_guard = """\
    {marker}
    workflow_state_path = task_dir / "workflow-state.json"
    finish_work_checklist = task_dir / "finish-work-checklist.md"
    if workflow_state_path.is_file():
        workflow_state = read_json(workflow_state_path)
        if isinstance(workflow_state, dict):
            stage = workflow_state.get("stage")
            if stage not in {{None, "", "check", "review-gate", "delivery"}}:
                print(
                    colored(
                        f"Error: archive only after workflow close-out gate validation "
                        f"(current workflow-state stage={{stage!r}})",
                        Colors.RED,
                    ),
                    file=sys.stderr,
                )
                return 1
            status = workflow_state.get("status")
            if stage in {{"check", "review-gate", "delivery"}} and isinstance(status, str):
                if status not in {{"awaiting_user_confirmation", "completed"}}:
                    print(
                        colored(
                            f"Error: archive only after workflow close-out gate validation "
                            f"(current workflow-state status={{status!r}} for stage={{stage!r}})",
                            Colors.RED,
                        ),
                        file=sys.stderr,
                    )
                    return 1
    if not finish_work_checklist.is_file():
        print(
            colored(
                "Error: archive only after workflow close-out gate validation "
                "(missing finish-work-checklist.md)",
                Colors.RED,
            ),
            file=sys.stderr,
        )
        return 1
    workflow_validate_path = repo_root / ".trellis" / "scripts" / "workflow" / "workflow-state.py"
    if workflow_validate_path.is_file():
        validate_result = subprocess.run(
            [
                sys.executable,
                str(workflow_validate_path),
                "validate",
                str(task_dir),
                "--project-root",
                str(repo_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if validate_result.returncode != 0:
            validate_output = (validate_result.stdout + validate_result.stderr).strip()
            print(
                colored(
                    "Error: archive only after workflow close-out gate validation "
                    + (f"({{validate_output}})" if validate_output else "(workflow-state.py validate failed)"),
                    Colors.RED,
                ),
                file=sys.stderr,
            )
            return 1
""".format(marker=ARCHIVE_PATCH_MARKER)
        archive_hook = "    dir_name = task_dir.name\n    task_json_path = task_dir / FILE_TASK_JSON\n"
        if archive_hook in content:
            content = content.replace(archive_hook, archive_hook + "\n" + archive_guard, 1)
            changed = True

    if not changed:
        print(f"OK: {target_path} already contains preserve-active/archive close-out patch, skipping")
        return True

    target_path.write_text(content, encoding="utf-8")
    print(f"OK: Applied preserve-active/archive close-out patch to {target_path}")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the preserve-active patch to a target common/task_store.py file."
    )
    parser.add_argument("target_path", help="Path to the target common/task_store.py file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_path = Path(args.target_path).resolve()
    if patch_task_store(target_path):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

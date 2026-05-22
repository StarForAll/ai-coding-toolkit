#!/usr/bin/env python3
"""Patch task runtime views to display strong-gate workflow stages."""

from __future__ import annotations

import argparse
from pathlib import Path

PATCH_MARKER = "# [workflow-embed-patch:strong-gate-task-status-view]"

TASKS_HELPER = """
WORKFLOW_STATE_FILE_NAME = "workflow-state.json"
TERMINAL_TASK_STATUSES = {"completed", "done", "archived"}


# [workflow-embed-patch:strong-gate-task-status-view]
def _shorten_status_detail(value: str, limit: int = 72) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


def _workflow_state_summary(state: dict) -> str | None:
    summary_parts: list[str] = []
    stage_status = state.get("stage_status")
    if isinstance(stage_status, str) and stage_status and stage_status != "in_progress":
        summary_parts.append(f"status={stage_status}")

    current_block = state.get("current_block")
    if isinstance(current_block, str) and current_block.strip():
        summary_parts.append(f"block={_shorten_status_detail(current_block)}")

    awaiting = state.get("awaiting_user_confirmation")
    if awaiting is True and stage_status != "awaiting_user_confirmation":
        summary_parts.append("awaiting_user_confirmation=true")

    return " | ".join(summary_parts) if summary_parts else None


def _display_status(task_dir: Path, data: dict) -> tuple[str, str | None]:
    state = read_json(task_dir / WORKFLOW_STATE_FILE_NAME)
    if isinstance(state, dict):
        stage = state.get("stage")
        if isinstance(stage, str) and stage:
            return stage, _workflow_state_summary(state)
        return "repair_needed", "repair_needed"

    raw_status = data.get("status", "unknown")
    if raw_status in TERMINAL_TASK_STATUSES:
        return "completed", None
    if isinstance(raw_status, str) and raw_status:
        return "repair_needed", "workflow-state.json missing"
    return "unknown", None
"""

LEGACY_TASKS_HELPER = """
WORKFLOW_STATE_FILE_NAME = "workflow-state.json"
TERMINAL_TASK_STATUSES = {"completed", "done", "archived"}


# [workflow-embed-patch:strong-gate-task-status-view]
def _display_status(task_dir: Path, data: dict) -> str:
    state = read_json(task_dir / WORKFLOW_STATE_FILE_NAME)
    if isinstance(state, dict):
        stage = state.get("stage")
        if isinstance(stage, str) and stage:
            return stage
        return "repair_needed"

    raw_status = data.get("status", "unknown")
    if raw_status in TERMINAL_TASK_STATUSES:
        return "completed"
    if isinstance(raw_status, str) and raw_status:
        return "repair_needed"
    return "unknown"
"""


def patch_task_views(tasks_path: Path) -> bool:
    if not tasks_path.is_file():
        print(f"⚠️ {tasks_path} 不存在，跳过补丁")
        return False

    content = tasks_path.read_text(encoding="utf-8")
    patched = content
    patched = patched.replace(
        '        return "needs-init", None\n',
        '        return "repair_needed", "workflow-state.json missing"\n',
    )
    patched = patched.replace(
        '        return "needs-init"\n',
        '        return "repair_needed"\n',
    )
    if PATCH_MARKER not in patched or "_workflow_state_summary(state)" not in patched:
        anchor = "\n\ndef load_task(task_dir: Path) -> TaskInfo | None:\n"
        if LEGACY_TASKS_HELPER.strip() in patched:
            patched = patched.replace(LEGACY_TASKS_HELPER.strip(), TASKS_HELPER.strip(), 1)
        elif anchor in patched:
            patched = patched.replace(anchor, "\n\n" + TASKS_HELPER.rstrip() + anchor, 1)

    if 'data["_workflow_display_extra"] = display_extra' not in patched:
        patched = patched.replace(
            '    if not data:\n        return None\n\n    return TaskInfo(\n',
            '    if not data:\n        return None\n\n'
            '    display_status, display_extra = _display_status(task_dir, data)\n'
            '    data["_workflow_display_extra"] = display_extra\n\n'
            '    return TaskInfo(\n',
            1,
        )
        patched = patched.replace(
            '    if not data:\n        return None\n    return TaskInfo(\n',
            '    if not data:\n        return None\n'
            '    display_status, display_extra = _display_status(task_dir, data)\n'
            '    data["_workflow_display_extra"] = display_extra\n'
            '    return TaskInfo(\n',
            1,
        )

    patched = patched.replace(
        '        status=data.get("status", "unknown"),\n',
        '        status=display_status,\n',
        1,
    )
    patched = patched.replace(
        '        status=_display_status(task_dir, data),\n',
        '        status=display_status,\n',
        1,
    )

    if patched == content:
        print(f"✅ {tasks_path} 已包含强门禁任务视图补丁，跳过")
        return True

    tasks_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {tasks_path} 应用强门禁任务视图补丁")
    return True


def patch_task_queue(task_queue_path: Path) -> bool:
    if not task_queue_path.is_file():
        print(f"⚠️ {task_queue_path} 不存在，跳过补丁")
        return False

    content = task_queue_path.read_text(encoding="utf-8")
    target = '    return list_tasks_by_status("planning", repo_root)\n'
    replacement = (
        f"    {PATCH_MARKER}\n"
        "    # Under strong-gate installs, active task views are stage-based.\n"
        "    # \"Pending\" therefore means every non-archived active task rather than\n"
        "    # the legacy raw task.json status=planning subset.\n"
        "    return list_tasks_by_status(None, repo_root)\n"
    )
    if PATCH_MARKER in content or target not in content:
        print(f"✅ {task_queue_path} 已包含强门禁 pending-task 视图补丁，跳过")
        return True

    task_queue_path.write_text(content.replace(target, replacement, 1), encoding="utf-8")
    print(f"✅ 已为 {task_queue_path} 应用强门禁 pending-task 视图补丁")
    return True


def patch_task_cli(task_cli_path: Path) -> bool:
    if not task_cli_path.is_file():
        print(f"⚠️ {task_cli_path} 不存在，跳过补丁")
        return False

    content = task_cli_path.read_text(encoding="utf-8")
    patched = content.replace(
        "  --status, -s <s>     Filter by status (planning, in_progress, review, completed)\n",
        "  --status, -s <s>     Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)\n",
    )
    patched = patched.replace(
        "  --status, -s <s>     Filter by workflow display status / stage (e.g. needs-init, feasibility, design, completed)\n",
        "  --status, -s <s>     Filter by workflow display status / stage (e.g. repair_needed, feasibility, design, completed)\n",
    )
    patched = patched.replace(
        '            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress}{marker}")\n',
        '            extra = t.raw.get("_workflow_display_extra")\n'
        '            extra_tag = f" {{{extra}}}" if extra else ""\n'
        '            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress}{extra_tag}{marker}")\n',
        1,
    )
    patched = patched.replace(
        '            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress} [{colored(t.assignee or \'-\', Colors.CYAN)}]{marker}")\n',
        '            extra = t.raw.get("_workflow_display_extra")\n'
        '            extra_tag = f" {{{extra}}}" if extra else ""\n'
        '            print(f"{prefix}{dir_name}/ ({t.status}){pkg_tag}{progress}{extra_tag} [{colored(t.assignee or \'-\', Colors.CYAN)}]{marker}")\n',
        1,
    )
    patched = patched.replace(
        "  python3 task.py list --mine --status in_progress   # List my in-progress tasks\n",
        "  python3 task.py list --mine --status check         # List my tasks currently in check stage\n",
    )

    if patched == content:
        print(f"✅ {task_cli_path} 已包含强门禁 task CLI 展示补丁，跳过")
        return True

    task_cli_path.write_text(patched, encoding="utf-8")
    print(f"✅ 已为 {task_cli_path} 应用强门禁 task CLI 展示补丁")
    return True


def patch_task_status_views(root: Path) -> bool:
    tasks_path = root / ".trellis" / "scripts" / "common" / "tasks.py"
    task_queue_path = root / ".trellis" / "scripts" / "common" / "task_queue.py"
    task_cli_path = root / ".trellis" / "scripts" / "task.py"

    results = [
        patch_task_views(tasks_path),
        patch_task_queue(task_queue_path),
        patch_task_cli(task_cli_path),
    ]
    return any(results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply the strong-gate task status view patches to a target repository root."
    )
    parser.add_argument("target_root", help="Path to the target repository root")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_root = Path(args.target_root).resolve()
    return 0 if patch_task_status_views(target_root) else 1


if __name__ == "__main__":
    raise SystemExit(main())

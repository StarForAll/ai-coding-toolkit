from collections.abc import Iterator
from pathlib import Path

from .io import read_json
from .paths import FILE_TASK_JSON
from .types import TaskInfo


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
    stage_status = state.get("status") or state.get("stage_status")
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
    raw_status = data.get("status", "unknown")
    if raw_status in TERMINAL_TASK_STATUSES:
        return "completed", None

    state = read_json(task_dir / WORKFLOW_STATE_FILE_NAME)
    if isinstance(state, dict):
        stage = state.get("stage")
        if isinstance(stage, str) and stage:
            return stage, _workflow_state_summary(state)
        return "repair_needed", "repair_needed"
    if isinstance(raw_status, str) and raw_status:
        return "repair_needed", "workflow-state.json missing"
    return "unknown", None

def load_task(task_dir: Path) -> TaskInfo | None:
    task_json = task_dir / FILE_TASK_JSON
    if not task_json.is_file():
        return None
    data = read_json(task_json)
    if not data:
        return None
    display_status, display_extra = _display_status(task_dir, data)
    data["_workflow_display_extra"] = display_extra
    return TaskInfo(
        dir_name=task_dir.name,
        directory=task_dir,
        title=data.get("title") or data.get("name") or "unknown",
        status=display_status,
        assignee=data.get("assignee", ""),
        priority=data.get("priority", "P2"),
        children=tuple(data.get("children", [])),
        parent=data.get("parent"),
        package=data.get("package"),
        raw=data,
    )

def iter_active_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:
    return iter(())

def get_all_statuses(tasks_dir: Path) -> dict[str, str]:
    return {t.dir_name: t.status for t in iter_active_tasks(tasks_dir)}

def children_progress(children, all_statuses) -> str:
    return ""

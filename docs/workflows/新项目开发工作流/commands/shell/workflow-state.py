#!/usr/bin/env python3
"""Workflow strong-gate state helper.

This helper manages and validates the task-local workflow-state.json used by the
"新项目开发工作流" strong-gate stage model.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_FILE_NAME = "workflow-state.json"
TASK_FILE_NAME = "task.json"
CURRENT_TASK_FILE = ".trellis/.current-task"
REQUIREMENTS_DIR = Path("docs/requirements")
CUSTOMER_PRD = REQUIREMENTS_DIR / "customer-facing-prd.md"
DEVELOPER_PRD = REQUIREMENTS_DIR / "developer-facing-prd.md"

STAGES = {
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "implementation",
    "test-first",
    "project-audit",
    "check",
    "review-gate",
    "finish-work",
    "delivery",
    "record-session",
}
STAGE_STATUSES = {
    "in_progress",
    "blocked",
    "awaiting_user_confirmation",
    "completed",
}
SUPPORTED_STATE_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (current / ".trellis").is_dir():
            return current
        current = current.parent
    return None


def normalize_task_pointer(pointer: str, repo_root: Path) -> str:
    normalized = pointer.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("tasks/"):
        normalized = f".trellis/{normalized}"
    abs_candidate = Path(normalized)
    if abs_candidate.is_absolute():
        try:
            return abs_candidate.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            return abs_candidate.resolve().as_posix()
    return normalized


def build_default_state(stage: str) -> dict[str, Any]:
    return {
        "version": 1,
        "stage": stage,
        "stage_status": "in_progress",
        "current_block": None,
        "completed_blocks": [],
        "allowed_next_stages": [],
        "awaiting_user_confirmation": False,
        "last_confirmed_transition": None,
        "notes": [],
        "checkpoints": {
            "architecture_confirmed": False,
        },
        "updated_at": now_iso(),
    }


def resolve_task_dir(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"task dir not found: {path_str}")
    if not (path / TASK_FILE_NAME).is_file():
        raise FileNotFoundError(f"task.json not found in: {path}")
    return path


def load_state(task_dir: Path) -> tuple[Path, dict[str, Any] | None]:
    state_path = task_dir / STATE_FILE_NAME
    return state_path, read_json(state_path)


def bool_arg(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {raw}")


def validate_state_shape(state: dict[str, Any], errors: list[str]) -> None:
    required_keys = {
        "version",
        "stage",
        "stage_status",
        "current_block",
        "completed_blocks",
        "allowed_next_stages",
        "awaiting_user_confirmation",
        "last_confirmed_transition",
        "notes",
        "checkpoints",
        "updated_at",
    }
    missing = sorted(required_keys - state.keys())
    if missing:
        errors.append(f"workflow-state.json 缺少字段: {', '.join(missing)}")

    version = state.get("version")
    if version != SUPPORTED_STATE_VERSION:
        errors.append(
            f"workflow-state.json version 非法或暂不支持: {version!r}；当前仅支持 {SUPPORTED_STATE_VERSION}"
        )

    stage = state.get("stage")
    if stage not in STAGES:
        errors.append(f"stage 非法: {stage!r}")

    stage_status = state.get("stage_status")
    if stage_status not in STAGE_STATUSES:
        errors.append(f"stage_status 非法: {stage_status!r}")

    current_block = state.get("current_block")
    if current_block is not None and not isinstance(current_block, str):
        errors.append("current_block 必须是字符串或 null")

    completed_blocks = state.get("completed_blocks")
    if not isinstance(completed_blocks, list) or not all(isinstance(item, str) for item in completed_blocks):
        errors.append("completed_blocks 必须是字符串数组")

    allowed_next = state.get("allowed_next_stages")
    if not isinstance(allowed_next, list) or not all(isinstance(item, str) for item in allowed_next):
        errors.append("allowed_next_stages 必须是字符串数组")
    else:
        invalid_next = [item for item in allowed_next if item not in STAGES]
        if invalid_next:
            errors.append(f"allowed_next_stages 存在非法阶段: {', '.join(invalid_next)}")

    awaiting = state.get("awaiting_user_confirmation")
    if not isinstance(awaiting, bool):
        errors.append("awaiting_user_confirmation 必须是布尔值")

    if awaiting is True and stage_status != "awaiting_user_confirmation":
        errors.append("awaiting_user_confirmation=true 时，stage_status 必须为 awaiting_user_confirmation")
    if stage_status == "awaiting_user_confirmation" and awaiting is not True:
        errors.append("stage_status=awaiting_user_confirmation 时，awaiting_user_confirmation 必须为 true")

    notes = state.get("notes")
    if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
        errors.append("notes 必须是字符串数组")

    checkpoints = state.get("checkpoints")
    if not isinstance(checkpoints, dict):
        errors.append("checkpoints 必须是对象")
    else:
        architecture_confirmed = checkpoints.get("architecture_confirmed")
        if not isinstance(architecture_confirmed, bool):
            errors.append("checkpoints.architecture_confirmed 必须是布尔值")

    transition = state.get("last_confirmed_transition")
    if transition is not None:
        if not isinstance(transition, dict):
            errors.append("last_confirmed_transition 必须是对象或 null")
        else:
            if not isinstance(transition.get("to"), str):
                errors.append("last_confirmed_transition.to 必须存在且为字符串")


def validate_current_task_pointer(task_dir: Path, repo_root: Path, current_task_file: Path, errors: list[str]) -> None:
    if not current_task_file.is_file():
        errors.append(f"{CURRENT_TASK_FILE} 不存在")
        return
    pointer = current_task_file.read_text(encoding="utf-8").strip()
    if not pointer:
        errors.append(f"{CURRENT_TASK_FILE} 不能为空，必须明确当前执行任务")
        return

    normalized_pointer = normalize_task_pointer(pointer, repo_root)
    expected = task_dir.resolve().relative_to(repo_root).as_posix()
    if normalized_pointer != expected:
        errors.append(
            f"{CURRENT_TASK_FILE} 指向 {normalized_pointer}，与当前 task {expected} 不一致"
        )


def validate_leaf_task(task_dir: Path, errors: list[str]) -> None:
    task_data = read_json(task_dir / TASK_FILE_NAME)
    if not task_data:
        errors.append("task.json 无法读取")
        return
    children = task_data.get("children", [])
    if isinstance(children, list) and children:
        errors.append("当前 task 已有 children，不应继续作为执行态叶子任务持有 workflow-state")


def validate_project_doc_boundary(state: dict[str, Any], project_root: Path, errors: list[str]) -> None:
    stage = state.get("stage")
    checkpoints = state.get("checkpoints", {})
    architecture_confirmed = checkpoints.get("architecture_confirmed", False)

    customer_prd = project_root / CUSTOMER_PRD
    developer_prd = project_root / DEVELOPER_PRD

    if stage in {"brainstorm", "design", "plan"} and not customer_prd.is_file():
        errors.append(f"缺少 {CUSTOMER_PRD.as_posix()}，当前阶段不满足正式需求文档门禁")

    if stage == "design" and architecture_confirmed is False and developer_prd.exists():
        errors.append(
            "技术架构尚未确认，但目标项目已存在 docs/requirements/developer-facing-prd.md；"
            "这违反“确认前严格草稿隔离”规则"
        )


def cmd_init(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task_dir)
    state_path, state = load_state(task_dir)
    if state_path.exists() and not args.force:
        print(f"❌ {state_path} 已存在；如需覆盖请使用 --force")
        return 1

    data = build_default_state(args.stage)
    write_json(state_path, data)
    print(f"✅ 已初始化 {state_path}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task_dir)
    state_path, state = load_state(task_dir)
    if state is None:
        print(f"❌ {state_path} 不存在或无法读取")
        return 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task_dir)
    state_path, state = load_state(task_dir)
    if state is None:
        print(f"❌ {state_path} 不存在或无法读取；请先运行 init")
        return 1

    if args.stage:
        state["stage"] = args.stage
    if args.stage_status:
        state["stage_status"] = args.stage_status
    if args.clear_current_block:
        state["current_block"] = None
    elif args.current_block is not None:
        state["current_block"] = args.current_block
    if args.completed_blocks is not None:
        state["completed_blocks"] = [item for item in args.completed_blocks.split(",") if item]
    if args.allowed_next is not None:
        state["allowed_next_stages"] = [item for item in args.allowed_next.split(",") if item]
    if args.awaiting_user_confirmation is not None:
        state["awaiting_user_confirmation"] = args.awaiting_user_confirmation
    if args.architecture_confirmed is not None:
        checkpoints = state.setdefault("checkpoints", {})
        checkpoints["architecture_confirmed"] = args.architecture_confirmed
    if args.note:
        notes = state.setdefault("notes", [])
        if not isinstance(notes, list):
            notes = []
            state["notes"] = notes
        notes.append(args.note)

    state["updated_at"] = now_iso()
    write_json(state_path, state)
    print(f"✅ 已更新 {state_path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task_dir)
    repo_root = find_repo_root(task_dir)
    state_path, state = load_state(task_dir)

    print("=== workflow-state 校验 ===")
    errors: list[str] = []

    if state is None:
        print(f"❌ {state_path} 不存在或无法读取")
        return 1
    print(f"✅ 找到 {state_path.name}")

    validate_state_shape(state, errors)

    should_check_current_task = not args.skip_current_task_check
    if should_check_current_task:
        if repo_root is None:
            errors.append("无法定位 repo root，不能校验 .current-task")
        else:
            current_task_file = (
                Path(args.current_task_file).resolve()
                if args.current_task_file
                else repo_root / CURRENT_TASK_FILE
            )
            validate_current_task_pointer(task_dir, repo_root, current_task_file, errors)
            validate_leaf_task(task_dir, errors)

    if args.project_root:
        validate_project_doc_boundary(state, Path(args.project_root).resolve(), errors)
    elif repo_root is not None:
        validate_project_doc_boundary(state, repo_root, errors)

    if errors:
        for message in errors:
            print(f"❌ {message}")
        return 1

    print("✅ workflow-state 校验通过")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="workflow strong-gate state helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a default workflow-state.json")
    init_parser.add_argument("task_dir")
    init_parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    show_parser = subparsers.add_parser("show", help="print workflow-state.json")
    show_parser.add_argument("task_dir")
    show_parser.set_defaults(func=cmd_show)

    set_parser = subparsers.add_parser("set", help="update workflow-state.json fields")
    set_parser.add_argument("task_dir")
    set_parser.add_argument("--stage", choices=sorted(STAGES))
    set_parser.add_argument("--stage-status", choices=sorted(STAGE_STATUSES))
    set_parser.add_argument("--current-block")
    set_parser.add_argument("--clear-current-block", action="store_true")
    set_parser.add_argument("--completed-blocks")
    set_parser.add_argument("--allowed-next")
    set_parser.add_argument("--awaiting-user-confirmation", type=bool_arg)
    set_parser.add_argument("--architecture-confirmed", type=bool_arg)
    set_parser.add_argument("--note")
    set_parser.set_defaults(func=cmd_set)

    validate_parser = subparsers.add_parser("validate", help="validate workflow-state.json and task boundaries")
    validate_parser.add_argument("task_dir")
    validate_parser.add_argument("--project-root")
    validate_parser.add_argument("--skip-current-task-check", action="store_true")
    validate_parser.add_argument("--current-task-file")
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

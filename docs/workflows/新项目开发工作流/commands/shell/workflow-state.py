#!/usr/bin/env python3
"""Workflow strong-gate state helper.

This helper manages and validates the task-local workflow-state.json used by the
"新项目开发工作流" strong-gate stage model.
"""

from __future__ import annotations

import argparse
import json
import re
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
TASK_PRD = Path("prd.md")
ASSESSMENT_FILE = Path("assessment.md")
VALID_ENGAGEMENT_TYPES = {"external_outsourcing", "non_outsourcing"}
MIN_KICKOFF_PAYMENT_RATIO = 30.0

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
EXECUTION_STAGES = {"implementation", "test-first"}
SUPPORTED_STATE_VERSION = 1
PROJECT_ESTIMATE_REQUIRED_STAGES = STAGES - {"feasibility", "brainstorm"}
# 只在 design/plan 校验 customer-facing PRD 的粗估摘要。
# 原因：L0 可在 brainstorm 收口后直接进入 start/implementation 或显式进入 test-first，
# 这些路径允许只保留 task-local prd.md 而不强制正式 customer-facing PRD。
# design/plan 负责第一次校验正式 customer-facing PRD 的粗估摘要；
# feasibility/brainstorm 之后的全部后续阶段则持续依赖 task-local prd.md 中的项目级粗估。
PROJECT_ESTIMATE_DOC_STAGES = {"design", "plan"}
TASK_ESTIMATE_MARKERS = (
    "## 项目级粗估",
    "预计总工时",
    "预计总工期",
    "预计完工窗口",
    "估算置信度",
    "估算前提",
)
CUSTOMER_ESTIMATE_MARKERS = (
    "## 项目级粗估摘要",
    "预计总工期",
    "预计完工窗口",
    "估算说明",
)


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
            "execution_authorized": False,
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
    # Tolerant: if version is missing, default to SUPPORTED_STATE_VERSION
    if "version" not in state:
        state["version"] = SUPPORTED_STATE_VERSION
    # Tolerant: ignore unknown keys (only validate required keys)

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
        execution_authorized = checkpoints.get("execution_authorized")
        if not isinstance(execution_authorized, bool):
            errors.append("checkpoints.execution_authorized 必须是布尔值")

    transition = state.get("last_confirmed_transition")
    if transition is not None:
        if not isinstance(transition, dict):
            errors.append("last_confirmed_transition 必须是对象或 null")
        else:
            if not isinstance(transition.get("from"), str):
                errors.append("last_confirmed_transition.from 必须存在且为字符串")
            if not isinstance(transition.get("to"), str):
                errors.append("last_confirmed_transition.to 必须存在且为字符串")
            if not isinstance(transition.get("confirmed_at"), str):
                errors.append("last_confirmed_transition.confirmed_at 必须存在且为字符串")


def validate_execution_boundary(state: dict[str, Any], errors: list[str]) -> None:
    stage = state.get("stage")
    checkpoints = state.get("checkpoints", {})
    execution_authorized = checkpoints.get("execution_authorized", False)
    transition = state.get("last_confirmed_transition")

    if stage in EXECUTION_STAGES:
        if execution_authorized is not True:
            errors.append(
                f"当前 stage={stage!r} 时，checkpoints.execution_authorized 必须为 true"
            )
        if not isinstance(transition, dict):
            errors.append(
                f"当前 stage={stage!r} 时，必须保留 last_confirmed_transition 作为进入执行阶段的确认记录"
            )
        elif transition.get("to") != stage:
            errors.append(
                f"当前 stage={stage!r} 时，last_confirmed_transition.to 必须等于当前 stage"
            )
    else:
        if execution_authorized is True:
            errors.append(
                f"当前 stage={stage!r} 不是执行阶段，checkpoints.execution_authorized 必须为 false"
            )


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


def load_task_json(path: Path) -> dict[str, Any] | None:
    data = read_json(path / TASK_FILE_NAME)
    if isinstance(data, dict):
        return data
    return None


def iter_task_lineage(task_dir: Path, repo_root: Path) -> list[Path]:
    lineage: list[Path] = []
    tasks_root = repo_root / ".trellis" / "tasks"
    current = task_dir.resolve()
    visited: set[Path] = set()

    while current not in visited and current.is_dir():
        visited.add(current)
        lineage.append(current)
        task_data = load_task_json(current)
        if not task_data:
            break
        parent_name = task_data.get("parent")
        if not isinstance(parent_name, str) or not parent_name:
            break
        parent_dir = tasks_root / parent_name
        if not parent_dir.is_dir():
            break
        current = parent_dir.resolve()

    return lineage


def find_assessment_file(task_dir: Path, repo_root: Path) -> Path | None:
    for candidate_dir in iter_task_lineage(task_dir, repo_root):
        assessment = candidate_dir / ASSESSMENT_FILE
        if assessment.is_file():
            return assessment
    return None


def extract_backticked_field(content: str, field_name: str) -> str | None:
    pattern = re.compile(rf'`{re.escape(field_name)}`:\s*`?(.+?)`?(?:\n|$)')
    match = pattern.search(content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def validate_external_project_controls(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    stage = state.get("stage")
    if stage == "feasibility":
        return

    assessment_file = find_assessment_file(task_dir, repo_root)
    if assessment_file is None:
        errors.append("缺少 assessment.md；任何项目都必须先经过 feasibility 并完成项目类别判断")
        return

    content = assessment_file.read_text(encoding="utf-8")
    engagement_type = extract_backticked_field(content, "project_engagement_type")
    if engagement_type is None:
        errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `project_engagement_type` 字段")
        return
    if engagement_type not in VALID_ENGAGEMENT_TYPES:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 的 `project_engagement_type` 取值无效: {engagement_type}"
        )
        return

    if engagement_type != "external_outsourcing":
        return

    kickoff_ratio = extract_backticked_field(content, "kickoff_payment_ratio")
    if kickoff_ratio is None:
        errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `kickoff_payment_ratio` 字段")
    else:
        percentages = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", kickoff_ratio)]
        if not percentages or min(percentages) < MIN_KICKOFF_PAYMENT_RATIO:
            errors.append(
                f"{assessment_file.relative_to(repo_root).as_posix()} 的 `kickoff_payment_ratio` "
                f"必须写明且最低不少于 {int(MIN_KICKOFF_PAYMENT_RATIO)}%"
            )

    kickoff_received = extract_backticked_field(content, "kickoff_payment_received")
    if kickoff_received is None:
        errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `kickoff_payment_received` 字段")
    elif kickoff_received not in {"yes", "no"}:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 的 `kickoff_payment_received` 只能填写 `yes` / `no`"
        )
    elif stage in EXECUTION_STAGES and kickoff_received != "yes":
        errors.append("外包项目在启动款未确认到账前，不得进入 implementation / test-first")

    delivery_track = extract_backticked_field(content, "delivery_control_track")
    if delivery_track is None:
        errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `delivery_control_track` 字段")
    elif delivery_track not in {"hosted_deployment", "trial_authorization"}:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 的 `delivery_control_track` 必须为 "
            "`hosted_deployment` 或 `trial_authorization`"
        )

    handover_trigger = extract_backticked_field(content, "delivery_control_handover_trigger")
    if handover_trigger is None:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `delivery_control_handover_trigger` 字段"
        )
    elif handover_trigger in {"...", "", "例如"}:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 的 `delivery_control_handover_trigger` 未填写具体值"
        )

    retained_scope = extract_backticked_field(content, "delivery_control_retained_scope")
    if retained_scope is None:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `delivery_control_retained_scope` 字段"
        )
    elif retained_scope in {"...", ""}:
        errors.append(
            f"{assessment_file.relative_to(repo_root).as_posix()} 的 `delivery_control_retained_scope` 未填写具体值"
        )

    if delivery_track == "trial_authorization":
        required_terms = [
            "trial_authorization_terms.validity",
            "trial_authorization_terms.clock_source_or_usage_basis",
            "trial_authorization_terms.expiration_behavior",
            "trial_authorization_terms.renewal_policy",
            "trial_authorization_terms.permanent_authorization_trigger",
        ]
        for term in required_terms:
            term_value = extract_backticked_field(content, term)
            if term_value is None:
                errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `{term}` 字段")
            elif term_value in {"...", ".", ""}:
                errors.append(
                    f"{assessment_file.relative_to(repo_root).as_posix()} 的 `{term}` 未填写具体值"
                )

def find_missing_markers(path: Path, markers: tuple[str, ...]) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return list(markers)
    return [marker for marker in markers if marker not in content]


def validate_project_doc_boundary(
    state: dict[str, Any],
    project_root: Path,
    task_dir: Path,
    errors: list[str],
) -> None:
    stage = state.get("stage")
    checkpoints = state.get("checkpoints", {})
    architecture_confirmed = checkpoints.get("architecture_confirmed", False)

    customer_prd = project_root / CUSTOMER_PRD
    developer_prd = project_root / DEVELOPER_PRD
    task_prd = task_dir / TASK_PRD

    if stage in {"design", "plan"} and not customer_prd.is_file():
        errors.append(f"缺少 {CUSTOMER_PRD.as_posix()}，当前阶段不满足正式需求文档门禁")

    if stage in PROJECT_ESTIMATE_REQUIRED_STAGES:
        if not task_prd.is_file():
            errors.append(f"缺少 {TASK_PRD.as_posix()}，当前阶段不满足项目级粗估门禁")
        else:
            missing_task_markers = find_missing_markers(task_prd, TASK_ESTIMATE_MARKERS)
            if missing_task_markers:
                errors.append(
                    f"{TASK_PRD.as_posix()} 缺少项目级粗估字段: {', '.join(missing_task_markers)}"
                )

    if stage in PROJECT_ESTIMATE_DOC_STAGES and customer_prd.is_file():
        missing_customer_markers = find_missing_markers(customer_prd, CUSTOMER_ESTIMATE_MARKERS)
        if missing_customer_markers:
            errors.append(
                f"{CUSTOMER_PRD.as_posix()} 缺少项目级粗估摘要字段: {', '.join(missing_customer_markers)}"
            )

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
    if args.execution_authorized is not None:
        checkpoints = state.setdefault("checkpoints", {})
        checkpoints["execution_authorized"] = args.execution_authorized
    if args.clear_last_transition:
        state["last_confirmed_transition"] = None
    elif args.transition_from is not None:
        state["last_confirmed_transition"] = {
            "from": args.transition_from,
            "to": state.get("stage"),
            "confirmed_at": now_iso(),
        }
    if args.note:
        notes = state.setdefault("notes", [])
        if not isinstance(notes, list):
            notes = []
            state["notes"] = notes
        notes.append(args.note)

    set_errors: list[str] = []
    validate_state_shape(state, set_errors)
    validate_execution_boundary(state, set_errors)
    if set_errors:
        for message in set_errors:
            print(f"❌ {message}")
        print("❌ 拒绝写入非法 workflow-state；请一次性完成合法的阶段切换参数")
        return 1

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
    validate_execution_boundary(state, errors)

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
            validate_external_project_controls(task_dir, repo_root, state, errors)

    if args.project_root:
        validate_project_doc_boundary(state, Path(args.project_root).resolve(), task_dir, errors)
    elif repo_root is not None:
        validate_project_doc_boundary(state, repo_root, task_dir, errors)

    if errors:
        for message in errors:
            print(f"❌ {message}")
        return 1

    print("✅ workflow-state 校验通过")
    return 0


# ---------------------------------------------------------------------------
# route / repair subcommands
# ---------------------------------------------------------------------------

INSTALL_RECORD = ".trellis/workflow-installed.json"
LIBRARY_LOCK = ".trellis/library-lock.yaml"
REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"


def detect_embed_invalid(repo_root: Path) -> str | None:
    install_record = repo_root / INSTALL_RECORD
    if not install_record.is_file():
        return None

    library_lock = repo_root / LIBRARY_LOCK
    if not library_lock.is_file():
        return f"检测到 {INSTALL_RECORD}，但缺少 {LIBRARY_LOCK}"

    try:
        lock_text = library_lock.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"{LIBRARY_LOCK} 不可读，无法确认最低资产集"

    if REQUIREMENTS_FOUNDATION_PACK not in lock_text:
        return f"{LIBRARY_LOCK} 缺少最低资产集 {REQUIREMENTS_FOUNDATION_PACK}"

    return None


def _route_result(
    target: str | None,
    action: str,
    reason: str,
    *,
    stage: str | None = None,
    stage_status: str | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "target": target,
        "action": action,
    }
    if stage is not None:
        result["stage"] = stage
    if stage_status is not None:
        result["stage_status"] = stage_status
    result["reason"] = reason
    result["blockers"] = blockers or []
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_route(args: argparse.Namespace) -> int:
    # Step 1: resolve repo_root
    if args.project_root:
        repo_root = Path(args.project_root).resolve()
    elif args.task_dir:
        repo_root = find_repo_root(Path(args.task_dir).resolve())
    else:
        repo_root = find_repo_root(Path.cwd())

    if repo_root is None:
        print(json.dumps({"error": "无法定位 repo root"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    embed_invalid_reason = detect_embed_invalid(repo_root)
    if embed_invalid_reason is not None:
        _route_result(None, "embed_invalid", embed_invalid_reason)
        return 0

    # Step 2: determine current-task pointer
    current_task_file = (
        Path(args.current_task_file).resolve()
        if args.current_task_file
        else repo_root / CURRENT_TASK_FILE
    )

    pointer: str | None = None
    if current_task_file.is_file():
        pointer = current_task_file.read_text(encoding="utf-8").strip() or None

    if not pointer:
        # No .current-task — scan .trellis/tasks/ for assessment.md
        tasks_root = repo_root / ".trellis" / "tasks"
        assessment_found: Path | None = None
        if tasks_root.is_dir():
            for candidate in tasks_root.rglob(ASSESSMENT_FILE.name):
                if candidate.is_file():
                    assessment_found = candidate
                    break

        if assessment_found is None:
            _route_result("feasibility", "first_entry", "无 assessment.md，首次进入 feasibility")
            return 0

        # Assessment exists — check if it permits brainstorm
        content = assessment_found.read_text(encoding="utf-8")
        # Look for "是否允许进入 brainstorm" field with a value containing "是"
        allow_brainstorm = False
        for line in content.splitlines():
            if "是否允许进入 brainstorm" in line and "是" in line:
                allow_brainstorm = True
                break

        if allow_brainstorm:
            _route_result(
                "brainstorm",
                "resume_with_assessment",
                f"assessment.md 存在于 {assessment_found.relative_to(repo_root).as_posix()}，允许进入 brainstorm",
            )
            return 0

        _route_result(
            None,
            "recovery_needed",
            "无 .current-task 且无法自动确定下一步",
        )
        return 0

    # Step 3: .current-task exists — validate it
    normalized = normalize_task_pointer(pointer, repo_root)
    task_dir = (repo_root / normalized).resolve()

    if not task_dir.is_dir():
        _route_result(None, "repair_needed", ".current-task 指向不存在的任务")
        return 0

    # Check leaf task (no children)
    task_data = read_json(task_dir / TASK_FILE_NAME)
    if task_data:
        children = task_data.get("children", [])
        if isinstance(children, list) and children:
            _route_result(None, "repair_needed", "当前 task 已有 children")
            return 0

    state_path, state = load_state(task_dir)
    if state is None:
        _route_result(None, "repair_needed", "缺少 workflow-state.json")
        return 0

    # Step 4: route by stage
    stage = state.get("stage", "")
    stage_status = state.get("stage_status", "")
    checkpoints = state.get("checkpoints", {})

    if stage_status == "awaiting_user_confirmation":
        _route_result(
            stage,
            "awaiting_confirmation",
            f"当前 stage={stage}, status=awaiting_user_confirmation",
            stage=stage,
            stage_status=stage_status,
        )
        return 0

    if stage in EXECUTION_STAGES:
        blockers: list[str] = []

        # Check execution_authorized
        execution_authorized = checkpoints.get("execution_authorized", False)
        if execution_authorized is not True:
            blockers.append("checkpoints.execution_authorized 未授权")

        # Check outsourcing kickoff gate
        assessment_file = find_assessment_file(task_dir, repo_root)
        if assessment_file is not None:
            a_content = assessment_file.read_text(encoding="utf-8")
            engagement_type = extract_backticked_field(a_content, "project_engagement_type")
            if engagement_type == "external_outsourcing":
                kickoff_received = extract_backticked_field(a_content, "kickoff_payment_received")
                if kickoff_received != "yes":
                    blockers.append("外包项目启动款未确认到账")

        if blockers:
            _route_result(
                stage,
                "blocked",
                f"当前 stage={stage} 存在阻塞条件",
                stage=stage,
                stage_status=stage_status,
                blockers=blockers,
            )
            return 0

        _route_result(
            stage,
            "reenter",
            f"当前 stage={stage}, status={stage_status}",
            stage=stage,
            stage_status=stage_status,
        )
        return 0

    # Non-execution stage — simple reenter
    _route_result(
        stage,
        "reenter",
        f"当前 stage={stage}, status={stage_status}",
        stage=stage,
        stage_status=stage_status,
    )
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    # Step 1: resolve repo_root
    task_dir_path = Path(args.task_dir).expanduser().resolve()
    if args.project_root:
        repo_root = Path(args.project_root).resolve()
    else:
        repo_root = find_repo_root(task_dir_path)

    if repo_root is None:
        print(json.dumps({"error": "无法定位 repo root"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    # Step 2: check if workflow-state.json already exists and is valid
    state_path, state = load_state(task_dir_path)
    if state is not None:
        check_errors: list[str] = []
        validate_state_shape(state, check_errors)
        if not check_errors:
            result = {
                "status": "ok",
                "message": "workflow-state.json 已存在且合法",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

    # Step 3: infer stage from artifacts
    evidence: list[str] = []

    # Check assessment.md in task lineage
    has_assessment = False
    if task_dir_path.is_dir() and (task_dir_path / TASK_FILE_NAME).is_file():
        assessment_file = find_assessment_file(task_dir_path, repo_root)
        if assessment_file is not None:
            has_assessment = True
            evidence.append("assessment.md 存在")
    else:
        # task_dir might not be a proper task dir — scan broadly
        tasks_root = repo_root / ".trellis" / "tasks"
        if tasks_root.is_dir():
            for candidate in tasks_root.rglob(ASSESSMENT_FILE.name):
                if candidate.is_file():
                    has_assessment = True
                    evidence.append("assessment.md 存在")
                    break

    if not has_assessment:
        inferred_stage = "feasibility"
        result = {
            "status": "repair_needed",
            "inferred_stage": inferred_stage,
            "confidence": "high",
            "evidence": ["assessment.md 不存在"],
            "message": f"推断当前阶段为 {inferred_stage}，请确认后使用 --apply 写入",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.apply:
            data = build_default_state(inferred_stage)
            write_json(state_path, data)
            print(json.dumps({"status": "applied", "stage": inferred_stage, "path": str(state_path)}, ensure_ascii=False, indent=2))
        return 0

    # Check customer-facing-prd.md
    customer_prd = repo_root / CUSTOMER_PRD
    has_customer_prd = customer_prd.is_file()
    if not has_customer_prd:
        inferred_stage = "brainstorm"
        result = {
            "status": "repair_needed",
            "inferred_stage": inferred_stage,
            "confidence": "high",
            "evidence": evidence + [f"{CUSTOMER_PRD.as_posix()} 不存在"],
            "message": f"推断当前阶段为 {inferred_stage}，请确认后使用 --apply 写入",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.apply:
            data = build_default_state(inferred_stage)
            write_json(state_path, data)
            print(json.dumps({"status": "applied", "stage": inferred_stage, "path": str(state_path)}, ensure_ascii=False, indent=2))
        return 0

    evidence.append(f"{CUSTOMER_PRD.as_posix()} 存在")

    # Check design/ dir in task_dir
    design_dir = task_dir_path / "design"
    if design_dir.is_dir():
        evidence.append("design/ 存在")
        task_plan = task_dir_path / "design" / "task_plan.md"
        if task_plan.is_file():
            evidence.append("design/task_plan.md 存在")
            inferred_stage = "plan"
        else:
            inferred_stage = "design"
    else:
        inferred_stage = "brainstorm"

    confidence = "high" if len(evidence) >= 2 else "medium"

    result = {
        "status": "repair_needed",
        "inferred_stage": inferred_stage,
        "confidence": confidence,
        "evidence": evidence,
        "message": f"推断当前阶段为 {inferred_stage}，请确认后使用 --apply 写入",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.apply:
        data = build_default_state(inferred_stage)
        write_json(state_path, data)
        print(json.dumps({"status": "applied", "stage": inferred_stage, "path": str(state_path)}, ensure_ascii=False, indent=2))

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
    set_parser.add_argument("--execution-authorized", type=bool_arg)
    set_parser.add_argument("--transition-from", choices=sorted(STAGES))
    set_parser.add_argument("--clear-last-transition", action="store_true")
    set_parser.add_argument("--note")
    set_parser.set_defaults(func=cmd_set)

    validate_parser = subparsers.add_parser("validate", help="validate workflow-state.json and task boundaries")
    validate_parser.add_argument("task_dir")
    validate_parser.add_argument("--project-root")
    validate_parser.add_argument("--skip-current-task-check", action="store_true")
    validate_parser.add_argument("--current-task-file")
    validate_parser.set_defaults(func=cmd_validate)

    route_parser = subparsers.add_parser("route", help="compute routing target for /trellis:start")
    route_parser.add_argument("task_dir", nargs="?", default=None)
    route_parser.add_argument("--project-root")
    route_parser.add_argument("--current-task-file")
    route_parser.set_defaults(func=cmd_route)

    repair_parser = subparsers.add_parser("repair", help="infer and fix missing workflow-state.json")
    repair_parser.add_argument("task_dir")
    repair_parser.add_argument("--project-root")
    repair_parser.add_argument("--apply", action="store_true")
    repair_parser.set_defaults(func=cmd_repair)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

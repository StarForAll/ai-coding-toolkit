#!/usr/bin/env python3
"""Workflow strong-gate state helper.

This helper manages and validates the task-local workflow-state.json used by the
"新项目开发工作流" strong-gate stage model.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _resolve_trellis_scripts_dir() -> Path:
    for candidate_root in Path(__file__).resolve().parents:
        scripts_dir = candidate_root / ".trellis" / "scripts"
        if (scripts_dir / "common" / "__init__.py").is_file():
            return scripts_dir
    raise RuntimeError("无法定位 Trellis scripts 目录")


TRELLIS_SCRIPTS_DIR = _resolve_trellis_scripts_dir()
if str(TRELLIS_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(TRELLIS_SCRIPTS_DIR))

from common.active_task import (  # type: ignore[import-not-found]
    resolve_active_task,
    resolve_task_ref,
)


STATE_FILE_NAME = "workflow-state.json"
TASK_FILE_NAME = "task.json"
REQUIREMENTS_DIR = Path("docs/requirements")
CUSTOMER_PRD = REQUIREMENTS_DIR / "customer-facing-prd.md"
DEVELOPER_PRD = REQUIREMENTS_DIR / "developer-facing-prd.md"
TASK_PRD = Path("prd.md")
TASK_PLAN_FILE = Path("task_plan.md")
CHECK_MD_FILE = Path("check.md")
FINISH_WORK_CHECKLIST_FILE = Path("finish-work-checklist.md")
TASK_CREATION_CHECKLIST_FILE = Path("task_creation_checklist.md")
DELIVERY_DIR = Path("delivery")
DELIVERY_ARTIFACTS = (
    DELIVERY_DIR / "acceptance.md",
    DELIVERY_DIR / "deliverables.md",
    DELIVERY_DIR / "transfer-checklist.md",
)
ROOT_README = Path("README.md")
ROOT_README_EN = Path("README.en.md")
ASSESSMENT_FILE = Path("assessment.md")
CONTEXT7_REVIEW_FILE = Path("design/context7-review.md")
VALID_ENGAGEMENT_TYPES = {"external_outsourcing", "non_outsourcing"}
MIN_KICKOFF_PAYMENT_RATIO = 30.0
VALID_SOURCE_WATERMARK_LEVELS = {"none", "basic", "hybrid", "forensic"}
EXIT_READY_STATUSES = {"awaiting_user_confirmation", "completed"}
OWNERSHIP_POLICY_FIELDS = (
    "source_watermark_level",
    "source_watermark_channels",
    "zero_width_watermark_enabled",
    "subtle_code_marker_enabled",
    "ownership_proof_required",
)
DESIGN_EXIT_REQUIRED_BLOCKS = {"A", "B", "C", "D"}

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
STAGE_TRANSITIONS: dict[str, list[str]] = {
    "feasibility": ["brainstorm"],
    "brainstorm": ["design", "plan", "implementation", "test-first"],
    "design": ["plan"],
    "plan": ["implementation", "test-first"],
    "implementation": ["test-first", "check", "project-audit"],
    "test-first": ["implementation", "check", "project-audit"],
    "project-audit": ["check", "review-gate"],
    "check": ["review-gate", "implementation", "finish-work"],
    "review-gate": ["finish-work", "implementation"],
    "finish-work": ["delivery"],
    "delivery": ["record-session"],
    "record-session": [],
}
STAGE_STATUSES = {
    "in_progress",
    "blocked",
    "awaiting_user_confirmation",
    "completed",
}
EXECUTION_STAGES = {"implementation", "test-first"}
COORDINATION_STAGES = {"feasibility", "brainstorm", "design", "plan"}
LEAF_REQUIRED_STAGES = STAGES - COORDINATION_STAGES
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
    "total_effort_hours",
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
PLACEHOLDER_MARKERS = ("待补充", "待定", "暂空", "后续补充", "TBD", "TODO", "FIXME", "...")

BRAINSTORM_EXIT_SNAPSHOT_FIELDS = (
    "complexity_decision",
    "ui_lane_decision",
    "cross_platform_scope",
    "estimate_refresh_result",
    "kill_criteria",
    "open_items",
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


def build_default_state(stage: str) -> dict[str, Any]:
    return {
        "version": 1,
        "stage": stage,
        "stage_status": "in_progress",
        "current_block": None,
        "completed_blocks": [],
        "allowed_next_stages": list(STAGE_TRANSITIONS.get(stage, [])),
        "awaiting_user_confirmation": False,
        "last_confirmed_transition": None,
        "notes": [],
        "checkpoints": {
            "architecture_confirmed": False,
            "context7_review_completed": False,
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


def session_runtime_has_any_current_task(repo_root: Path) -> bool:
    sessions_dir = repo_root / ".trellis" / ".runtime" / "sessions"
    if not sessions_dir.is_dir():
        return False
    for session_file in sessions_dir.glob("*.json"):
        session_data = read_json(session_file)
        if not session_data:
            continue
        current_task = session_data.get("current_task")
        if isinstance(current_task, str) and current_task.strip():
            return True
    return False


def resolve_degraded_task_dir(repo_root: Path) -> Path | None:
    if session_runtime_has_any_current_task(repo_root):
        # Degraded fallback is only a last resort when no live session state
        # exists. If any session file already carries a current_task pointer,
        # prefer explicit recovery instead of guessing from a degraded pointer.
        return None
    degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
    degraded = read_json(degraded_path)
    if not degraded:
        return None
    task_ref = degraded.get("current_task")
    if not isinstance(task_ref, str) or not task_ref.strip():
        return None
    resolved = resolve_task_ref(task_ref, repo_root)
    if resolved is None or not resolved.is_dir():
        return None
    return resolved.resolve()


def bool_arg(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool value: {raw}")


def summarize_validator_output(stdout: str, stderr: str) -> str:
    combined = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    if not combined:
        return ""
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    return lines[-1] if lines else combined


def run_gate_validator(
    script_name: str,
    validator_args: list[str],
    errors: list[str],
    *,
    label: str,
    timeout: int = 30,
) -> None:
    script_path = Path(__file__).resolve().parent / script_name
    if not script_path.is_file():
        errors.append(f"缺少 {script_name}；无法执行 {label}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), *validator_args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        errors.append(f"{label} 执行超时")
        return
    except OSError as exc:
        errors.append(f"{label} 执行失败: {exc}")
        return
    if result.returncode == 0:
        return
    summary = summarize_validator_output(result.stdout, result.stderr)
    if summary:
        errors.append(f"{label} 未通过: {summary}")
    else:
        errors.append(f"{label} 未通过")


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
        context7_review_completed = checkpoints.get("context7_review_completed", False)
        if not isinstance(context7_review_completed, bool):
            errors.append("checkpoints.context7_review_completed 必须是布尔值")
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


def transition_payload_is_valid(
    transition: Any,
    *,
    target_stage: str | None = None,
) -> bool:
    if not isinstance(transition, dict):
        return False
    if not isinstance(transition.get("from"), str):
        return False
    if not isinstance(transition.get("to"), str):
        return False
    if not isinstance(transition.get("confirmed_at"), str):
        return False
    if target_stage is not None and transition.get("to") != target_stage:
        return False
    return True


def recover_repair_state(
    candidate_stage: str,
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    repaired = build_default_state(candidate_stage)
    if not isinstance(state, dict) or state.get("stage") != candidate_stage:
        return repaired

    existing_block = state.get("current_block")
    if existing_block is None or isinstance(existing_block, str):
        repaired["current_block"] = existing_block

    existing_completed = state.get("completed_blocks")
    if isinstance(existing_completed, list) and all(isinstance(item, str) for item in existing_completed):
        repaired["completed_blocks"] = existing_completed

    existing_allowed_next = state.get("allowed_next_stages")
    canonical_allowed_next = set(STAGE_TRANSITIONS.get(candidate_stage, []))
    if (
        isinstance(existing_allowed_next, list)
        and all(isinstance(item, str) for item in existing_allowed_next)
        and set(existing_allowed_next).issubset(canonical_allowed_next)
    ):
        repaired["allowed_next_stages"] = existing_allowed_next

    existing_notes = state.get("notes")
    if isinstance(existing_notes, list) and all(isinstance(item, str) for item in existing_notes):
        repaired["notes"] = existing_notes

    if candidate_stage in EXECUTION_STAGES:
        existing_stage_status = state.get("stage_status")
        existing_awaiting = state.get("awaiting_user_confirmation")
        if (
            existing_stage_status in STAGE_STATUSES
            and isinstance(existing_awaiting, bool)
            and (
                (existing_awaiting is True and existing_stage_status == "awaiting_user_confirmation")
                or (existing_awaiting is False and existing_stage_status != "awaiting_user_confirmation")
            )
        ):
            repaired["stage_status"] = existing_stage_status
            repaired["awaiting_user_confirmation"] = existing_awaiting

        existing_checkpoints = state.get("checkpoints")
        if isinstance(existing_checkpoints, dict):
            repaired_checkpoints = repaired.setdefault("checkpoints", {})
            for field_name in (
                "architecture_confirmed",
                "context7_review_completed",
                "execution_authorized",
            ):
                field_value = existing_checkpoints.get(field_name)
                if isinstance(field_value, bool):
                    repaired_checkpoints[field_name] = field_value

        existing_transition = state.get("last_confirmed_transition")
        if transition_payload_is_valid(existing_transition, target_stage=candidate_stage):
            repaired["last_confirmed_transition"] = existing_transition

    return repaired


def apply_repair_overrides(repaired: dict[str, Any], args: argparse.Namespace) -> None:
    if getattr(args, "stage_status", None):
        repaired["stage_status"] = args.stage_status
    if getattr(args, "clear_current_block", False):
        repaired["current_block"] = None
    elif getattr(args, "current_block", None) is not None:
        repaired["current_block"] = args.current_block
    if getattr(args, "completed_blocks", None) is not None:
        repaired["completed_blocks"] = [item for item in args.completed_blocks.split(",") if item]
    if getattr(args, "allowed_next", None) is not None:
        repaired["allowed_next_stages"] = [item for item in args.allowed_next.split(",") if item]
    if getattr(args, "awaiting_user_confirmation", None) is not None:
        repaired["awaiting_user_confirmation"] = args.awaiting_user_confirmation

    checkpoints = repaired.setdefault("checkpoints", {})
    if getattr(args, "architecture_confirmed", None) is not None:
        checkpoints["architecture_confirmed"] = args.architecture_confirmed
    if getattr(args, "context7_review_completed", None) is not None:
        checkpoints["context7_review_completed"] = args.context7_review_completed
    if getattr(args, "execution_authorized", None) is not None:
        checkpoints["execution_authorized"] = args.execution_authorized

    if getattr(args, "clear_last_transition", False):
        repaired["last_confirmed_transition"] = None
    elif getattr(args, "transition_from", None) is not None:
        repaired["last_confirmed_transition"] = {
            "from": args.transition_from,
            "to": repaired.get("stage"),
            "confirmed_at": now_iso(),
        }

    if getattr(args, "note", None):
        notes = repaired.setdefault("notes", [])
        if not isinstance(notes, list):
            notes = []
            repaired["notes"] = notes
        notes.append(args.note)


def validate_plan_gate(task_dir: Path, errors: list[str]) -> None:
    """Validate plan artifacts before entering implementation or test-first."""
    checklist_path = task_dir / TASK_CREATION_CHECKLIST_FILE
    if checklist_path.is_file():
        content = checklist_path.read_text(encoding="utf-8")
        if "`task_creation_confirmed`" in content:
            if not re.search(r'`task_creation_confirmed`\s*[：:]\s*`?yes`?', content):
                errors.append(
                    "task_creation_checklist.md 存在但 task_creation_confirmed 未确认为 yes；"
                    "不得进入执行阶段"
                )
        plan_path = task_dir / TASK_PLAN_FILE
        if not plan_path.is_file():
            errors.append(
                "task_creation_checklist.md 存在但缺少 task_plan.md；"
                "计划产物不完整，不得进入执行阶段"
            )
    run_gate_validator(
        "plan-validate.py",
        [str(task_dir)],
        errors,
        label="plan-validate.py 结构验证",
    )
    run_gate_validator(
        "delivery-control-validate.py",
        ["--phase", "plan", "--task-dir", str(task_dir)],
        errors,
        label="delivery-control-validate.py plan 校验",
    )
    run_gate_validator(
        "ownership-proof-validate.py",
        ["--phase", "plan", "--task-dir", str(task_dir)],
        errors,
        label="ownership-proof-validate.py plan 校验",
    )


def validate_design_exit_gate(task_dir: Path, errors: list[str]) -> None:
    run_gate_validator(
        "ownership-proof-validate.py",
        ["--phase", "design", "--task-dir", str(task_dir)],
        errors,
        label="ownership-proof-validate.py design 校验",
    )


def validate_check_gate(task_dir: Path, errors: list[str]) -> None:
    """Validate check.md exists and has minimum content structure before leaving check stage."""
    check_path = task_dir / CHECK_MD_FILE
    if not check_path.is_file():
        errors.append("缺少 check.md；check 阶段产物未生成，不得进入 review-gate 或 finish-work")
        return
    content = check_path.read_text(encoding="utf-8")
    missing_sections: list[str] = []
    if not re.search(r"^\s*##+\s*(?:Changed Scope|变更范围)\s*$", content, re.MULTILINE):
        missing_sections.append("Changed Scope / 变更范围")
    if not re.search(r"^\s*##+\s*(?:Applied Specs|适用规范)\s*$", content, re.MULTILINE):
        missing_sections.append("Applied Specs / 适用规范")
    if not re.search(r"^\s*##+\s*(?:Verification Results|验证结果)\s*$", content, re.MULTILINE):
        missing_sections.append("Verification Results / 验证结果")
    if not re.search(r"^\s*##+\s*(?:Deviations|偏差清单)\s*$", content, re.MULTILINE):
        missing_sections.append("Deviations / 偏差清单")
    if not re.search(r"^\s*##+\s*(?:Uncovered Risks|未覆盖风险)\s*$", content, re.MULTILINE):
        missing_sections.append("Uncovered Risks / 未覆盖风险")
    if not re.search(r"^\s*##+\s*(?:Suggested Next Step|推荐下一步)\s*$", content, re.MULTILINE):
        missing_sections.append("Suggested Next Step / 推荐下一步")
    if missing_sections:
        errors.append(
            f"check.md 缺少必要章节: {', '.join(missing_sections)}；"
            "check 阶段产物不完整，不得进入 review-gate 或 finish-work"
        )
        return

    if not re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE):
        errors.append(
            "check.md 缺少真实验证结论（pass / fail / not run）；"
            "check 阶段产物不完整，不得进入 review-gate 或 finish-work"
        )


def validate_finish_work_gate(task_dir: Path, errors: list[str]) -> None:
    """Validate frozen close-out evidence before leaving finish-work for delivery."""
    checklist_path = task_dir / FINISH_WORK_CHECKLIST_FILE
    if not checklist_path.is_file():
        errors.append(
            "缺少 finish-work-checklist.md；finish-work 阶段未冻结验证矩阵与收尾证据，不得进入 delivery"
        )
        return

    content = checklist_path.read_text(encoding="utf-8")
    missing_sections: list[str] = []
    if not re.search(r"^\s*##+\s*(?:冻结验证矩阵|Verification Matrix)\s*$", content, re.MULTILINE):
        missing_sections.append("冻结验证矩阵 / Verification Matrix")
    if not re.search(r"Check\s*\|.*Command or Method.*\|.*Result", content, re.IGNORECASE):
        missing_sections.append("Check | Command or Method | Result")
    if not re.search(r"^\s*##+\s*(?:人工验证|Manual Verification)\s*$", content, re.MULTILINE):
        missing_sections.append("人工验证 / Manual Verification")
    if not re.search(r"^\s*##+\s*(?:同步结论|Sync Conclusion)\s*$", content, re.MULTILINE):
        missing_sections.append("同步结论 / Sync Conclusion")
    if missing_sections:
        errors.append(
            f"finish-work-checklist.md 缺少必要内容: {', '.join(missing_sections)}；"
            "finish-work 阶段证据不完整，不得进入 delivery"
        )
        return

    if not re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE):
        errors.append(
            "finish-work-checklist.md 缺少真实验证结论（pass / fail / not run）；"
            "finish-work 阶段证据不完整，不得进入 delivery"
        )
    if not re.search(r"当前状态|status|证据缺口|evidence gap", content, re.IGNORECASE):
        errors.append(
            "finish-work-checklist.md 缺少人工验证真实状态或证据缺口；"
            "finish-work 阶段证据不完整，不得进入 delivery"
        )


def validate_project_audit_gate(task_dir: Path, errors: list[str]) -> None:
    report_path = task_dir / "project-audit.md"
    if not report_path.is_file():
        errors.append("缺少 project-audit.md；project-audit 阶段未沉淀项目级审查结论，不得进入后续阶段")
        return

    content = report_path.read_text(encoding="utf-8")
    missing_sections: list[str] = []
    required_sections = (
        "Mode",
        "Project-Level Verification Matrix",
        "Confirmed Findings",
        "Candidate Findings / Reviewer Evidence",
        "Confirmed Fix Plan",
        "Applied Changes",
        "Project-Level Verification Results",
        "Remaining Risks",
        "Suggested Next Step",
    )
    for section in required_sections:
        if not re.search(rf"^\s*##+\s*{re.escape(section)}\s*$", content, re.MULTILINE):
            missing_sections.append(section)

    if missing_sections:
        errors.append(
            f"project-audit.md 缺少必要章节: {', '.join(missing_sections)}；"
            "project-audit 阶段证据不完整，不得进入后续阶段"
        )


def validate_review_gate_gate(task_dir: Path, errors: list[str]) -> None:
    review_gate_dir = task_dir / "review-gate"
    if not review_gate_dir.is_dir():
        errors.append(
            "缺少 review-gate/ 目录；review-gate 阶段未沉淀本轮判定记录，不得进入后续阶段"
        )
        return

    reports = sorted(review_gate_dir.glob("review-gate-round-*.md"))
    if not reports:
        errors.append(
            "缺少 review-gate/review-gate-round-<N>.md；review-gate 阶段未记录判定结论，不得进入后续阶段"
        )
        return

    content = reports[-1].read_text(encoding="utf-8")
    missing_sections: list[str] = []
    for section in ("Decision", "Trigger Evidence", "Mode", "Recommended Next Step"):
        if not re.search(rf"^\s*##+\s*{re.escape(section)}\s*$", content, re.MULTILINE):
            missing_sections.append(section)

    if missing_sections:
        errors.append(
            f"{reports[-1].relative_to(task_dir).as_posix()} 缺少必要章节: {', '.join(missing_sections)}；"
            "review-gate 阶段证据不完整，不得进入后续阶段"
        )


def validate_record_session_gate(task_dir: Path, errors: list[str]) -> None:
    validate_delivery_gate(task_dir, errors)


def validate_delivery_gate(task_dir: Path, errors: list[str], repo_root: Path | None = None) -> None:
    """Validate delivery artifacts before entering record-session."""
    missing = [
        artifact.as_posix()
        for artifact in DELIVERY_ARTIFACTS
        if not (task_dir / artifact).is_file()
    ]
    if missing:
        errors.append(
            f"缺少交付产物: {', '.join(missing)}；delivery 阶段未完成，不得进入 record-session"
        )
    # Outsourcing-specific delivery artifact checks
    if repo_root is not None:
        assessment_path = find_assessment_file(task_dir, repo_root)
        if assessment_path is not None:
            assessment_content = assessment_path.read_text(encoding="utf-8")
            engagement = extract_backticked_field(assessment_content, "project_engagement_type")
            if engagement == "external_outsourcing":
                outsourcing_artifacts = [
                    (Path("delivery") / "ownership-proof.md", "ownership-proof.md"),
                    (Path("delivery") / "source-watermark-verification.md", "source-watermark-verification.md"),
                ]
                missing_outsourcing = [
                    label for artifact_path, label in outsourcing_artifacts
                    if not (task_dir / artifact_path).is_file()
                ]
                if missing_outsourcing:
                    errors.append(
                        f"外包项目缺少交付产物: {', '.join(missing_outsourcing)}；"
                        "delivery 阶段未完成，不得进入 record-session"
                    )
    run_gate_validator(
        "delivery-control-validate.py",
        ["--phase", "delivery", "--task-dir", str(task_dir)],
        errors,
        label="delivery-control-validate.py delivery 校验",
    )
    run_gate_validator(
        "ownership-proof-validate.py",
        ["--phase", "delivery", "--task-dir", str(task_dir)],
        errors,
        label="ownership-proof-validate.py delivery 校验",
    )
    if repo_root is not None:
        assessment_path = find_assessment_file(task_dir, repo_root)
        if assessment_path is not None:
            content = assessment_path.read_text(encoding="utf-8")
            ownership_required = normalize_yes_no_field(
                extract_backticked_field(content, "ownership_proof_required")
            )
            level = extract_backticked_field(content, "source_watermark_level")
            level_normalized = level.lower() if isinstance(level, str) else None
            if ownership_required is True and level_normalized not in {None, "none"}:
                run_gate_validator(
                    "source-watermark-guard.py",
                    ["--task-dir", str(task_dir), "--mode", "check"],
                    errors,
                    label="source-watermark-guard.py 保持性校验",
                )


def validate_stage_transition_gates(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
    new_stage: str,
    errors: list[str],
) -> None:
    """Validate gate requirements when transitioning to a new stage via set."""
    if new_stage in {"feasibility"}:
        return
    validate_leaf_task(task_dir, new_stage, errors)

    current_stage = state.get("stage")
    canonical_next = STAGE_TRANSITIONS.get(current_stage, [])
    if current_stage is not None and new_stage != current_stage and new_stage not in canonical_next:
        errors.append(
            f"阶段切换被拒绝: {current_stage!r} → {new_stage!r} 不属于 canonical transition {canonical_next}"
        )
        return

    candidate_state = json.loads(json.dumps(state, ensure_ascii=False))
    candidate_state["stage"] = new_stage
    if "allowed_next_stages" not in candidate_state or not isinstance(
        candidate_state.get("allowed_next_stages"), list
    ):
        candidate_state["allowed_next_stages"] = list(STAGE_TRANSITIONS.get(new_stage, []))

    # Stages >= brainstorm require external project controls and ownership policy
    if new_stage in STAGES - {"feasibility"}:
        gate_errors: list[str] = []
        validate_external_project_controls(
            task_dir,
            repo_root,
            candidate_state,
            gate_errors,
            target_stage=new_stage,
        )
        validate_ownership_policy_controls(task_dir, repo_root, state, gate_errors)

        errors.extend(gate_errors)

    # Stages >= design additionally require project doc boundary
    if new_stage in PROJECT_ESTIMATE_REQUIRED_STAGES:
        validate_project_doc_boundary(candidate_state, repo_root, task_dir, errors)

    if state.get("stage") == "brainstorm":
        validate_brainstorm_exit_gate(state, repo_root, task_dir, errors)

    if state.get("stage") == "design" and new_stage == "plan":
        validate_design_exit_gate(task_dir, errors)

    # Only the explicit plan → execution exit requires plan artifacts.
    if new_stage in EXECUTION_STAGES and state.get("stage") == "plan":
        validate_plan_gate(task_dir, errors)

    # Check → finish-work/review-gate requires check.md
    if new_stage in {"finish-work", "review-gate"}:
        validate_check_gate(task_dir, errors)

    if current_stage == "project-audit":
        validate_project_audit_gate(task_dir, errors)

    if current_stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)

    # Finish-work → delivery requires the frozen close-out checklist
    if new_stage == "delivery":
        validate_finish_work_gate(task_dir, errors)

    # Delivery → record-session requires delivery artifacts
    if new_stage == "record-session":
        validate_delivery_gate(task_dir, errors, repo_root)


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


def validate_session_active_task(task_dir: Path, repo_root: Path, errors: list[str]) -> None:
    active = resolve_active_task(repo_root)
    source_label = "Trellis session runtime"
    if not active.task_path:
        resolved_active = resolve_degraded_task_dir(repo_root)
        source_label = "degraded active-task fallback"
        if resolved_active is None:
            errors.append("无法从 Trellis session runtime 或 degraded fallback 解析当前活动任务")
            return
    else:
        if active.stale:
            errors.append(f"Trellis session runtime 中的当前活动任务已失效: {active.task_path}")
            return
        resolved_active = resolve_task_ref(active.task_path, repo_root)
        if resolved_active is None:
            errors.append(f"无法解析当前活动任务路径: {active.task_path}")
            return

    if resolved_active.resolve() != task_dir.resolve():
        expected = task_dir.resolve().relative_to(repo_root).as_posix()
        actual = resolved_active.resolve().relative_to(repo_root).as_posix()
        errors.append(
            f"{source_label} 指向 {actual}，与当前 task {expected} 不一致"
        )


def stage_requires_leaf(stage: str | None) -> bool:
    return isinstance(stage, str) and stage in LEAF_REQUIRED_STAGES


def validate_leaf_task(task_dir: Path, stage: str | None, errors: list[str]) -> None:
    if not stage_requires_leaf(stage):
        return
    task_data = read_json(task_dir / TASK_FILE_NAME)
    if not task_data:
        errors.append("task.json 无法读取")
        return
    children = task_data.get("children", [])
    if isinstance(children, list) and children:
        errors.append("当前 task 已有 children，不应继续作为执行态叶子任务持有 workflow-state")


def collect_dependency_blockers(task_dir: Path, repo_root: Path) -> list[str]:
    task_data = load_task_json(task_dir)
    if not task_data:
        return []
    meta = task_data.get("meta")
    if not isinstance(meta, dict):
        return []
    depends_on = meta.get("depends_on")
    if not isinstance(depends_on, list):
        return []

    blockers: list[str] = []
    tasks_root = repo_root / ".trellis" / "tasks"
    for item in depends_on:
        if not isinstance(item, str) or not item.strip():
            continue
        dep_dir = tasks_root / item.strip()
        dep_task = load_task_json(dep_dir)
        if dep_task is None:
            blockers.append(f"前置依赖任务不存在或不可读: {item}")
            continue
        dep_status = dep_task.get("status")
        if dep_status != "completed":
            blockers.append(f"前置依赖任务未完成: {item} (status={dep_status})")
    return blockers


def collect_route_readiness_blockers(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> list[str]:
    stage = state.get("stage")
    blockers: list[str] = []

    if stage == "brainstorm":
        assessment_file = find_assessment_file(task_dir, repo_root)
        if assessment_file is None:
            if not is_personal_brainstorm_bootstrap_allowed(task_dir, repo_root, state):
                blockers.append("缺少 assessment.md；必须先完成 feasibility 才允许继续 brainstorm")
        else:
            content = assessment_file.read_text(encoding="utf-8")
            allow_line_present = False
            allow_brainstorm = False
            for line in content.splitlines():
                if "是否允许进入 brainstorm" in line:
                    allow_line_present = True
                    if "是" in line or "`yes`" in line or ": yes" in line.lower():
                        allow_brainstorm = True
                    break
            if not allow_line_present:
                blockers.append("assessment.md 缺少“是否允许进入 brainstorm”字段")
            elif not allow_brainstorm:
                blockers.append("assessment.md 未明确允许进入 brainstorm")

        task_prd = task_dir / TASK_PRD
        if not task_prd.is_file():
            blockers.append("当前 brainstorm task 缺少 prd.md 工作底稿")

    if stage == "plan":
        task_prd = task_dir / TASK_PRD
        if not task_prd.is_file():
            blockers.append("当前推荐执行任务说明卡缺少最小 prd.md，不能继续进入后续路由")
        design_dir = task_dir / "design"
        if design_dir.is_dir() and not (repo_root / ROOT_README_EN).is_file():
            blockers.append("design 已落盘但项目根 README.en.md 缺失；需先补齐 design 阶段块 C 英文文档")

    if stage in EXECUTION_STAGES:
        task_prd = task_dir / TASK_PRD
        if not task_prd.is_file():
            blockers.append("当前推荐执行任务说明卡缺少最小 prd.md，不能进入执行态")
        elif find_missing_markers(task_prd, TASK_ESTIMATE_MARKERS):
            blockers.append("当前推荐执行任务说明卡缺少项目级粗估字段，不能进入执行态")
        blockers.extend(collect_dependency_blockers(task_dir, repo_root))

    return blockers


def collect_exit_gate_blockers(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> list[str]:
    """Check exit-gate completeness when a stage is awaiting_user_confirmation.

    These blockers indicate the stage's exit requirements are not yet met, even
    though the stage_status has been set to awaiting_user_confirmation. They are
    only evaluated when the route is deciding whether to report 'awaiting_confirmation'
    so that the AI/user receives accurate readiness signals rather than a false OK.
    """
    stage = state.get("stage")
    blockers: list[str] = []

    if stage == "check":
        validate_check_gate(task_dir, blockers)

    elif stage == "plan":
        validate_plan_gate(task_dir, blockers)

    elif stage == "finish-work":
        validate_finish_work_gate(task_dir, blockers)

    elif stage == "delivery":
        validate_delivery_gate(task_dir, blockers, repo_root)

    elif stage == "project-audit":
        validate_project_audit_gate(task_dir, blockers)

    elif stage == "review-gate":
        validate_review_gate_gate(task_dir, blockers)

    elif stage == "record-session":
        validate_record_session_gate(task_dir, blockers)

    elif stage == "design":
        validate_project_doc_boundary(state, repo_root, task_dir, blockers)
        validate_context7_review_artifact(task_dir, state, blockers)
        validate_design_exit_gate(task_dir, blockers)

    elif stage == "brainstorm":
        allowed_targets = design_path_candidates_from_state(state)
        validate_brainstorm_exit_gate(
            state,
            repo_root,
            task_dir,
            blockers,
            require_exit_snapshot=True,
            require_customer_prd=bool(allowed_targets & {"design", "plan"}),
        )

    return blockers


def validate_stage_exit_artifacts(
    task_dir: Path,
    repo_root: Path | None,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    if repo_root is None:
        return

    stage = state.get("stage")
    if stage == "brainstorm":
        validate_brainstorm_exit_gate(
            state,
            repo_root,
            task_dir,
            errors,
            require_exit_snapshot=state.get("stage_status") in EXIT_READY_STATUSES,
            require_customer_prd=False,
        )
    elif stage == "plan":
        validate_plan_gate(task_dir, errors)
    elif stage == "check":
        validate_check_gate(task_dir, errors)
    elif stage == "finish-work":
        validate_finish_work_gate(task_dir, errors)
    elif stage == "project-audit":
        validate_project_audit_gate(task_dir, errors)
    elif stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)
    elif stage == "delivery":
        validate_delivery_gate(task_dir, errors, repo_root)


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


def is_personal_brainstorm_bootstrap_allowed(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> bool:
    """Whether personal-profile brainstorm may bootstrap assessment in place."""
    if state.get("stage") != "brainstorm":
        return False
    if state.get("stage_status") != "in_progress":
        return False
    if find_assessment_file(task_dir, repo_root) is not None:
        return False

    install_record = read_json(repo_root / INSTALL_RECORD)
    return isinstance(install_record, dict) and install_record.get("profile") == "personal"


def extract_backticked_field(content: str, field_name: str) -> str | None:
    pattern = re.compile(rf'`{re.escape(field_name)}`:\s*`?(.+?)`?(?:\n|$)')
    match = pattern.search(content)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def normalize_yes_no_field(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().strip("`").lower()
    if lowered in {"yes", "true", "on", "1", "是"}:
        return True
    if lowered in {"no", "false", "off", "0", "否"}:
        return False
    return None


def parse_channels(raw: str | None) -> set[str]:
    if not raw:
        return set()
    parts = re.split(r"[,\uFF0C/\s]+", raw.lower())
    channels = {part for part in parts if part}
    normalized = set()
    for channel in channels:
        if channel in {"visible", "可见", "可见水印", "comment", "comments"}:
            normalized.add("visible")
        elif channel in {"zero-width", "zero", "zw", "零宽", "zero_width"}:
            normalized.add("zero-width")
        elif channel in {"subtle", "subtle-marker", "subtle-markers", "marker", "markers", "隐蔽", "不起眼"}:
            normalized.add("subtle-markers")
        elif channel in {"zero-watermark", "zero-watermarks", "fingerprint", "fingerprints", "零水印", "指纹"}:
            normalized.add("zero-watermark")
        else:
            normalized.add(channel)
    return normalized


def is_placeholder_like(text: str | None) -> bool:
    if text is None:
        return True
    normalized = text.strip().lstrip("-").strip().strip("`*_ \t\r\n")
    if not normalized:
        return True
    lowered = normalized.lower()
    for marker in PLACEHOLDER_MARKERS:
        lowered_marker = marker.lower()
        if not lowered.startswith(lowered_marker):
            continue
        if len(lowered) == len(lowered_marker):
            return True
        next_char = normalized[len(marker)]
        if next_char.isspace():
            return True
        if unicodedata.category(next_char).startswith("P"):
            return True
    return False


def normalize_design_block_name(raw: str) -> str | None:
    normalized = raw.strip().lower().replace("_", "-")
    mapping = {
        "a": "A",
        "block-a": "A",
        "块a": "A",
        "块 a": "A",
        "developer-facing-prd": "A",
        "developer-facing-prd.md": "A",
        "b": "B",
        "block-b": "B",
        "块b": "B",
        "块 b": "B",
        "design-docs": "B",
        "c": "C",
        "block-c": "C",
        "块c": "C",
        "块 c": "C",
        "project-docs": "C",
        "readme": "C",
        "d": "D",
        "block-d": "D",
        "块d": "D",
        "块 d": "D",
        "engineering-alignment": "D",
        "spec-alignment": "D",
    }
    return mapping.get(normalized)


def design_exit_ready(state: dict[str, Any]) -> bool:
    if state.get("stage") != "design":
        return False
    completed_blocks = state.get("completed_blocks")
    if not isinstance(completed_blocks, list):
        return False
    normalized_blocks = {
        normalized
        for item in completed_blocks
        if isinstance(item, str)
        for normalized in [normalize_design_block_name(item)]
        if normalized is not None
    }
    return DESIGN_EXIT_REQUIRED_BLOCKS.issubset(normalized_blocks)


def validate_external_project_controls(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
    errors: list[str],
    *,
    target_stage: str | None = None,
) -> None:
    stage = target_stage if target_stage is not None else state.get("stage")
    assessment_file = find_assessment_file(task_dir, repo_root)
    if assessment_file is None:
        if (
            target_stage is None
            and is_personal_brainstorm_bootstrap_allowed(task_dir, repo_root, state)
        ):
            return
        errors.append("缺少 assessment.md；任何项目都必须先经过 feasibility 并完成项目类别判断")
        return

    content = assessment_file.read_text(encoding="utf-8")
    legal_match = re.search(r'法律(?:/|与)?合规风险结论[：:]\s*(\S+)', content)
    if not legal_match:
        errors.append(f"{assessment_file.relative_to(repo_root).as_posix()} 缺少 `法律/合规风险结论` 字段")
    else:
        legal_value = legal_match.group(1)
        if legal_value not in {"通过", "不通过", "待补充"}:
            errors.append(
                f"{assessment_file.relative_to(repo_root).as_posix()} 的 `法律/合规风险结论` 值异常: {legal_value}"
            )

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


def validate_ownership_policy_controls(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    assessment_file = find_assessment_file(task_dir, repo_root)
    if assessment_file is None:
        if is_personal_brainstorm_bootstrap_allowed(task_dir, repo_root, state):
            return
        return

    content = assessment_file.read_text(encoding="utf-8")
    rel_path = assessment_file.relative_to(repo_root).as_posix()

    level = extract_backticked_field(content, "source_watermark_level")
    if level is None:
        errors.append(f"{rel_path} 缺少 `source_watermark_level` 字段")
        level_normalized = None
    else:
        level_normalized = level.lower()
        if level_normalized not in VALID_SOURCE_WATERMARK_LEVELS:
            errors.append(f"{rel_path} 的 `source_watermark_level` 取值无效: {level}")

    channels_raw = extract_backticked_field(content, "source_watermark_channels")
    if channels_raw is None:
        errors.append(f"{rel_path} 缺少 `source_watermark_channels` 字段")
        channels = set()
    elif is_placeholder_like(channels_raw):
        errors.append(f"{rel_path} 的 `source_watermark_channels` 未填写具体值")
        channels = set()
    else:
        channels = parse_channels(channels_raw)
        if not channels:
            errors.append(f"{rel_path} 的 `source_watermark_channels` 不能为空")

    zero_width_raw = extract_backticked_field(content, "zero_width_watermark_enabled")
    zero_width_enabled = normalize_yes_no_field(zero_width_raw)
    if zero_width_raw is None:
        errors.append(f"{rel_path} 缺少 `zero_width_watermark_enabled` 字段")
    elif zero_width_enabled is None:
        errors.append(f"{rel_path} 的 `zero_width_watermark_enabled` 只能填写 `yes` / `no`")

    subtle_raw = extract_backticked_field(content, "subtle_code_marker_enabled")
    subtle_enabled = normalize_yes_no_field(subtle_raw)
    if subtle_raw is None:
        errors.append(f"{rel_path} 缺少 `subtle_code_marker_enabled` 字段")
    elif subtle_enabled is None:
        errors.append(f"{rel_path} 的 `subtle_code_marker_enabled` 只能填写 `yes` / `no`")

    ownership_raw = extract_backticked_field(content, "ownership_proof_required")
    ownership_required = normalize_yes_no_field(ownership_raw)
    if ownership_raw is None:
        errors.append(f"{rel_path} 缺少 `ownership_proof_required` 字段")
    elif ownership_required is None:
        errors.append(f"{rel_path} 的 `ownership_proof_required` 只能填写 `yes` / `no`")

    if zero_width_enabled is True and "zero-width" not in channels:
        errors.append(
            f"{rel_path} 已启用 `zero_width_watermark_enabled`，但 `source_watermark_channels` 未包含 `zero-width`"
        )
    if subtle_enabled is True and "subtle-markers" not in channels:
        errors.append(
            f"{rel_path} 已启用 `subtle_code_marker_enabled`，但 `source_watermark_channels` 未包含 `subtle-markers`"
        )
    if ownership_required is True:
        if level_normalized == "none":
            errors.append(f"{rel_path} 的 `ownership_proof_required = yes` 时，`source_watermark_level` 不能为 `none`")
        if "visible" not in channels:
            errors.append(
                f"{rel_path} 的 `ownership_proof_required = yes` 时，`source_watermark_channels` 必须包含 `visible`"
            )

def find_missing_markers(path: Path, markers: tuple[str, ...]) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return list(markers)
    return [marker for marker in markers if marker not in content]


def design_path_candidates_from_state(state: dict[str, Any]) -> set[str]:
    allowed_next = state.get("allowed_next_stages")
    if not isinstance(allowed_next, list):
        return set()
    return {item for item in allowed_next if isinstance(item, str)}


def validate_brainstorm_exit_gate(
    state: dict[str, Any],
    project_root: Path,
    task_dir: Path,
    errors: list[str],
    *,
    require_exit_snapshot: bool = True,
    require_customer_prd: bool = True,
) -> None:
    validate_external_project_controls(task_dir, project_root, state, errors)
    validate_ownership_policy_controls(task_dir, project_root, state, errors)

    task_prd = task_dir / TASK_PRD
    if not task_prd.is_file():
        errors.append(f"缺少 {TASK_PRD.as_posix()}；brainstorm 退出前不满足工作底稿门禁")
        return

    missing_task_markers = find_missing_markers(task_prd, TASK_ESTIMATE_MARKERS)
    if missing_task_markers:
        errors.append(
            f"{TASK_PRD.as_posix()} 缺少项目级粗估字段: {', '.join(missing_task_markers)}"
        )

    task_content = task_prd.read_text(encoding="utf-8")
    if require_exit_snapshot:
        missing_snapshot = [
            field for field in BRAINSTORM_EXIT_SNAPSHOT_FIELDS if f"`{field}`" not in task_content
        ]
        if missing_snapshot:
            errors.append(
                f"{TASK_PRD.as_posix()} 缺少阶段出口快照字段: {', '.join(missing_snapshot)}"
            )

    allowed_targets = design_path_candidates_from_state(state)
    if require_customer_prd and allowed_targets & {"design", "plan"}:
        customer_prd = project_root / CUSTOMER_PRD
        if not customer_prd.is_file():
            errors.append(f"缺少 {CUSTOMER_PRD.as_posix()}，当前 brainstorm 退出不满足 design/plan 正式文档门禁")
        else:
            missing_customer_markers = find_missing_markers(customer_prd, CUSTOMER_ESTIMATE_MARKERS)
            if missing_customer_markers:
                errors.append(
                    f"{CUSTOMER_PRD.as_posix()} 缺少项目级粗估摘要字段: {', '.join(missing_customer_markers)}"
                )


def validate_context7_review_artifact(
    task_dir: Path,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    checkpoints = state.get("checkpoints", {})
    architecture_confirmed = checkpoints.get("architecture_confirmed", False)
    context7_review_completed = checkpoints.get("context7_review_completed", False)
    stage = state.get("stage")
    final_design_exit = design_exit_ready(state) and state.get("stage_status") in EXIT_READY_STATUSES

    if stage == "plan":
        should_enforce = True
    else:
        should_enforce = stage == "design" and final_design_exit and architecture_confirmed is True

    if not should_enforce:
        return

    review_path = task_dir / CONTEXT7_REVIEW_FILE
    if not review_path.is_file():
        errors.append(f"缺少 {CONTEXT7_REVIEW_FILE.as_posix()}；未完成 Context7 spec 复核留痕")
        return

    if context7_review_completed is not True:
        errors.append("进入 plan 或退出 design 前，checkpoints.context7_review_completed 必须为 true")

    required_fields = (
        "`context7_review_completed`",
        "`review_scope`",
        "`review_summary`",
        "`blocking_findings`",
        "`open_items`",
    )
    content = review_path.read_text(encoding="utf-8")
    missing_fields = [field for field in required_fields if field not in content]
    if missing_fields:
        errors.append(
            f"{CONTEXT7_REVIEW_FILE.as_posix()} 缺少结构化字段: {', '.join(missing_fields)}"
        )
        return

    review_completed_value = normalize_yes_no_field(extract_backticked_field(content, "context7_review_completed"))
    if review_completed_value is not True:
        errors.append(
            f"{CONTEXT7_REVIEW_FILE.as_posix()} 的 `context7_review_completed` 必须为 `yes`"
        )

    for field_name in ("review_scope", "review_summary", "blocking_findings", "open_items"):
        field_value = extract_backticked_field(content, field_name)
        if is_placeholder_like(field_value):
            errors.append(
                f"{CONTEXT7_REVIEW_FILE.as_posix()} 的 `{field_name}` 未填写具体结论"
            )


def validate_project_doc_boundary(
    state: dict[str, Any],
    project_root: Path,
    task_dir: Path,
    errors: list[str],
) -> None:
    stage = state.get("stage")
    checkpoints = state.get("checkpoints", {})
    architecture_confirmed = checkpoints.get("architecture_confirmed", False)
    final_design_exit = design_exit_ready(state) and state.get("stage_status") in EXIT_READY_STATUSES

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

    if final_design_exit and architecture_confirmed is not True:
        errors.append("design 退出前必须先完成技术架构确认，不能在 architecture_confirmed=false 时等待用户确认")

    if final_design_exit and architecture_confirmed is True and not developer_prd.is_file():
        errors.append("design 退出前缺少 docs/requirements/developer-facing-prd.md；块 A 尚未真正完成")

    if final_design_exit and not (project_root / ROOT_README).is_file():
        errors.append("design 退出前缺少项目根 README.md；块 C 尚未真正完成")

    if final_design_exit and not (project_root / ROOT_README_EN).is_file():
        errors.append("design 退出前缺少项目根 README.en.md；块 C 的英文补充版尚未真正完成")

    validate_context7_review_artifact(task_dir, state, errors)


def build_pending_state_for_set(
    state: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    pending = json.loads(json.dumps(state, ensure_ascii=False))
    current_stage = pending.get("stage", "")
    pending_stage = args.stage if args.stage else current_stage

    pending["stage"] = pending_stage
    if current_stage in EXECUTION_STAGES and pending_stage not in EXECUTION_STAGES:
        checkpoints = pending.setdefault("checkpoints", {})
        checkpoints["execution_authorized"] = False
    if args.stage_status:
        pending["stage_status"] = args.stage_status
    if args.clear_current_block:
        pending["current_block"] = None
    elif args.current_block is not None:
        pending["current_block"] = args.current_block
    if args.completed_blocks is not None:
        pending["completed_blocks"] = [item for item in args.completed_blocks.split(",") if item]
    if args.allowed_next is not None:
        pending["allowed_next_stages"] = [item for item in args.allowed_next.split(",") if item]
    if args.awaiting_user_confirmation is not None:
        pending["awaiting_user_confirmation"] = args.awaiting_user_confirmation
    if args.architecture_confirmed is not None:
        checkpoints = pending.setdefault("checkpoints", {})
        checkpoints["architecture_confirmed"] = args.architecture_confirmed
    if args.context7_review_completed is not None:
        checkpoints = pending.setdefault("checkpoints", {})
        checkpoints["context7_review_completed"] = args.context7_review_completed
    if args.execution_authorized is not None:
        checkpoints = pending.setdefault("checkpoints", {})
        checkpoints["execution_authorized"] = args.execution_authorized
    if args.clear_last_transition:
        pending["last_confirmed_transition"] = None
    elif args.transition_from is not None:
        pending["last_confirmed_transition"] = {
            "from": args.transition_from,
            "to": pending_stage,
            "confirmed_at": now_iso(),
        }
    if args.note:
        notes = pending.setdefault("notes", [])
        if not isinstance(notes, list):
            notes = []
            pending["notes"] = notes
        notes.append(args.note)

    return pending


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

    current_stage = state.get("stage", "")
    pending_state = build_pending_state_for_set(state, args)
    pending_stage = pending_state.get("stage", current_stage)

    if args.stage:
        if pending_stage != current_stage and not args.force:
            # 1. allowed_next_stages gate
            allowed = state.get("allowed_next_stages", [])
            if isinstance(allowed, list) and pending_stage not in allowed:
                print(f"❌ 阶段切换被拒绝: {current_stage!r} → {pending_stage!r} 不在 allowed_next_stages {allowed} 中；如需强制切换请使用 --force")
                return 1
            canonical_next = STAGE_TRANSITIONS.get(current_stage, [])
            if pending_stage not in canonical_next:
                print(
                    f"❌ 阶段切换被拒绝: {current_stage!r} → {pending_stage!r} 不属于 canonical transition {canonical_next}；如需强制切换请使用 --force"
                )
                return 1
            # 2. awaiting_user_confirmation gate for all non-trivial stage transitions
            if pending_stage not in {"feasibility"}:
                current_status = state.get("stage_status", "")
                if current_status != "awaiting_user_confirmation":
                    print(f"❌ 阶段切换被拒绝: 进入 {pending_stage!r} 前 stage_status 必须为 awaiting_user_confirmation；当前为 {current_status!r}。如需强制切换请使用 --force")
                    return 1
            # 3. execution_authorized gate for execution stages
            if pending_stage in EXECUTION_STAGES:
                checkpoints = pending_state.get("checkpoints", {})
                pending_ea = checkpoints.get("execution_authorized", False)
                if pending_ea is not True:
                    print(f"❌ 阶段切换被拒绝: 进入 {pending_stage!r} 前 checkpoints.execution_authorized 必须为 true（可在同一命令中通过 --execution-authorized true 设置）。如需强制切换请使用 --force")
                    return 1
            # 4. Stage transition gate validation (external project controls, ownership, doc boundary)
            repo_root = find_repo_root(task_dir)
            if repo_root is not None:
                gate_errors: list[str] = []
                validate_stage_transition_gates(task_dir, repo_root, pending_state, pending_stage, gate_errors)
                if gate_errors:
                    for message in gate_errors:
                        print(f"❌ {message}")
                    print("❌ 阶段切换被拒绝: 门禁产物未齐；如需强制切换请使用 --force")
                    return 1

    set_errors: list[str] = []
    validate_state_shape(pending_state, set_errors)
    validate_execution_boundary(pending_state, set_errors)
    validate_leaf_task(task_dir, pending_state.get("stage"), set_errors)
    if set_errors:
        for message in set_errors:
            print(f"❌ {message}")
        print("❌ 拒绝写入非法 workflow-state；请一次性完成合法的阶段切换参数")
        return 1

    pending_state["updated_at"] = now_iso()
    write_json(state_path, pending_state)
    print(f"✅ 已更新 {state_path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        task_dir = resolve_task_dir(args.task_dir)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        return 1
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

    should_check_active_task = args.require_active_task_check
    if should_check_active_task:
        if repo_root is None:
            errors.append("无法定位 repo root，不能校验当前活动任务")
        else:
            validate_session_active_task(task_dir, repo_root, errors)
    if repo_root is not None:
        validate_leaf_task(task_dir, state.get("stage"), errors)
        validate_external_project_controls(task_dir, repo_root, state, errors)
        validate_ownership_policy_controls(task_dir, repo_root, state, errors)
        validate_stage_exit_artifacts(task_dir, repo_root, state, errors)

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
CRITICAL_RUNTIME_PATCH_NAMES = (
    "inject-workflow-state",
    "session-start-strong-gate",
    "task-start-strong-gate",
    "task-create-preserve-active",
    "workflow-phase-strong-gate",
)
INJECT_WORKFLOW_STATE_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-state-json]"
OPENCODE_INJECT_WORKFLOW_STATE_PATCH_MARKER = "// [workflow-embed-patch:prefer-workflow-state-json]"
SESSION_START_STRONG_GATE_PATCH_MARKER = "# strong-gate-session-start-patch-applied"
OPENCODE_SESSION_UTILS_PATCH_MARKER = "// [workflow-embed-patch:strong-gate-session-utils]"
TASK_START_STRONG_GATE_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"
TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"
WORKFLOW_PHASE_STRONG_GATE_PATCH_MARKER = "# strong-gate-phase-patch-applied"


def _load_install_record_data(install_record: Path) -> dict[str, Any]:
    data = read_json(install_record)
    return data if isinstance(data, dict) else {}


def _install_record_cli_types(record: dict[str, Any]) -> set[str]:
    cli_types = record.get("cli_types")
    if not isinstance(cli_types, list):
        return set()
    return {str(item) for item in cli_types if isinstance(item, str)}


def _expected_critical_runtime_patches(record: dict[str, Any]) -> set[str]:
    configured = record.get("critical_runtime_patches")
    if isinstance(configured, list):
        return {
            str(item)
            for item in configured
            if isinstance(item, str) and item in CRITICAL_RUNTIME_PATCH_NAMES
        }
    return set(CRITICAL_RUNTIME_PATCH_NAMES)


def _critical_patch_paths(repo_root: Path, cli_types: set[str]) -> list[tuple[str, Path, str]]:
    checks = [
        ("task-start-strong-gate", repo_root / ".trellis" / "scripts" / "task.py", TASK_START_STRONG_GATE_PATCH_MARKER),
        (
            "task-create-preserve-active",
            repo_root / ".trellis" / "scripts" / "common" / "task_store.py",
            TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER,
        ),
        (
            "workflow-phase-strong-gate",
            repo_root / ".trellis" / "scripts" / "common" / "workflow_phase.py",
            WORKFLOW_PHASE_STRONG_GATE_PATCH_MARKER,
        ),
    ]
    if "claude" in cli_types:
        checks.extend(
            [
                (
                    "inject-workflow-state",
                    repo_root / ".claude" / "hooks" / "inject-workflow-state.py",
                    INJECT_WORKFLOW_STATE_PATCH_MARKER,
                ),
                (
                    "session-start-strong-gate",
                    repo_root / ".claude" / "hooks" / "session-start.py",
                    SESSION_START_STRONG_GATE_PATCH_MARKER,
                ),
            ]
        )
    if "codex" in cli_types:
        checks.extend(
            [
                (
                    "inject-workflow-state",
                    repo_root / ".codex" / "hooks" / "inject-workflow-state.py",
                    INJECT_WORKFLOW_STATE_PATCH_MARKER,
                ),
            ]
        )
    if "opencode" in cli_types:
        checks.extend(
            [
                (
                    "inject-workflow-state",
                    repo_root / ".opencode" / "plugins" / "inject-workflow-state.js",
                    OPENCODE_INJECT_WORKFLOW_STATE_PATCH_MARKER,
                ),
                (
                    "session-start-strong-gate",
                    repo_root / ".opencode" / "lib" / "session-utils.js",
                    OPENCODE_SESSION_UTILS_PATCH_MARKER,
                ),
            ]
        )
    return checks


def _python_compile_error(
    repo_root: Path,
    path: Path,
    patch_name: str,
    content: str,
) -> str | None:
    if path.suffix != ".py":
        return None
    try:
        compile(content, str(path), "exec")
    except SyntaxError as exc:
        detail = exc.msg
        if exc.lineno is not None:
            detail = f"{detail} @ line {exc.lineno}"
        return (
            f"{path.relative_to(repo_root)} 无法编译"
            f"（critical runtime patch: {patch_name}; {exc.__class__.__name__}: {detail}）"
        )
    return None


def _detect_missing_critical_runtime_patches(repo_root: Path, record: dict[str, Any]) -> list[str]:
    expected = _expected_critical_runtime_patches(record)
    if not expected:
        return []
    cli_types = _install_record_cli_types(record)
    missing: list[str] = []
    for patch_name, path, marker in _critical_patch_paths(repo_root, cli_types):
        if patch_name not in expected:
            continue
        if not path.is_file():
            missing.append(f"{path.relative_to(repo_root)} 缺失（critical runtime patch: {patch_name}）")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            missing.append(f"{path.relative_to(repo_root)} 不可读（critical runtime patch: {patch_name}）")
            continue
        if marker not in content:
            missing.append(f"{path.relative_to(repo_root)} 缺少补丁标记（critical runtime patch: {patch_name}）")
            continue
        compile_error = _python_compile_error(repo_root, path, patch_name, content)
        if compile_error is not None:
            missing.append(compile_error)
    return missing


def _detect_missing_patched_codex_skills(repo_root: Path, record: dict[str, Any]) -> list[str]:
    configured = record.get("patched_codex_skills")
    if not isinstance(configured, list):
        return []

    problems: list[str] = []
    shared_skills_dir = repo_root / ".agents" / "skills"
    for skill_name in configured:
        if not isinstance(skill_name, str):
            continue
        target = shared_skills_dir / skill_name / "SKILL.md"
        if not target.is_file():
            problems.append(f"{target.relative_to(repo_root)} 缺失（patched codex skill: {skill_name}）")
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{target.relative_to(repo_root)} 不可读（patched codex skill: {skill_name}）")
            continue
        if skill_name == "trellis-start" and "## Workflow Phase Router Patch `[AI]`" not in content:
            problems.append(
                f"{target.relative_to(repo_root)} 缺少强门禁 Phase Router 补丁（patched codex skill: trellis-start）"
            )
    return problems


def detect_embed_invalid(repo_root: Path) -> str | None:
    install_record = repo_root / INSTALL_RECORD
    if not install_record.is_file():
        return None
    record = _load_install_record_data(install_record)

    library_lock = repo_root / LIBRARY_LOCK
    if not library_lock.is_file():
        return f"检测到 {INSTALL_RECORD}，但缺少 {LIBRARY_LOCK}"

    try:
        lock_text = library_lock.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"{LIBRARY_LOCK} 不可读，无法确认最低资产集"

    if REQUIREMENTS_FOUNDATION_PACK not in lock_text:
        return f"{LIBRARY_LOCK} 缺少最低资产集 {REQUIREMENTS_FOUNDATION_PACK}"

    missing_patches = _detect_missing_critical_runtime_patches(repo_root, record)
    if missing_patches:
        return "critical runtime patch 未完整落地: " + "; ".join(missing_patches)

    missing_codex_skills = _detect_missing_patched_codex_skills(repo_root, record)
    if missing_codex_skills:
        return "patched codex skill 未完整落地: " + "; ".join(missing_codex_skills)

    return None


def _route_result(
    target: str | None,
    action: str,
    reason: str,
    *,
    stage: str | None = None,
    stage_status: str | None = None,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    profile_hint: str | None = None,
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
    if warnings:
        result["warnings"] = warnings
    if profile_hint is not None:
        result["profile_hint"] = profile_hint
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

    # Step 2: determine the active task from Trellis session runtime
    if args.task_dir:
        try:
            task_dir = resolve_task_dir(args.task_dir)
        except FileNotFoundError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
    else:
        active = resolve_active_task(repo_root)
        if active.task_path:
            if active.stale:
                # Distinguish archived vs invalid stale path
                stale_path = active.task_path
                if isinstance(stale_path, (str, Path)):
                    stale_str = str(stale_path)
                    if "archive" in stale_str:
                        _route_result(None, "repair_needed", f"活动任务已归档: {stale_path}。请 task.py start 切换到其他活跃任务")
                    else:
                        _route_result(None, "repair_needed", f"活动任务路径无效: {stale_path}。请 task.py start <task-dir> 重新指定")
                else:
                    _route_result(None, "repair_needed", f"活动任务路径无效: {stale_path}。请 task.py start <task-dir> 重新指定")
                return 0
            resolved_active = resolve_task_ref(active.task_path, repo_root)
            if resolved_active is None or not resolved_active.is_dir():
                _route_result(None, "repair_needed", f"无法解析当前活动任务: {active.task_path}")
                return 0
            task_dir = resolved_active.resolve()
        else:
            degraded_task_dir = resolve_degraded_task_dir(repo_root)
            if degraded_task_dir is not None:
                task_dir = degraded_task_dir
            else:
                tasks_root = repo_root / ".trellis" / "tasks"
                has_any_task = False
                if tasks_root.is_dir():
                    for candidate in tasks_root.iterdir():
                        if candidate.is_dir() and (candidate / TASK_FILE_NAME).is_file():
                            has_any_task = True
                            break
                if not has_any_task:
                    # Detect project profile and whether an existing assessment
                    # explicitly allows direct brainstorm re-entry.
                    profile_hint = None
                    target = "feasibility"
                    reason = "当前 session 尚无 active task，首次进入 feasibility"
                    assessment_path = repo_root / ASSESSMENT_FILE
                    if assessment_path.is_file():
                        try:
                            a_content = assessment_path.read_text(encoding="utf-8")
                            engagement_type = extract_backticked_field(a_content, "project_engagement_type")
                            if engagement_type and engagement_type != "external_outsourcing":
                                profile_hint = "personal"
                            elif engagement_type == "external_outsourcing":
                                profile_hint = "outsourcing"
                            allow_brainstorm = False
                            for line in a_content.splitlines():
                                if "是否允许进入 brainstorm" not in line:
                                    continue
                                if "是" in line or "`yes`" in line or ": yes" in line.lower():
                                    allow_brainstorm = True
                                break
                            if allow_brainstorm:
                                target = "brainstorm"
                                reason = "当前 session 尚无 active task，但已存在允许进入 brainstorm 的 assessment"
                        except (OSError, UnicodeDecodeError):
                            pass
                    else:
                        install_record_path = repo_root / INSTALL_RECORD
                        if install_record_path.is_file():
                            try:
                                import json as _json
                                installed_data = _json.loads(install_record_path.read_text(encoding="utf-8"))
                                installed_profile = installed_data.get("profile")
                                if installed_profile == "outsourcing":
                                    profile_hint = "outsourcing"
                                else:
                                    profile_hint = "personal"
                            except (OSError, UnicodeDecodeError, ValueError):
                                profile_hint = "personal"
                    _route_result(
                        target,
                        "first_entry",
                        reason,
                        profile_hint=profile_hint or "unknown",
                    )
                else:
                    # Enumerate existing tasks for actionable guidance
                    existing_tasks = []
                    try:
                        for candidate in tasks_root.iterdir():
                            if candidate.is_dir() and (candidate / TASK_FILE_NAME).is_file():
                                t_data = read_json(candidate / TASK_FILE_NAME)
                                t_stage = None
                                t_state_path = candidate / "workflow-state.json"
                                if t_state_path.is_file():
                                    t_state = read_json(t_state_path)
                                    if isinstance(t_state, dict):
                                        t_stage = t_state.get("stage")
                                task_label = candidate.name
                                if t_stage:
                                    task_label += f"({t_stage})"
                                existing_tasks.append(task_label)
                    except OSError:
                        pass
                    if existing_tasks:
                        task_list_str = ", ".join(existing_tasks)
                        reason = (
                            f"当前 session 未解析到 active task。已有任务: {task_list_str}。"
                            f"请执行 task.py start <task-dir> 切换到目标任务"
                        )
                    else:
                        reason = "当前 session 未解析到 active task；请先明确当前任务或重新进入目标阶段"
                    _route_result(None, "recovery_needed", reason)
                return 0

    # Step 3: validate the resolved task
    if not task_dir.is_dir():
        _route_result(None, "repair_needed", "当前活动任务目录不存在")
        return 0

    task_data = read_json(task_dir / TASK_FILE_NAME)

    state_path, state = load_state(task_dir)
    if state is None:
        _route_result(
            None,
            "repair_needed",
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前）。请执行 workflow-state.py init <task-dir> --stage feasibility 初始化",
        )
        return 0

    state_errors: list[str] = []
    validate_state_shape(state, state_errors)
    validate_execution_boundary(state, state_errors)
    if state_errors:
        _route_result(
            state.get("stage") if isinstance(state.get("stage"), str) else None,
            "repair_needed",
            state_errors[0],
            stage=state.get("stage") if isinstance(state.get("stage"), str) else None,
            stage_status=state.get("stage_status") if isinstance(state.get("stage_status"), str) else None,
            blockers=state_errors,
        )
        return 0

    # Step 4: route by stage
    stage = state.get("stage", "")
    stage_status = state.get("stage_status", "")
    checkpoints = state.get("checkpoints", {})
    if task_data and stage_requires_leaf(stage):
        children = task_data.get("children", [])
        if isinstance(children, list) and children:
            children_list = ", ".join(str(c) for c in children)
            _route_result(
                None,
                "context_needed",
                f"当前 task 处于 leaf-required stage={stage} 但含有 children，需切换到子任务执行。子任务: {children_list}。请执行 task.py start <child-task-dir>",
                stage=stage,
                stage_status=stage_status or None,
            )
            return 0

    readiness_blockers = collect_route_readiness_blockers(task_dir, repo_root, state)

    if stage_status == "awaiting_user_confirmation":
        exit_blockers = collect_exit_gate_blockers(task_dir, repo_root, state)
        all_blockers = readiness_blockers + exit_blockers
        if all_blockers:
            _route_result(
                stage,
                "awaiting_confirmation_with_blockers",
                f"当前 stage={stage}, status=awaiting_user_confirmation 但仍存在 readiness blockers",
                stage=stage,
                stage_status=stage_status,
                blockers=all_blockers,
            )
        else:
            _route_result(
                stage,
                "awaiting_confirmation",
                f"当前 stage={stage}, status=awaiting_user_confirmation",
                stage=stage,
                stage_status=stage_status,
            )
        return 0

    if readiness_blockers:
        primary_reason = readiness_blockers[0]
        _route_result(
            stage or None,
            "blocked",
            primary_reason,
            stage=stage or None,
            stage_status=stage_status or None,
            blockers=readiness_blockers,
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

    # Non-execution stage — simple reenter with optional warnings
    warnings: list[str] = []
    if stage in STAGES - {"feasibility"}:
        # Collect non-blocking gate warnings for reenter scenarios
        warn_errors: list[str] = []
        validate_external_project_controls(task_dir, repo_root, state, warn_errors)
        validate_ownership_policy_controls(task_dir, repo_root, state, warn_errors)
        warnings.extend(warn_errors)

    _route_result(
        stage,
        "reenter",
        f"当前 stage={stage}, status={stage_status}",
        stage=stage,
        stage_status=stage_status,
        warnings=warnings if warnings else None,
    )
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    # Step 1: resolve repo_root
    try:
        task_dir_path = resolve_task_dir(args.task_dir)
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
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
        validate_execution_boundary(state, check_errors)
        validate_leaf_task(task_dir_path, state.get("stage"), check_errors)
        if not check_errors:
            result = {
                "status": "ok",
                "message": "workflow-state.json 已存在且合法",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

    evidence: list[str] = []
    if state_path.exists() and state is None:
        evidence.append("workflow-state.json 存在但无法读取或不是合法 JSON")
    elif not state_path.exists():
        evidence.append("workflow-state.json 缺失")
    else:
        evidence.append("workflow-state.json 可读取，但当前状态不合法")

    candidate_stage = args.stage
    recovered_from_state = False
    if candidate_stage is None and isinstance(state, dict):
        stage_value = state.get("stage")
        if stage_value in STAGES:
            candidate_stage = stage_value
            recovered_from_state = True
            evidence.append(f"保留了现有 state.stage={stage_value!r}")

    if candidate_stage is None:
        result = {
            "status": "manual_confirmation_required",
            "evidence": evidence,
            "message": (
                "无法从现有 workflow-state.json 自恢复当前阶段。"
                "repair 不会根据 prd.md、task_plan.md、design/、check.md 等产物推断 stage。"
                "请先由用户确认当前已确认阶段，再使用 `--stage <stage>`（必要时配合 `--apply`）重建状态。"
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.apply else 0

    repaired = recover_repair_state(candidate_stage, state)
    apply_repair_overrides(repaired, args)

    repair_errors: list[str] = []
    validate_state_shape(repaired, repair_errors)
    validate_execution_boundary(repaired, repair_errors)
    validate_leaf_task(task_dir_path, candidate_stage, repair_errors)

    missing_confirmation_args: list[str] = []
    if candidate_stage in EXECUTION_STAGES:
        checkpoints = repaired.get("checkpoints", {})
        if checkpoints.get("execution_authorized") is not True:
            missing_confirmation_args.append("--execution-authorized true")
        if not transition_payload_is_valid(repaired.get("last_confirmed_transition"), target_stage=candidate_stage):
            missing_confirmation_args.append("--transition-from <上一阶段>")

    repair_status = "repair_ready"
    if repair_errors:
        if candidate_stage in EXECUTION_STAGES and missing_confirmation_args and all(
            (
                "checkpoints.execution_authorized" in error
                or "last_confirmed_transition" in error
            )
            for error in repair_errors
        ):
            repair_status = "manual_confirmation_required"
        else:
            repair_status = "repair_blocked"

    result = {
        "status": repair_status,
        "stage": candidate_stage,
        "evidence": evidence,
        "blockers": repair_errors,
        "message": (
            f"已准备按 stage={candidate_stage} 重建 workflow-state.json"
            if not repair_errors
            else (
                (
                    f"当前 stage={candidate_stage} 属于执行阶段；还需要用户显式确认执行授权信息后才能重建。"
                    f" 请补充 {' '.join(missing_confirmation_args)}，必要时再配合 --apply。"
                )
                if repair_status == "manual_confirmation_required"
                else (
                    f"当前 stage={candidate_stage} 的状态仍缺少关键语义字段；"
                    "请先回到上游确认点或手动补齐确认信息后再重建。"
                )
            )
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.apply:
        if repair_errors:
            return 1
        write_json(state_path, repaired)
        print(
            json.dumps(
                {"status": "applied", "stage": candidate_stage, "path": str(state_path)},
                ensure_ascii=False,
                indent=2,
            )
        )

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
    set_parser.add_argument("--force", action="store_true", help="skip stage transition gate validation")
    set_parser.add_argument("--stage-status", choices=sorted(STAGE_STATUSES))
    set_parser.add_argument("--current-block")
    set_parser.add_argument("--clear-current-block", action="store_true")
    set_parser.add_argument("--completed-blocks")
    set_parser.add_argument("--allowed-next", nargs="?", const="", default=None)
    set_parser.add_argument("--awaiting-user-confirmation", type=bool_arg)
    set_parser.add_argument("--architecture-confirmed", type=bool_arg)
    set_parser.add_argument("--context7-review-completed", type=bool_arg)
    set_parser.add_argument("--execution-authorized", type=bool_arg)
    set_parser.add_argument("--transition-from", choices=sorted(STAGES))
    set_parser.add_argument("--clear-last-transition", action="store_true")
    set_parser.add_argument("--note")
    set_parser.set_defaults(func=cmd_set)

    validate_parser = subparsers.add_parser("validate", help="validate workflow-state.json and task boundaries")
    validate_parser.add_argument("task_dir")
    validate_parser.add_argument("--project-root")
    validate_parser.add_argument("--skip-active-task-check", action="store_true", help=argparse.SUPPRESS)
    validate_parser.add_argument("--require-active-task-check", action="store_true")
    validate_parser.add_argument(
        "--skip-current-task-check",
        action="store_true",
        dest="skip_active_task_check",
        help=argparse.SUPPRESS,
    )
    validate_parser.add_argument(
        "--require-current-task-check",
        action="store_true",
        dest="require_active_task_check",
        help=argparse.SUPPRESS,
    )
    validate_parser.set_defaults(func=cmd_validate)

    route_parser = subparsers.add_parser("route", help="compute routing target for /trellis:continue")
    route_parser.add_argument("task_dir", nargs="?", default=None)
    route_parser.add_argument("--project-root")
    route_parser.set_defaults(func=cmd_route)

    repair_parser = subparsers.add_parser("repair", help="safely rebuild missing or broken workflow-state.json")
    repair_parser.add_argument("task_dir")
    repair_parser.add_argument("--project-root")
    repair_parser.add_argument("--stage", choices=sorted(STAGES))
    repair_parser.add_argument("--stage-status", choices=sorted(STAGE_STATUSES))
    repair_parser.add_argument("--current-block")
    repair_parser.add_argument("--clear-current-block", action="store_true")
    repair_parser.add_argument("--completed-blocks")
    repair_parser.add_argument("--allowed-next", nargs="?", const="", default=None)
    repair_parser.add_argument("--awaiting-user-confirmation", type=bool_arg)
    repair_parser.add_argument("--architecture-confirmed", type=bool_arg)
    repair_parser.add_argument("--context7-review-completed", type=bool_arg)
    repair_parser.add_argument("--execution-authorized", type=bool_arg)
    repair_parser.add_argument("--transition-from", choices=sorted(STAGES))
    repair_parser.add_argument("--clear-last-transition", action="store_true")
    repair_parser.add_argument("--note")
    repair_parser.add_argument("--apply", action="store_true")
    repair_parser.set_defaults(func=cmd_repair)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

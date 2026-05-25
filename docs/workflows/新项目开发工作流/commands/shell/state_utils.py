#!/usr/bin/env python3
"""Shared constants and low-level helpers for workflow-state modules.

This module owns schema constants, path helpers, JSON/state serialization, and
small data-shaping utilities shared by the higher-level validator, collector,
and route modules.
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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_common import (  # noqa: E402
    PLACEHOLDER_MARKERS,
)


def _resolve_trellis_scripts_dir() -> Path:
    for candidate_root in Path(__file__).resolve().parents:
        scripts_dir = candidate_root / ".trellis" / "scripts"
        if (scripts_dir / "common" / "__init__.py").is_file():
            return scripts_dir
    raise RuntimeError("无法定位 Trellis scripts 目录")


TRELLIS_SCRIPTS_DIR = _resolve_trellis_scripts_dir()
if str(TRELLIS_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(TRELLIS_SCRIPTS_DIR))

from common.active_task import resolve_active_task, resolve_task_ref  # type: ignore[import-not-found]  # noqa: E402


STATE_FILE_NAME = "workflow-state.json"
TASK_FILE_NAME = "task.json"
INSTALL_RECORD = ".trellis/workflow-installed.json"
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
FINISH_WORK_PATCH_FILE = Path("finish-work-patch-projectization.md")
VALID_ENGAGEMENT_TYPES = {"external_outsourcing", "non_outsourcing"}
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
DESIGN_ALLOWED_CURRENT_BLOCKS = {
    "input-review",
    "option-research",
    "A",
    "B",
    "C",
    "D",
}

STAGES = {
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "implementation",
    "check",
    "review-gate",
    "project-audit",
    "delivery",
}
STAGE_TRANSITIONS: dict[str, list[str]] = {
    "feasibility": ["brainstorm"],
    "brainstorm": ["design", "plan", "implementation"],
    "design": ["plan"],
    "plan": ["implementation"],
    "implementation": ["check", "project-audit"],
    "check": ["implementation", "review-gate", "project-audit", "delivery"],
    "review-gate": ["implementation", "project-audit", "delivery"],
    "project-audit": ["implementation", "check", "review-gate", "delivery"],
    "delivery": [],
}
STAGE_STATUSES = {
    "in_progress",
    "blocked",
    "awaiting_user_confirmation",
    "completed",
}
EXECUTION_STAGES = {"implementation"}
COORDINATION_STAGES = {"feasibility", "brainstorm", "design", "plan", "project-audit", "delivery"}
LEAF_REQUIRED_STAGES = STAGES - COORDINATION_STAGES
SUPPORTED_STATE_VERSION = 1
PROJECT_ESTIMATE_REQUIRED_STAGES = STAGES - {"feasibility", "brainstorm"}
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
BRAINSTORM_EXIT_SNAPSHOT_FIELDS = (
    "complexity_decision",
    "ui_lane_decision",
    "cross_platform_scope",
    "estimate_refresh_result",
    "kill_criteria",
    "open_items",
)
L0_DIRECT_EXECUTION_MARKERS = (
    "automation_matrix_source",
    "closeout_baseline_source",
)
REVIEW_GATE_DECISIONS = {"skip", "recommended", "required"}
REVIEW_GATE_HARD_CONDITION_FIELDS = (
    ("auth_or_sensitive", "认证 / 授权 / 权限边界 / 敏感信息处理"),
    ("data_migration_or_schema_change", "数据迁移 / schema 变化 / 删除 / 回填"),
    (
        "public_api_or_cross_layer_contract_or_external_integration",
        "公共 API / 跨层 contract / 外部系统集成",
    ),
    ("payment_queue_cache_concurrency", "支付 / 消息队列 / 缓存一致性 / 并发状态"),
    ("shared_core_with_blast_radius", "共享核心模块且 blast radius 明显"),
    ("explicit_user_review_gate_request", "用户显式要求进入 review-gate"),
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
        "status": "in_progress",
        "current_block": None,
        "completed_blocks": [],
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
    state = read_json(state_path)
    if isinstance(state, dict) and "status" not in state:
        legacy_status = state.get("stage_status")
        if isinstance(legacy_status, str):
            state["status"] = legacy_status
    return state_path, state


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
    if not lines:
        return combined

    failure_lines = [
        line
        for line in lines
        if line.startswith("❌") or line.lower().startswith("error:")
    ]
    if failure_lines:
        return " | ".join(failure_lines[:3])

    return " | ".join(lines[:3])


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

    if candidate_stage in EXECUTION_STAGES:
        existing_status = state.get("status") or state.get("stage_status")
        if existing_status in STAGE_STATUSES:
            repaired["status"] = existing_status

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
        repaired["status"] = args.stage_status
    if getattr(args, "clear_current_block", False):
        repaired["current_block"] = None
    elif getattr(args, "current_block", None) is not None:
        repaired["current_block"] = args.current_block
    if getattr(args, "completed_blocks", None) is not None:
        repaired["completed_blocks"] = [item for item in args.completed_blocks.split(",") if item]

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


def find_task_plan_file(task_dir: Path, repo_root: Path) -> Path | None:
    for candidate_dir in iter_task_lineage(task_dir, repo_root):
        plan_file = candidate_dir / TASK_PLAN_FILE
        if plan_file.is_file():
            return plan_file
    return None

def installed_workflow_profile(repo_root: Path) -> str | None:
    install_record = read_json(repo_root / INSTALL_RECORD)
    if not isinstance(install_record, dict):
        return None
    profile = install_record.get("profile")
    return profile if profile in {"personal", "outsourcing"} else None


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


def normalize_design_current_block(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().lower().replace("_", "-")
    mapping = {
        "input-review": "input-review",
        "input review": "input-review",
        "option-research": "option-research",
        "option research": "option-research",
        "tech-selection": "option-research",
        "tech selection": "option-research",
        "spec-alignment": "D",
        "engineering-alignment": "D",
        "engineering alignment": "D",
        "project-docs": "C",
        "project docs": "C",
        "design-docs": "B",
        "design docs": "B",
        "developer-facing-prd": "A",
        "developer-facing-prd.md": "A",
        "developer facing prd": "A",
    }
    if normalized in mapping:
        return mapping[normalized]
    return normalize_design_block_name(raw)


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


def find_missing_markers(path: Path, markers: tuple[str, ...]) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return list(markers)
    return [marker for marker in markers if marker not in content]


def design_path_candidates_from_state(state: dict[str, Any]) -> set[str]:
    allowed_next_override = state.get("allowed_next_stages")
    if isinstance(allowed_next_override, list) and all(isinstance(item, str) for item in allowed_next_override):
        return {item for item in allowed_next_override if item in STAGES}
    allowed_next_cli = state.get("_allowed_next_override")
    if isinstance(allowed_next_cli, list) and all(isinstance(item, str) for item in allowed_next_cli):
        return {item for item in allowed_next_cli if item in STAGES}
    current_stage = state.get("stage", "")
    allowed_next = STAGE_TRANSITIONS.get(current_stage, [])
    return {item for item in allowed_next if isinstance(item, str)}


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
        pending["status"] = args.stage_status
    if args.clear_current_block:
        pending["current_block"] = None
    elif args.current_block is not None:
        pending["current_block"] = args.current_block
    if args.completed_blocks is not None:
        pending["completed_blocks"] = [item for item in args.completed_blocks.split(",") if item]
    if args.allowed_next is not None:
        pending["_allowed_next_override"] = [item for item in args.allowed_next.split(",") if item]
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

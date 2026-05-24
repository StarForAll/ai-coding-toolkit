#!/usr/bin/env python3
"""Core validators for workflow-state shape, task boundaries, and shared controls."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_common import MIN_KICKOFF_PAYMENT_RATIO, extract_backticked_field  # noqa: E402
from state_utils import (  # noqa: E402
    CONTEXT7_REVIEW_FILE,
    CUSTOMER_ESTIMATE_MARKERS,
    CUSTOMER_PRD,
    DEVELOPER_PRD,
    DESIGN_ALLOWED_CURRENT_BLOCKS,
    EXECUTION_STAGES,
    EXIT_READY_STATUSES,
    LEAF_REQUIRED_STAGES,
    PROJECT_ESTIMATE_DOC_STAGES,
    PROJECT_ESTIMATE_REQUIRED_STAGES,
    ROOT_README,
    ROOT_README_EN,
    STAGES,
    STAGE_STATUSES,
    SUPPORTED_STATE_VERSION,
    TASK_ESTIMATE_MARKERS,
    TASK_PRD,
    VALID_ENGAGEMENT_TYPES,
    VALID_SOURCE_WATERMARK_LEVELS,
    design_exit_ready,
    find_assessment_file,
    find_missing_markers,
    installed_workflow_profile,
    is_personal_brainstorm_bootstrap_allowed,
    is_placeholder_like,
    load_task_json,
    normalize_design_current_block,
    normalize_yes_no_field,
    parse_channels,
    resolve_active_task,
    resolve_task_ref,
)


def validate_state_shape(state: dict[str, Any], errors: list[str]) -> None:
    if "version" not in state:
        state["version"] = SUPPORTED_STATE_VERSION

    required_keys = {
        "version",
        "stage",
        "status",
        "current_block",
        "completed_blocks",
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

    status = state.get("status")
    if status not in STAGE_STATUSES:
        errors.append(f"status 非法: {status!r}")

    current_block = state.get("current_block")
    if current_block is not None and not isinstance(current_block, str):
        errors.append("current_block 必须是字符串或 null")
    elif isinstance(current_block, str) and state.get("stage") == "design":
        normalized_current_block = normalize_design_current_block(current_block)
        if normalized_current_block not in DESIGN_ALLOWED_CURRENT_BLOCKS:
            errors.append(
                "design 阶段的 current_block 非法："
                f"{current_block!r}；只能使用 input-review / option-research / A / B / C / D"
            )

    completed_blocks = state.get("completed_blocks")
    if not isinstance(completed_blocks, list) or not all(isinstance(item, str) for item in completed_blocks):
        errors.append("completed_blocks 必须是字符串数组")

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


def validate_execution_boundary(state: dict[str, Any], errors: list[str]) -> None:
    stage = state.get("stage")
    checkpoints = state.get("checkpoints", {})
    execution_authorized = checkpoints.get("execution_authorized", False)

    if stage in EXECUTION_STAGES:
        if execution_authorized is not True:
            errors.append(
                f"当前 stage={stage!r} 时，checkpoints.execution_authorized 必须为 true"
            )
    else:
        if execution_authorized is True:
            errors.append(
                f"当前 stage={stage!r} 不是执行阶段，checkpoints.execution_authorized 必须为 false"
            )


def validate_session_active_task(task_dir: Path, repo_root: Path, errors: list[str]) -> None:
    active = resolve_active_task(repo_root)
    if not active.task_path:
        errors.append("无法从 Trellis session runtime 解析当前活动任务")
        return
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
            f"Trellis session runtime 指向 {actual}，与当前 task {expected} 不一致"
        )


def stage_requires_leaf(stage: str | None) -> bool:
    return isinstance(stage, str) and stage in LEAF_REQUIRED_STAGES


def validate_leaf_task(task_dir: Path, stage: str | None, errors: list[str]) -> None:
    if not stage_requires_leaf(stage):
        return
    task_data = load_task_json(task_dir)
    if not task_data:
        errors.append("task.json 无法读取")
        return
    children = task_data.get("children", [])
    if isinstance(children, list) and children:
        errors.append("当前 task 已有 children，不应继续作为执行态叶子任务持有 workflow-state")


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
        if target_stage is None and is_personal_brainstorm_bootstrap_allowed(task_dir, repo_root, state):
            return
        transition = state.get("last_confirmed_transition")
        transition_from = transition.get("from") if isinstance(transition, dict) else None
        if installed_workflow_profile(repo_root) == "personal" and (
            state.get("stage") == "brainstorm" or transition_from == "brainstorm"
        ):
            if target_stage is None:
                errors.append(
                    "缺少 assessment.md；personal profile 首次入口可在当前 brainstorm 阶段补齐最小 assessment 基线，补齐后再继续本阶段。"
                )
            else:
                errors.append(
                    f"缺少 assessment.md；personal profile 首次入口必须先在当前 brainstorm 阶段补齐最小 assessment 基线，才能进入 {target_stage}"
                )
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
        errors.append("外包项目在启动款未确认到账前，不得进入 implementation")

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


def validate_context7_review_artifact(
    task_dir: Path,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    checkpoints = state.get("checkpoints", {})
    architecture_confirmed = checkpoints.get("architecture_confirmed", False)
    context7_review_completed = checkpoints.get("context7_review_completed", False)
    stage = state.get("stage")
    final_design_exit = design_exit_ready(state) and state.get("status") in EXIT_READY_STATUSES

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
    final_design_exit = design_exit_ready(state) and state.get("status") in EXIT_READY_STATUSES

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


def validate_design_engineering_alignment_contract(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
    errors: list[str],
) -> None:
    if state.get("stage") != "design":
        return
    if not design_exit_ready(state) or state.get("status") not in EXIT_READY_STATUSES:
        return

    task_prd = task_dir / TASK_PRD
    if task_prd.is_file():
        task_prd_text = task_prd.read_text(encoding="utf-8")
        required_task_markers = (
            "自动化检查矩阵",
            "质量平台门禁",
            "close-out 主入口",
            "archive 前置条件",
            "元数据边界",
        )
        missing_task_markers = [marker for marker in required_task_markers if marker not in task_prd_text]
        if missing_task_markers:
            errors.append(
                "design 退出前 task 工作底稿缺少工程化联动结论: "
                + ", ".join(missing_task_markers)
                + "；块 D 尚未真正完成"
            )

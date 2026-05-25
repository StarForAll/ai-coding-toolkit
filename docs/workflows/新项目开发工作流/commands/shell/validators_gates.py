#!/usr/bin/env python3
"""Stage-gate validators built on top of workflow-state core validation rules."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_common import extract_backticked_field  # noqa: E402
from state_utils import (  # noqa: E402
    BRAINSTORM_EXIT_SNAPSHOT_FIELDS,
    CHECK_MD_FILE,
    CUSTOMER_ESTIMATE_MARKERS,
    CUSTOMER_PRD,
    DELIVERY_ARTIFACTS,
    EXECUTION_STAGES,
    EXIT_READY_STATUSES,
    FINISH_WORK_CHECKLIST_FILE,
    PROJECT_ESTIMATE_REQUIRED_STAGES,
    REVIEW_GATE_DECISIONS,
    REVIEW_GATE_HARD_CONDITION_FIELDS,
    STAGES,
    STAGE_TRANSITIONS,
    TASK_CREATION_CHECKLIST_FILE,
    TASK_ESTIMATE_MARKERS,
    TASK_PLAN_FILE,
    TASK_PRD,
    design_path_candidates_from_state,
    find_assessment_file,
    find_missing_markers,
    is_placeholder_like,
    normalize_yes_no_field,
    run_gate_validator,
)
from validators_core import (  # noqa: E402
    validate_context7_review_artifact,
    validate_design_engineering_alignment_contract,
    validate_external_project_controls,
    validate_leaf_task,
    validate_ownership_policy_controls,
    validate_project_doc_boundary,
)


def validate_plan_gate(task_dir: Path, errors: list[str]) -> None:
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


def validate_design_exit_gate(task_dir: Path, repo_root: Path | None, state: dict[str, Any], errors: list[str]) -> None:
    run_gate_validator(
        "ownership-proof-validate.py",
        ["--phase", "design", "--task-dir", str(task_dir)],
        errors,
        label="ownership-proof-validate.py design 校验",
    )
    if repo_root is not None:
        validate_design_engineering_alignment_contract(task_dir, repo_root, state, errors)


def validate_check_review_gate_decision(
    content: str,
    errors: list[str],
    *,
    for_delivery: bool = False,
) -> None:
    if not re.search(r"^\s*##+\s*(?:Review-Gate Decision|补充审查判定)\s*$", content, re.MULTILINE):
        errors.append(
            "check.md 缺少 Review-Gate Decision / 补充审查判定章节；"
            "check 阶段产物不完整，不得进入后续阶段"
        )
        return

    decision = extract_backticked_field(content, "review_gate_decision")
    if decision not in REVIEW_GATE_DECISIONS:
        rendered = decision or "(missing)"
        errors.append(
            f"check.md 的 `review_gate_decision` 非法: {rendered!r}；"
            "只能填写 `skip` / `recommended` / `required`"
        )
        return

    reason = extract_backticked_field(content, "review_gate_reason")
    if is_placeholder_like(reason):
        errors.append("check.md 的 `review_gate_reason` 未填写具体结论")

    hard_hits: list[str] = []
    for field_name, label in REVIEW_GATE_HARD_CONDITION_FIELDS:
        raw_value = extract_backticked_field(content, field_name)
        normalized = normalize_yes_no_field(raw_value)
        if normalized is None:
            rendered = raw_value or "(missing)"
            errors.append(
                f"check.md 的 `{field_name}` 非法: {rendered!r}；只能填写 `yes` / `no`"
            )
            continue
        if normalized is True:
            hard_hits.append(label)

    if hard_hits and decision != "required":
        errors.append(
            "check.md 命中了 review-gate 硬条件，但 `review_gate_decision` 不是 `required`: "
            + " / ".join(hard_hits)
        )

    if for_delivery and decision == "required":
        errors.append("check.md 的 `review_gate_decision`=`required`；不得从 check 直接进入 delivery")


def validate_check_gate(task_dir: Path, errors: list[str], *, for_delivery: bool = False) -> None:
    check_path = task_dir / CHECK_MD_FILE
    if not check_path.is_file():
        errors.append("缺少 check.md；check 阶段产物未生成，不得进入 review-gate")
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
            "check 阶段产物不完整，不得进入 review-gate"
        )
        return

    if not re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE):
        errors.append(
            "check.md 缺少真实验证结论（pass / fail / not run）；"
            "check 阶段产物不完整，不得进入 review-gate"
        )
        return

    validate_check_review_gate_decision(content, errors, for_delivery=for_delivery)


def validate_finish_work_gate(task_dir: Path, errors: list[str]) -> None:
    checklist_path = task_dir / FINISH_WORK_CHECKLIST_FILE
    if not checklist_path.is_file():
        errors.append(
            "缺少 finish-work-checklist.md；delivery 阶段前置条件未满足，未冻结验证矩阵与收尾证据"
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
            "delivery 阶段前置条件不完整"
        )
        return

    if not re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE):
        errors.append(
            "finish-work-checklist.md 缺少真实验证结论（pass / fail / not run）；"
            "delivery 阶段前置条件不完整"
        )
    if not re.search(r"当前状态|status|证据缺口|evidence gap", content, re.IGNORECASE):
        errors.append(
            "finish-work-checklist.md 缺少人工验证真实状态或证据缺口；"
            "delivery 阶段前置条件不完整"
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


def validate_delivery_gate(task_dir: Path, errors: list[str], repo_root: Path | None = None) -> None:
    missing = [
        artifact.as_posix()
        for artifact in DELIVERY_ARTIFACTS
        if not (task_dir / artifact).is_file()
    ]
    if missing:
        errors.append(f"缺少交付产物: {', '.join(missing)}；delivery 阶段未完成")
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
                    label
                    for artifact_path, label in outsourcing_artifacts
                    if not (task_dir / artifact_path).is_file()
                ]
                if missing_outsourcing:
                    errors.append(
                        f"外包项目缺少交付产物: {', '.join(missing_outsourcing)}；"
                        "delivery 阶段未完成"
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
    allowed_targets = design_path_candidates_from_state(state)
    if require_exit_snapshot:
        missing_snapshot = [
            field for field in BRAINSTORM_EXIT_SNAPSHOT_FIELDS if f"`{field}`" not in task_content
        ]
        if missing_snapshot:
            errors.append(
                f"{TASK_PRD.as_posix()} 缺少阶段出口快照字段: {', '.join(missing_snapshot)}"
            )
        else:
            placeholder_snapshot = [
                field
                for field in BRAINSTORM_EXIT_SNAPSHOT_FIELDS
                if is_placeholder_like(extract_backticked_field(task_content, field))
            ]
            if placeholder_snapshot:
                errors.append(
                    f"{TASK_PRD.as_posix()} 的阶段出口快照字段未填写有效结论: {', '.join(placeholder_snapshot)}"
                )
            elif allowed_targets and allowed_targets.issubset(EXECUTION_STAGES):
                complexity_decision = extract_backticked_field(task_content, "complexity_decision")
                if complexity_decision != "L0":
                    rendered_value = complexity_decision or "(missing)"
                    errors.append(
                        f"{TASK_PRD.as_posix()} 的 `complexity_decision`={rendered_value!r}；"
                        "brainstorm 仅允许 `L0` 直接进入 implementation，其他复杂度必须先进入 design/plan"
                    )

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


def validate_stage_transition_gates(
    task_dir: Path,
    repo_root: Path,
    current_state: dict[str, Any],
    candidate_state: dict[str, Any],
    new_stage: str,
    errors: list[str],
) -> None:
    if new_stage in {"feasibility"}:
        return
    validate_leaf_task(task_dir, new_stage, errors)

    current_stage = current_state.get("stage")
    canonical_next = STAGE_TRANSITIONS.get(current_stage, [])
    if current_stage is not None and new_stage != current_stage and new_stage not in canonical_next:
        errors.append(
            f"阶段切换被拒绝: {current_stage!r} → {new_stage!r} 不属于 canonical transition {canonical_next}"
        )
        return

    if new_stage in STAGES - {"feasibility"}:
        gate_errors: list[str] = []
        validate_external_project_controls(
            task_dir,
            repo_root,
            candidate_state,
            gate_errors,
            target_stage=new_stage,
        )
        validate_ownership_policy_controls(task_dir, repo_root, current_state, gate_errors)
        errors.extend(gate_errors)

    if new_stage in PROJECT_ESTIMATE_REQUIRED_STAGES:
        validate_project_doc_boundary(candidate_state, repo_root, task_dir, errors)

    if current_state.get("stage") == "brainstorm":
        allowed_targets = design_path_candidates_from_state(candidate_state)
        validate_brainstorm_exit_gate(
            current_state,
            repo_root,
            task_dir,
            errors,
            require_customer_prd=bool(allowed_targets & {"design", "plan"}),
        )

    if current_state.get("stage") == "design" and new_stage == "plan":
        validate_design_exit_gate(task_dir, repo_root, current_state, errors)

    if new_stage in EXECUTION_STAGES and current_state.get("stage") == "plan":
        validate_plan_gate(task_dir, errors)

    if new_stage == "review-gate":
        validate_check_gate(task_dir, errors)

    if current_stage == "check" and new_stage == "delivery":
        validate_check_gate(task_dir, errors, for_delivery=True)

    if current_stage == "project-audit":
        validate_project_audit_gate(task_dir, errors)

    if current_stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)

    if new_stage == "delivery" and current_stage == "project-audit":
        validate_project_audit_gate(task_dir, errors)


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
        allowed_targets = design_path_candidates_from_state(state)
        exit_ready = state.get("status") in EXIT_READY_STATUSES
        validate_brainstorm_exit_gate(
            state,
            repo_root,
            task_dir,
            errors,
            require_exit_snapshot=exit_ready,
            require_customer_prd=exit_ready and bool(allowed_targets & {"design", "plan"}),
        )
    elif stage == "design":
        if state.get("status") in EXIT_READY_STATUSES:
            validate_project_doc_boundary(state, repo_root, task_dir, errors)
            validate_context7_review_artifact(task_dir, state, errors)
            validate_design_exit_gate(task_dir, repo_root, state, errors)
    elif stage == "plan":
        validate_plan_gate(task_dir, errors)
    elif stage == "check":
        validate_check_gate(task_dir, errors)
    elif stage == "project-audit":
        validate_project_audit_gate(task_dir, errors)
    elif stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)
    elif stage == "delivery":
        validate_delivery_gate(task_dir, errors, repo_root)

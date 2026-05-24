#!/usr/bin/env python3
"""Workflow strong-gate state helper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_common import extract_backticked_field  # noqa: E402
from embed_integrity import detect_embed_invalid  # noqa: E402
from state_utils import (  # noqa: E402
    ASSESSMENT_FILE,
    EXECUTION_STAGES,
    INSTALL_RECORD,
    ROOT_README_EN,
    STAGES,
    STAGE_STATUSES,
    STAGE_TRANSITIONS,
    TASK_ESTIMATE_MARKERS,
    TASK_FILE_NAME,
    TASK_PRD,
    apply_repair_overrides,
    bool_arg,
    build_default_state,
    build_pending_state_for_set,
    design_path_candidates_from_state,
    find_assessment_file,
    find_missing_markers,
    find_repo_root,
    installed_workflow_profile,
    is_personal_brainstorm_bootstrap_allowed,
    load_state,
    load_task_json,
    now_iso,
    read_json,
    recover_repair_state,
    resolve_active_task,
    resolve_task_dir,
    resolve_task_ref,
    transition_payload_is_valid,
    write_json,
)
from validators_core import (  # noqa: E402
    stage_requires_leaf,
    validate_execution_boundary,
    validate_external_project_controls,
    validate_context7_review_artifact,
    validate_leaf_task,
    validate_ownership_policy_controls,
    validate_project_doc_boundary,
    validate_session_active_task,
    validate_state_shape,
)
from validators_gates import (  # noqa: E402
    validate_brainstorm_exit_gate,
    validate_check_gate,
    validate_delivery_gate,
    validate_design_exit_gate,
    validate_plan_gate,
    validate_project_audit_gate,
    validate_review_gate_gate,
    validate_stage_exit_artifacts,
    validate_stage_transition_gates,
)


def _route_result(
    target: str | None,
    action: str,
    reason: str,
    *,
    stage: str | None = None,
    status: str | None = None,
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
    if status is not None:
        result["status"] = status
    result["reason"] = reason
    result["blockers"] = blockers or []
    if warnings:
        result["warnings"] = warnings
    if profile_hint is not None:
        result["profile_hint"] = profile_hint
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def _resolve_route_repo_root(args: argparse.Namespace) -> Path | None:
    if args.project_root:
        return Path(args.project_root).resolve()
    if args.task_dir:
        return find_repo_root(Path(args.task_dir).resolve())
    return find_repo_root(Path.cwd())


def _route_entry_choice_without_any_task(repo_root: Path, tasks_root: Path) -> int:
    _ = tasks_root
    profile_hint = None
    target = "feasibility"
    reason = "当前 session 尚无 active task，首次进入 feasibility"
    assessment_path = repo_root / ASSESSMENT_FILE
    if assessment_path.is_file():
        try:
            assessment_content = assessment_path.read_text(encoding="utf-8")
            engagement_type = extract_backticked_field(assessment_content, "project_engagement_type")
            if engagement_type and engagement_type != "external_outsourcing":
                profile_hint = "personal"
            elif engagement_type == "external_outsourcing":
                profile_hint = "outsourcing"

            allow_brainstorm = False
            for line in assessment_content.splitlines():
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
                installed_data = json.loads(install_record_path.read_text(encoding="utf-8"))
                installed_profile = installed_data.get("profile")
                if installed_profile == "outsourcing":
                    profile_hint = "outsourcing"
                elif installed_profile == "personal":
                    profile_hint = "personal"
                    target = "brainstorm"
                    reason = (
                        "当前 session 尚无 active task，personal profile 首次入口可直接进入 brainstorm，"
                        "并在该阶段补齐 assessment 基线"
                    )
                else:
                    profile_hint = "unknown"
            except (OSError, UnicodeDecodeError, ValueError):
                profile_hint = "unknown"

    _route_result(
        target,
        "entry_choice_required",
        (
            f"{reason}。若当前意图是 workflow / 项目只读分析、元审计或 A/A+ 纯分析，"
            "保持 no_task 直接分析，不要把仓库误当成新项目入口；"
            + (
                "若 `profile_hint=unknown`，请先确认当前项目应按 personal 还是 outsourcing 理解，再决定是否跳过 feasibility；"
                if profile_hint == "unknown"
                else ""
            )
            + f"若当前意图是开始新的实现任务，则进入 {target}"
        ),
        profile_hint=profile_hint or "unknown",
    )
    return 0


def _route_recovery_without_active_task(tasks_root: Path) -> int:
    existing_tasks = []
    try:
        for candidate in tasks_root.iterdir():
            if candidate.is_dir() and (candidate / TASK_FILE_NAME).is_file():
                task_stage = None
                state_path = candidate / "workflow-state.json"
                if state_path.is_file():
                    state = read_json(state_path)
                    if isinstance(state, dict):
                        task_stage = state.get("stage")
                task_label = candidate.name
                if task_stage:
                    task_label += f"({task_stage})"
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


def _resolve_route_task_dir(args: argparse.Namespace, repo_root: Path) -> tuple[Path | None, int]:
    if args.task_dir:
        try:
            return resolve_task_dir(args.task_dir), 0
        except FileNotFoundError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return None, 1

    active = resolve_active_task(repo_root)
    if active.task_path:
        if active.stale:
            stale_path = active.task_path
            if isinstance(stale_path, (str, Path)) and "archive" in str(stale_path):
                _route_result(None, "repair_needed", f"活动任务已归档: {stale_path}。请 task.py start 切换到其他活跃任务")
            else:
                _route_result(None, "repair_needed", f"活动任务路径无效: {stale_path}。请 task.py start <task-dir> 重新指定")
            return None, 0
        resolved_active = resolve_task_ref(active.task_path, repo_root)
        if resolved_active is None or not resolved_active.is_dir():
            _route_result(None, "repair_needed", f"无法解析当前活动任务: {active.task_path}")
            return None, 0
        return resolved_active.resolve(), 0

    tasks_root = repo_root / ".trellis" / "tasks"
    has_any_task = False
    if tasks_root.is_dir():
        for candidate in tasks_root.iterdir():
            if candidate.is_dir() and (candidate / TASK_FILE_NAME).is_file():
                has_any_task = True
                break
    if not has_any_task:
        return None, _route_entry_choice_without_any_task(repo_root, tasks_root)
    return None, _route_recovery_without_active_task(tasks_root)


def _collect_dependency_blockers(task_dir: Path, repo_root: Path) -> list[str]:
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


def _collect_route_readiness_blockers(
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
                if installed_workflow_profile(repo_root) == "personal":
                    blockers.append(
                        "缺少 assessment.md；personal profile 首次入口可在当前 brainstorm 阶段补齐最小 assessment 基线。"
                        "请先补齐 assessment，再继续或退出本阶段。"
                    )
                else:
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
        blockers.extend(_collect_dependency_blockers(task_dir, repo_root))

    if stage == "review-gate":
        validate_check_gate(task_dir, blockers)

    return blockers


def _collect_nonblocking_warnings(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if state.get("stage") == "brainstorm" and is_personal_brainstorm_bootstrap_allowed(task_dir, repo_root, state):
        warnings.append(
            "assessment.md 基线尚未补齐（personal bootstrap 允许当前 brainstorm 继续，但离开 brainstorm 前必须完成最小 assessment 字段）。"
        )
    return warnings


def _collect_non_execution_reentry_blockers(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> list[str]:
    stage = state.get("stage")
    if stage not in STAGES - {"feasibility"}:
        return []

    blockers: list[str] = []
    validate_external_project_controls(task_dir, repo_root, state, blockers)
    validate_ownership_policy_controls(task_dir, repo_root, state, blockers)
    validate_project_doc_boundary(state, repo_root, task_dir, blockers)
    return blockers


def _collect_exit_gate_blockers(
    task_dir: Path,
    repo_root: Path,
    state: dict[str, Any],
) -> list[str]:
    stage = state.get("stage")
    blockers: list[str] = []

    if stage == "check":
        validate_check_gate(task_dir, blockers)
    elif stage == "plan":
        validate_plan_gate(task_dir, blockers)
    elif stage == "delivery":
        validate_delivery_gate(task_dir, blockers, repo_root)
    elif stage == "project-audit":
        validate_project_audit_gate(task_dir, blockers)
    elif stage == "review-gate":
        validate_review_gate_gate(task_dir, blockers)
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


def _route_valid_task_state(
    task_dir: Path,
    repo_root: Path,
    task_data: dict[str, Any] | None,
    state: dict[str, Any],
) -> int:
    stage = state.get("stage", "")
    status = state.get("status", "")
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
                status=status or None,
            )
            return 0

    readiness_blockers = _collect_route_readiness_blockers(task_dir, repo_root, state)
    route_warnings = _collect_nonblocking_warnings(task_dir, repo_root, state)

    if status == "awaiting_user_confirmation":
        exit_blockers = _collect_exit_gate_blockers(task_dir, repo_root, state)
        all_blockers = readiness_blockers + exit_blockers
        if all_blockers:
            _route_result(
                stage,
                "awaiting_confirmation_with_blockers",
                f"当前 stage={stage}, status=awaiting_user_confirmation 但仍存在 readiness blockers",
                stage=stage,
                status=status,
                blockers=all_blockers,
            )
        else:
            _route_result(
                stage,
                "awaiting_confirmation",
                f"当前 stage={stage}, status=awaiting_user_confirmation",
                stage=stage,
                status=status,
            )
        return 0

    if readiness_blockers:
        _route_result(
            stage or None,
            "blocked",
            readiness_blockers[0],
            stage=stage or None,
            status=status or None,
            blockers=readiness_blockers,
        )
        return 0

    if stage in EXECUTION_STAGES:
        blockers: list[str] = []
        if checkpoints.get("execution_authorized", False) is not True:
            blockers.append("checkpoints.execution_authorized 未授权")

        assessment_file = find_assessment_file(task_dir, repo_root)
        if assessment_file is not None:
            assessment_content = assessment_file.read_text(encoding="utf-8")
            engagement_type = extract_backticked_field(assessment_content, "project_engagement_type")
            if engagement_type == "external_outsourcing":
                kickoff_received = extract_backticked_field(assessment_content, "kickoff_payment_received")
                if kickoff_received != "yes":
                    blockers.append("外包项目启动款未确认到账")

        if blockers:
            _route_result(
                stage,
                "blocked",
                f"当前 stage={stage} 存在阻塞条件",
                stage=stage,
                status=status,
                blockers=blockers,
            )
            return 0

    else:
        non_execution_blockers = _collect_non_execution_reentry_blockers(task_dir, repo_root, state)
        if non_execution_blockers:
            _route_result(
                stage or None,
                "blocked",
                non_execution_blockers[0],
                stage=stage or None,
                status=status or None,
                blockers=non_execution_blockers,
            )
            return 0

    _route_result(
        stage,
        "reenter",
        f"当前 stage={stage}, status={status}",
        stage=stage,
        status=status,
        warnings=route_warnings,
    )
    return 0


def _route_task_dir(task_dir: Path, repo_root: Path) -> int:
    if not task_dir.is_dir():
        _route_result(None, "repair_needed", "当前活动任务目录不存在")
        return 0

    task_data = read_json(task_dir / TASK_FILE_NAME)
    _state_path, state = load_state(task_dir)
    if state is None:
        _route_result(
            None,
            "repair_needed",
            "缺少 workflow-state.json（可能因任务创建于工作流安装之前，或当前任务尚未初始化阶段状态）。请先执行 workflow-state.py repair <task-dir>。若输出 repair_ready，在用户确认后再配合 --apply；若输出 manual_confirmation_required，必须按当前已确认阶段显式补齐 --stage，执行阶段还要补 --execution-authorized true 与 --transition-from <上一阶段>。",
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
            status=state.get("status") if isinstance(state.get("status"), str) else None,
            blockers=state_errors,
        )
        return 0

    return _route_valid_task_state(task_dir, repo_root, task_data, state)


def cmd_init(args: argparse.Namespace) -> int:
    task_dir = resolve_task_dir(args.task_dir)
    state_path, _state = load_state(task_dir)
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

    if args.stage and pending_stage != current_stage and not args.force:
        canonical_next = STAGE_TRANSITIONS.get(current_stage, [])
        if pending_stage not in canonical_next:
            print(
                f"❌ 阶段切换被拒绝: {current_stage!r} → {pending_stage!r} 不属于 canonical transition {canonical_next}；如需强制切换请使用 --force"
            )
            return 1
        if pending_stage not in {"feasibility"}:
            current_status = state.get("status", "")
            if current_status != "awaiting_user_confirmation":
                print(
                    f"❌ 阶段切换被拒绝: 进入 {pending_stage!r} 前 status 必须为 awaiting_user_confirmation；当前为 {current_status!r}。如需强制切换请使用 --force"
                )
                return 1
        if pending_stage in EXECUTION_STAGES:
            checkpoints = pending_state.get("checkpoints", {})
            pending_ea = checkpoints.get("execution_authorized", False)
            if pending_ea is not True:
                print(
                    f"❌ 阶段切换被拒绝: 进入 {pending_stage!r} 前 checkpoints.execution_authorized 必须为 true（可在同一命令中通过 --execution-authorized true 设置）。如需强制切换请使用 --force"
                )
                return 1
        repo_root = find_repo_root(task_dir)
        if repo_root is not None:
            gate_errors: list[str] = []
            validate_stage_transition_gates(
                task_dir,
                repo_root,
                state,
                pending_state,
                pending_stage,
                gate_errors,
            )
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
    warnings: list[str] = []

    if state is None:
        print(f"❌ {state_path} 不存在或无法读取")
        return 1
    print(f"✅ 找到 {state_path.name}")

    validate_state_shape(state, errors)
    validate_execution_boundary(state, errors)

    if args.require_active_task_check:
        if repo_root is None:
            errors.append("无法定位 repo root，不能校验当前活动任务")
        else:
            validate_session_active_task(task_dir, repo_root, errors)
    if repo_root is not None:
        warnings.extend(_collect_nonblocking_warnings(task_dir, repo_root, state))
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

    for message in warnings:
        print(f"⚠️  {message}")

    print("✅ workflow-state 校验通过")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    repo_root = _resolve_route_repo_root(args)
    if repo_root is None:
        print(json.dumps({"error": "无法定位 repo root"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    embed_invalid_reason = detect_embed_invalid(repo_root)
    if embed_invalid_reason is not None:
        _route_result(None, "embed_invalid", embed_invalid_reason)
        return 0

    task_dir, status_code = _resolve_route_task_dir(args, repo_root)
    if task_dir is None:
        return status_code
    return _route_task_dir(task_dir, repo_root)


def cmd_repair(args: argparse.Namespace) -> int:
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

    state_path, state = load_state(task_dir_path)
    if state is not None:
        check_errors: list[str] = []
        validate_state_shape(state, check_errors)
        validate_execution_boundary(state, check_errors)
        validate_leaf_task(task_dir_path, state.get("stage"), check_errors)
        if not check_errors:
            if args.apply:
                candidate_stage = state.get("stage")
                if isinstance(candidate_stage, str) and candidate_stage in STAGES:
                    repaired = recover_repair_state(candidate_stage, state)
                    apply_repair_overrides(repaired, args)
                    repaired_errors: list[str] = []
                    validate_state_shape(repaired, repaired_errors)
                    validate_execution_boundary(repaired, repaired_errors)
                    validate_leaf_task(task_dir_path, candidate_stage, repaired_errors)
                    if repaired_errors:
                        print(
                            json.dumps(
                                {
                                    "status": "repair_blocked",
                                    "stage": candidate_stage,
                                    "blockers": repaired_errors,
                                    "message": "workflow-state.json 可读取，但规范化重建后仍不合法",
                                },
                                ensure_ascii=False,
                                indent=2,
                            )
                        )
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
    if candidate_stage is None and isinstance(state, dict):
        stage_value = state.get("stage")
        if stage_value in STAGES:
            candidate_stage = stage_value
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
                or "execution_authorized" in error
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

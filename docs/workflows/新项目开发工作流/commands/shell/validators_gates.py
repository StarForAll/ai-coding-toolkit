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
    L0_DIRECT_EXECUTION_MARKERS,
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
    find_task_creation_checklist_file,
    find_assessment_file,
    find_task_plan_file,
    find_missing_markers,
    is_placeholder_like,
    load_task_json,
    normalize_yes_no_field,
    read_json,
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


def _missing_required_sections(content: str, sections: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for section in sections:
        if not re.search(rf"^\s*##+\s*{re.escape(section)}\s*$", content, re.MULTILINE):
            missing.append(section)
    return missing


def _extract_section_body(content: str, heading: str) -> str:
    pattern = re.compile(
        rf"^\s*##+\s*{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^\s*##+\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return ""
    return match.group("body").strip()


def _has_section_heading(content: str, heading: str) -> bool:
    return bool(re.search(rf"^\s*##+\s*{re.escape(heading)}\s*$", content, re.MULTILINE))


def _normalize_section_body_for_comparison(body: str) -> str:
    normalized_lines = [line.strip() for line in body.splitlines() if line.strip()]
    return "\n".join(normalized_lines)


def _validate_equivalent_section_conflict(
    content: str,
    headings: tuple[str, ...],
    errors: list[str],
    *,
    document_name: str,
) -> str:
    present_bodies: list[tuple[str, str]] = []
    for heading in headings:
        if _has_section_heading(content, heading):
            present_bodies.append((heading, _extract_section_body(content, heading)))

    if len(present_bodies) > 1:
        normalized = {
            heading: _normalize_section_body_for_comparison(body)
            for heading, body in present_bodies
        }
        if len(set(normalized.values())) > 1:
            errors.append(
                f"{document_name} 同时存在 {' / '.join(headings)} 章节，但内容不一致；"
                "请保留单一事实源或同步两者"
            )

    for _heading, body in present_bodies:
        if body:
            return body
    return ""


def _extract_backticked_status_from_text(text: str) -> str | None:
    match = re.search(r"[：:]\s*`?(pass|fail|not run|not_run|not applicable|not_applicable|not needed|not_needed)`?", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower().replace(" ", "_")


def _has_status_marker(content: str) -> bool:
    return bool(re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE))


def _extract_structured_status(content: str, field_name: str) -> str | None:
    raw_value = extract_backticked_field(content, field_name)
    if raw_value is None:
        return None
    normalized = raw_value.strip().strip("`").lower().replace("-", "_").replace(" ", "_")
    if normalized in {"pass", "fail", "not_run", "not_applicable", "not_needed"}:
        return normalized
    return None


def _is_blocking_status(status: str | None, *, allow_not_run: bool = False) -> bool:
    if status == "pass":
        return False
    if allow_not_run and status == "not_run":
        return False
    if status in {"not_applicable", "not_needed"}:
        return False
    return status is not None


def _should_enforce_missing_gate_status() -> bool:
    return True


def _normalize_keyword(value: str) -> str:
    return value.strip().strip("`").strip().lower().replace("-", "_").replace(" ", "_")


def _normalized_nonempty_lines(section_body: str) -> list[str]:
    values: list[str] = []
    for raw_line in section_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*+]\s*", "", line).strip()
        if not line:
            continue
        values.append(_normalize_keyword(line))
    return values


def _extract_single_keyword_from_section(
    content: str,
    heading: str,
    valid_values: set[str],
    *,
    field_name: str | None = None,
) -> str | None:
    if field_name is not None:
        raw_value = extract_backticked_field(content, field_name)
        if raw_value is not None:
            normalized = _normalize_keyword(raw_value)
            if normalized in valid_values:
                return normalized
            return None

    lines = _normalized_nonempty_lines(_extract_section_body(content, heading))
    matched = {line for line in lines if line in valid_values}
    if len(matched) == 1 and len(lines) == 1:
        return next(iter(matched))
    return None


def _repo_root_from_task_dir(task_dir: Path) -> Path:
    if task_dir.parent.name == "tasks" and task_dir.parent.parent.name == ".trellis":
        return task_dir.parent.parent.parent
    return task_dir.parent.parent


def _resolve_plan_gate_owner_dir(task_dir: Path) -> Path:
    repo_root = _repo_root_from_task_dir(task_dir)
    plan_path = find_task_plan_file(task_dir, repo_root)
    if plan_path is not None:
        return plan_path.parent
    checklist_path = find_task_creation_checklist_file(task_dir, repo_root)
    if checklist_path is not None:
        return checklist_path.parent
    return task_dir


def _parse_task_reference_tokens(raw_value: str) -> set[str]:
    tokens: set[str] = set()
    for raw_token in re.split(r"[,\n;]+", raw_value):
        token = raw_token.strip().strip("`").strip()
        if not token or token.lower() in {"none", "n/a", "na"}:
            continue
        if token.startswith(".trellis/tasks/") or token.startswith("tasks/"):
            tokens.add(Path(token).name)
            continue
        if "/" not in token and "." not in token:
            tokens.add(token)
    return tokens


def _resolve_task_level_check_dir_from_field(
    task_dir: Path,
    raw_value: str | None,
    *,
    fallback_dir: Path | None = None,
) -> Path | None:
    if raw_value is None:
        return None

    normalized = raw_value.strip().strip("`").strip()
    lowered = normalized.lower().replace("-", "_").replace(" ", "_")
    if lowered == "current_active_task":
        return fallback_dir
    if lowered == "self":
        return task_dir
    if lowered == "parent":
        task_data = load_task_json(task_dir)
        parent_name = task_data.get("parent") if isinstance(task_data, dict) else None
        if isinstance(parent_name, str) and parent_name.strip():
            return task_dir.parent / parent_name.strip()
        return None

    repo_root = _repo_root_from_task_dir(task_dir)
    if normalized.startswith(".trellis/tasks/") or normalized.startswith("tasks/"):
        return repo_root / normalized.replace("tasks/", ".trellis/tasks/", 1) if normalized.startswith("tasks/") else repo_root / normalized

    if "/" not in normalized:
        return task_dir.parent / normalized

    return None


def _resolve_delivery_check_task_dir(task_dir: Path) -> Path | None:
    fallback_dir = _resolve_task_level_check_task_dir(task_dir)
    report_path = task_dir / "project-audit.md"
    if not report_path.is_file():
        return fallback_dir

    content = report_path.read_text(encoding="utf-8")
    task_level_check_task_raw = extract_backticked_field(content, "task_level_check_task")
    if task_level_check_task_raw is None:
        return fallback_dir
    return _resolve_task_level_check_dir_from_field(
        task_dir,
        task_level_check_task_raw,
        fallback_dir=fallback_dir,
    )


def _extract_coverage_line(content: str) -> str | None:
    matrix_body = _extract_section_body(content, "Project-Level Verification Matrix")
    for raw_line in matrix_body.splitlines():
        if "project-task-coverage" in raw_line:
            return raw_line.strip()
    return None


def _parse_project_task_coverage(coverage_line: str | None) -> tuple[str | None, set[str], set[str], str | None]:
    if coverage_line is None:
        return None, set(), set(), None

    lowered = coverage_line.lower()
    coverage_mode: str | None = None
    covered_tasks: set[str] = set()
    exception_tasks: set[str] = set()
    blockers_state: str | None = None

    if "all code-related tasks complete" in lowered:
        coverage_mode = "all"
    elif "covers " in lowered and " only" in lowered:
        coverage_mode = "listed"
        match = re.search(r"covers\s+(.+?)\s+only", coverage_line, re.IGNORECASE)
        if match:
            covered_tasks = _parse_task_reference_tokens(match.group(1))
    else:
        covered_match = re.search(r"covered\s*=\s*([^;]+)", coverage_line, re.IGNORECASE)
        if covered_match:
            coverage_mode = "listed"
            covered_tasks = _parse_task_reference_tokens(covered_match.group(1))

    exceptions_match = re.search(r"exceptions\s*=\s*([^;]+)", coverage_line, re.IGNORECASE)
    if exceptions_match:
        exception_tasks = _parse_task_reference_tokens(exceptions_match.group(1))
    elif "no approved exceptions" in lowered or "exceptions=none" in lowered:
        exception_tasks = set()

    if "no delivery blockers" in lowered or "blockers=none" in lowered:
        blockers_state = "none"
    elif "blockers remain" in lowered or "delivery blockers remain" in lowered:
        blockers_state = "nonempty"

    return coverage_mode, covered_tasks, exception_tasks, blockers_state


def _validate_project_audit_results_consistency(content: str, errors: list[str]) -> None:
    results_body = _extract_section_body(content, "Project-Level Verification Results")
    gate_status = _extract_project_audit_gate_status(content)
    coverage_line = _extract_coverage_line(content)
    _coverage_mode, _covered_tasks, _exception_tasks, blockers_state = _parse_project_task_coverage(coverage_line)

    if gate_status == "pass":
        for label in ("项目级统一代码漏洞检测", "项目级统一代码质量总检"):
            for raw_line in results_body.splitlines():
                if label not in raw_line:
                    continue
                line_status = _extract_backticked_status_from_text(raw_line)
                if line_status == "fail":
                    errors.append(
                        f"project-audit.md 的 `{label}` 结果为 fail，但 `project_audit_gate_status` 仍是 `pass`"
                    )
                    break
        if blockers_state == "nonempty":
            errors.append(
                "project-audit.md 的 `project-task-coverage` 仍声明存在 blockers，但 `project_audit_gate_status` 仍是 `pass`"
            )


def _validate_delivery_results_consistency(task_dir: Path, errors: list[str]) -> None:
    acceptance_path = task_dir / "delivery" / "acceptance.md"
    if not acceptance_path.is_file():
        return
    content = acceptance_path.read_text(encoding="utf-8")
    gate_status = _extract_delivery_gate_status(content)
    if gate_status != "pass":
        return

    current_status_body = _extract_section_body(content, "当前交付状态")
    acceptance_gate_body = _extract_section_body(content, "Acceptance Gate")
    combined = "\n".join(part for part in (current_status_body, acceptance_gate_body) if part)
    for raw_line in combined.splitlines():
        line_status = _extract_backticked_status_from_text(raw_line)
        if line_status == "fail":
            errors.append(
                "delivery/acceptance.md 的 Acceptance Gate / 当前交付状态包含 fail，但 `delivery_gate_status` 仍是 `pass`"
            )
            break


def _has_action_decision_marker(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in ("adopted", "rejected", "采纳", "拒绝"))


def _project_audit_tmp_root(task_dir: Path) -> Path:
    return _repo_root_from_task_dir(task_dir) / "tmp" / "multi-cli-review" / f"{task_dir.name}-project-audit"


def _review_gate_tmp_root(task_dir: Path) -> Path:
    return _repo_root_from_task_dir(task_dir) / "tmp" / "multi-cli-review" / task_dir.name


def _extract_check_gate_status(content: str) -> str | None:
    return _extract_structured_status(content, "check_gate_status")


def _extract_project_audit_gate_status(content: str) -> str | None:
    return _extract_structured_status(content, "project_audit_gate_status")


def _extract_review_gate_closure_status(content: str) -> str | None:
    return _extract_structured_status(content, "review_gate_closure_status")


def _extract_delivery_gate_status(content: str) -> str | None:
    return _extract_structured_status(content, "delivery_gate_status")


def _extract_finish_work_gate_status(content: str) -> str | None:
    return _extract_structured_status(content, "finish_work_gate_status")


def _task_plan_declares_project_audit(plan_path: Path) -> bool:
    content = plan_path.read_text(encoding="utf-8")
    if _project_audit_tasks_from_plan(plan_path):
        return True
    return "PROJECT-AUDIT" in content or "project-audit" in content.lower()


def _project_audit_tasks_from_plan(plan_path: Path) -> list[str]:
    tasks: list[str] = []
    for raw_line in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if ".trellis/tasks/" not in line or not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 2:
            continue
        task_path = columns[0]
        task_type = columns[1].lower().replace("_", "-").strip()
        if task_type != "project-audit":
            continue
        tasks.append(Path(task_path).name)
    return tasks


def _resolve_task_level_check_task_dir(task_dir: Path) -> Path:
    if (task_dir / CHECK_MD_FILE).is_file():
        return task_dir
    task_data = load_task_json(task_dir)
    if not isinstance(task_data, dict):
        return task_dir
    parent_name = task_data.get("parent")
    if not isinstance(parent_name, str) or not parent_name.strip():
        return task_dir
    parent_dir = task_dir.parent / parent_name.strip()
    if (parent_dir / CHECK_MD_FILE).is_file():
        return parent_dir
    return task_dir


def _code_related_task_rows_from_plan(plan_path: Path) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for raw_line in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if ".trellis/tasks/" not in line or not line.startswith("|"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 3:
            continue
        task_path = columns[0]
        task_type = columns[1].lower()
        project_domain = columns[2]
        note = columns[3] if len(columns) > 3 else ""
        rows.append((task_path, task_type, project_domain, note))
    return rows


def _task_row_is_code_related(task_type: str, project_domain: str, note: str = "") -> bool:
    normalized_type = task_type.strip().lower()
    normalized_domain = project_domain.strip().lower()
    normalized_note = note.strip().lower()

    explicit_markers = (
        ("`code_related`: `yes`", True),
        ("`code_related`: `no`", False),
        ("`code_related_task`: `yes`", True),
        ("`code_related_task`: `no`", False),
        ("code_related=yes", True),
        ("code_related=no", False),
        ("code-related=yes", True),
        ("code-related=no", False),
    )
    for marker, result in explicit_markers:
        if marker in normalized_note:
            return result

    if normalized_type == "project-audit":
        return False
    if normalized_type == "implementation":
        return True
    if normalized_type in {"frontend", "backend", "feature", "bugfix", "fix", "refactor"}:
        return True

    code_markers = (
        "代码相关",
        "code-related",
        "code related",
        "研发",
        "engineering",
        "开发",
        "迁移",
        "migration",
    )
    haystack = " ".join(part for part in (normalized_type, normalized_domain, normalized_note) if part)
    if any(marker in haystack for marker in code_markers):
        return True

    performance_security_positive_markers = (
        "性能优化",
        "性能回归",
        "性能修复",
        "performance optimization",
        "performance optimise",
        "performance optimize",
        "performance regression fix",
        "security hardening",
        "security fix",
        "security remediation",
        "安全加固",
        "安全修复",
        "安全整改",
    )
    if any(marker in haystack for marker in performance_security_positive_markers):
        return True

    return False


def _validate_project_audit_mode(content: str, errors: list[str]) -> None:
    mode = _extract_single_keyword_from_section(
        content,
        "Mode",
        {"formal", "pre_audit"},
        field_name="project_audit_mode",
    )
    if mode == "formal":
        return
    if mode == "pre_audit":
        errors.append("project-audit.md 当前仍是 `pre-audit`；预审不能作为正式 project-audit 出口")
        return
    errors.append("project-audit.md 的 `Mode` 未声明合法值；只能是 `formal` 或 `pre-audit`")


def _normalize_project_audit_check_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().strip("`").lower().replace("-", "_").replace(" ", "_")
    if normalized in {"pass", "fail", "not_run", "not_needed"}:
        return normalized
    return None


def _validate_project_audit_evidence(content: str, errors: list[str]) -> None:
    matrix_body = _extract_section_body(content, "Project-Level Verification Matrix")
    required_matrix_markers = (
        "project-task-coverage",
        "统一代码漏洞检测",
        "统一代码质量总检",
    )
    missing_matrix = [marker for marker in required_matrix_markers if marker not in matrix_body]
    if missing_matrix:
        errors.append(
            "project-audit.md 的 Project-Level Verification Matrix 缺少必要聚合证据字段: "
            + ", ".join(missing_matrix)
        )

    results_body = _extract_section_body(content, "Project-Level Verification Results")
    if not _has_status_marker(results_body):
        errors.append(
            "project-audit.md 的 Project-Level Verification Results 缺少真实验证结论（pass / fail / not run）"
        )

    coverage_line = _extract_coverage_line(content)
    if coverage_line is None:
        errors.append(
            "project-audit.md 的 Project-Level Verification Matrix 缺少 `project-task-coverage` 行"
        )


def _validate_project_audit_task_plan_completion(task_dir: Path, errors: list[str]) -> None:
    repo_root = _repo_root_from_task_dir(task_dir)
    plan_path = find_task_plan_file(task_dir, repo_root)
    if plan_path is None:
        errors.append(
            "formal project-audit 缺少 task_plan.md；"
            "无法证明全部代码相关任务已完成，不得作为正式 project-audit 出口"
        )
        return

    code_related_rows = [
        (task_path, task_type, project_domain, note)
        for task_path, task_type, project_domain, note in _code_related_task_rows_from_plan(plan_path)
        if _task_row_is_code_related(task_type, project_domain, note)
    ]
    task_rows = [task_path for task_path, _task_type, _project_domain, _note in code_related_rows]
    expected_tasks = {Path(task_path).name for task_path in task_rows if Path(task_path).name != task_dir.name}

    coverage_line = _extract_coverage_line((task_dir / "project-audit.md").read_text(encoding="utf-8"))
    coverage_mode, covered_tasks, exception_tasks, _blockers_state = _parse_project_task_coverage(coverage_line)
    effective_covered = expected_tasks - exception_tasks
    if coverage_mode == "listed":
        if covered_tasks != effective_covered:
            errors.append(
                "project-audit.md 的 `project-task-coverage` 与 task_plan.md 中应覆盖的代码相关任务集合不一致"
            )
    elif coverage_mode == "all":
        if exception_tasks and not exception_tasks.issubset(expected_tasks):
            errors.append(
                "project-audit.md 的 `project-task-coverage` 例外项包含 task_plan.md 中不存在的任务"
            )

    for task_path in task_rows:
        task_name = Path(task_path).name
        if task_name == task_dir.name:
            continue
        referenced_dir = task_dir.parent / task_name
        task_data = load_task_json(referenced_dir)
        if task_data is None:
            errors.append(
                f"task_plan.md 引用的代码相关任务不存在或不可读: {task_path}"
            )
            continue
        task_status = task_data.get("status")
        if task_status == "completed":
            continue

        state_data = read_json(referenced_dir / "workflow-state.json")
        stage = state_data.get("stage") if isinstance(state_data, dict) else None
        stage_ready = stage in {"check", "review-gate", "project-audit", "delivery"}
        check_errors: list[str] = []
        validate_check_gate(referenced_dir, check_errors, downstream_stage="project-audit")
        if stage_ready and not check_errors:
            continue

        detail = f"status={task_status}"
        if stage is not None:
            detail += f", stage={stage}"
        if check_errors:
            detail += f", check_gate={' / '.join(check_errors)}"
        errors.append(
            f"task_plan.md 中代码相关任务未全部完成: {task_name} ({detail})"
        )


def _validate_project_audit_multi_cli_review_artifacts(task_dir: Path, content: str, errors: list[str]) -> None:
    process_dir = task_dir / "project-audit"
    root_tmp = _project_audit_tmp_root(task_dir)

    reviewer_commands = sorted(process_dir.glob("reviewer-commands-round-*.md"))
    action_rounds = sorted(process_dir.glob("action-round-*.md"))
    review_round_dirs = sorted(root_tmp.glob("review-round-*"))
    summary_rounds = sorted(root_tmp.glob("summary-round-*.md"))
    action_file = root_tmp / "action.md"

    multi_cli_markers = (
        "multi-cli-review",
        "reviewer-commands-round-",
        "reviewer:",
        "review-round-",
        "action-round-",
        "summary-round-",
    )
    multi_cli_used = any(marker in content for marker in multi_cli_markers)
    if not multi_cli_used and not reviewer_commands and not action_rounds and not review_round_dirs and not summary_rounds and not action_file.is_file():
        return

    if not reviewer_commands:
        errors.append("project-audit 使用了 multi-cli-review 证据，但缺少 project-audit/reviewer-commands-round-<N>.md")

    if not review_round_dirs:
        errors.append(
            "project-audit 使用了 multi-cli-review 证据，但缺少 "
            f"{root_tmp.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()}/review-round-<N>/"
        )
    else:
        for review_round_dir in review_round_dirs:
            reports = sorted(review_round_dir.glob("*.md"))
            if len(reports) < 2:
                errors.append(
                    f"{review_round_dir.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} reviewer 报告不足 2 份；"
                    "project-audit 内部 full 审查未完成"
                )

    if review_round_dirs and not summary_rounds:
        errors.append(
            "project-audit 已存在 reviewer 报告，但缺少 tmp/multi-cli-review/<task-id>-project-audit/summary-round-<N>.md"
        )
    for summary_round in summary_rounds:
        summary_content = summary_round.read_text(encoding="utf-8")
        if not _has_status_marker(summary_content):
            errors.append(
                f"{summary_round.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺少真实验证/采纳结论（pass / fail / not run）"
            )

    if review_round_dirs and not action_rounds and not action_file.is_file():
        errors.append(
            "project-audit 已存在 reviewer 报告，但缺少 project-audit/action-round-<N>.md 或 "
            "tmp/multi-cli-review/<task-id>-project-audit/action.md"
        )

    for action_round in action_rounds:
        action_content = action_round.read_text(encoding="utf-8")
        if not _has_action_decision_marker(action_content):
            errors.append(
                f"{action_round.relative_to(task_dir).as_posix()} 缺少采纳/拒绝决策记录；无法证明 project-audit 闭环"
            )

    if action_file.is_file():
        action_content = action_file.read_text(encoding="utf-8")
        if not _has_action_decision_marker(action_content):
            errors.append(
                f"{action_file.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺少采纳/拒绝决策记录；无法证明 project-audit 闭环"
            )


def _validate_project_audit_delivery_linkage(
    task_dir: Path,
    content: str,
    errors: list[str],
    *,
    check_task_dir: Path | None = None,
) -> None:
    task_level_check_task_raw = extract_backticked_field(content, "task_level_check_task")
    explicit_check_dir = _resolve_task_level_check_dir_from_field(
        task_dir,
        task_level_check_task_raw,
        fallback_dir=check_task_dir or task_dir,
    )
    if task_level_check_task_raw is None:
        errors.append(
            "project-audit.md 缺少 `task_level_check_task` 字段；必须显式绑定当前任务级 check 证据所属 task"
        )
    elif explicit_check_dir is None or not explicit_check_dir.is_dir():
        errors.append(
            "project-audit.md 的 `task_level_check_task` 无法解析到合法 task 目录"
        )
    else:
        validate_check_gate(explicit_check_dir, errors, for_delivery=True, downstream_stage="delivery")

    code_change_raw = extract_backticked_field(content, "project_audit_code_changes")
    code_changes = normalize_yes_no_field(code_change_raw)
    if code_change_raw is None:
        errors.append("project-audit.md 缺少 `project_audit_code_changes` 字段")
    elif code_changes is None:
        errors.append("project-audit.md 的 `project_audit_code_changes` 只能填写 `yes` / `no`")

    task_level_check_raw = extract_backticked_field(content, "task_level_check_status")
    task_level_check_status = _normalize_project_audit_check_status(task_level_check_raw)
    if task_level_check_raw is None:
        errors.append("project-audit.md 缺少 `task_level_check_status` 字段")
        return
    if task_level_check_status is None:
        rendered = task_level_check_raw or "(missing)"
        errors.append(
            f"project-audit.md 的 `task_level_check_status` 非法: {rendered!r}；"
            "只能填写 `pass` / `fail` / `not_run` / `not_needed`"
        )
        return

    if code_changes is True:
        errors.append(
            "project-audit.md 标记本轮存在代码修改；project-audit 后不得直接进入 delivery，"
            "必须先回到任务级 check 重新闭环"
        )
    if code_changes is False and task_level_check_status not in {"pass", "not_needed"}:
        errors.append(
            "project-audit.md 标记本轮无代码修改时，`task_level_check_status` 只能为 `pass` 或 `not_needed`"
        )


def _validate_project_audit_non_check_exit(
    content: str,
    errors: list[str],
    *,
    target_stage: str,
) -> None:
    if target_stage == "check":
        return

    code_change_raw = extract_backticked_field(content, "project_audit_code_changes")
    code_changes = normalize_yes_no_field(code_change_raw)
    if code_change_raw is None:
        errors.append(
            "project-audit.md 缺少 `project_audit_code_changes` 字段；"
            f"离开 project-audit 进入 {target_stage} 前必须明确本轮是否发生代码修改"
        )
        return
    if code_changes is None:
        errors.append("project-audit.md 的 `project_audit_code_changes` 只能填写 `yes` / `no`")
        return
    if code_changes is True:
        errors.append(
            "project-audit.md 标记本轮存在代码修改；"
            f"不得从 project-audit 直接进入 {target_stage}，必须先回到任务级 check 重新闭环"
        )
        return


def _validate_project_audit_task_level_handoff(
    task_dir: Path,
    content: str,
    errors: list[str],
    *,
    target_stage: str,
) -> None:
    if target_stage not in {"check", "review-gate"}:
        return

    task_level_check_task_raw = extract_backticked_field(content, "task_level_check_task")
    resolved_dir = _resolve_task_level_check_dir_from_field(
        task_dir,
        task_level_check_task_raw,
        fallback_dir=_resolve_task_level_check_task_dir(task_dir),
    )
    if resolved_dir is None or resolved_dir == task_dir:
        return

    repo_root = _repo_root_from_task_dir(task_dir)
    target_dir = resolved_dir.relative_to(repo_root).as_posix()
    errors.append(
        "project-audit.md 已将任务级 check 证据绑定到 "
        f"{target_dir}；`{target_stage}` 是任务级阶段，必须先执行 "
        f"`python3 ./.trellis/scripts/task.py start {target_dir}` 把当前 active task 切回该 task，"
        "再在那个 task 上执行阶段切换，不能在项目级 PROJECT-AUDIT carrier 上直接进入任务级阶段"
    )


def _review_gate_capability_gap_allows_not_run(
    task_dir: Path,
    report_path: Path,
    content: str,
    errors: list[str],
    *,
    decision: str | None,
    mode: str | None,
) -> bool:
    if decision != "recommended" or mode != "lite":
        return False
    if _extract_review_gate_closure_status(content) != "not_run":
        return False

    gap_raw = extract_backticked_field(content, "review_gate_capability_gap")
    gap = normalize_yes_no_field(gap_raw)
    if gap_raw is None:
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 缺少 `review_gate_capability_gap`；"
            "当 review-gate 因能力缺口未执行时必须显式说明"
        )
        return False
    if gap is not True:
        rendered = gap_raw or "(missing)"
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 的 `review_gate_capability_gap` 必须为 `yes`，当前为 {rendered!r}"
        )
        return False

    ack_raw = extract_backticked_field(content, "review_gate_capability_gap_acknowledged_by_user")
    ack = normalize_yes_no_field(ack_raw)
    if ack_raw is None:
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 缺少 `review_gate_capability_gap_acknowledged_by_user`；"
            "当 review-gate 因能力缺口未执行时必须记录用户是否接受该残余风险"
        )
        return False
    if ack is not True:
        rendered = ack_raw or "(missing)"
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 的 `review_gate_capability_gap_acknowledged_by_user` 必须为 `yes`，当前为 {rendered!r}"
        )
        return False

    reason = extract_backticked_field(content, "review_gate_capability_gap_reason")
    if is_placeholder_like(reason):
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 缺少 `review_gate_capability_gap_reason`；"
            "必须说明缺失的能力、为何无法补齐，以及为何本轮允许带风险跳过"
        )
        return False
    return True


def _validate_required_formal_project_audit_for_delivery(
    task_dir: Path,
    repo_root: Path,
    errors: list[str],
    *,
    check_task_dir: Path,
) -> None:
    plan_path = find_task_plan_file(task_dir, repo_root)
    if plan_path is None or not _task_plan_declares_project_audit(plan_path):
        return

    project_audit_tasks = _project_audit_tasks_from_plan(plan_path)
    if not project_audit_tasks:
        errors.append(
            "task_plan.md 已声明 `PROJECT-AUDIT` / project-audit，但未提供结构化的 project-audit task 行；"
            "不得进入 delivery"
        )
        return

    matched = False
    first_candidate_errors: list[str] = []
    for task_name in project_audit_tasks:
        candidate_dir = task_dir.parent / task_name
        if not candidate_dir.is_dir():
            if not first_candidate_errors:
                first_candidate_errors.append(
                    f"task_plan.md 声明的 PROJECT-AUDIT task 不存在: {task_name}"
                )
            continue
        candidate_errors: list[str] = []
        _validate_formal_project_audit_task(
            candidate_dir,
            candidate_errors,
            check_task_dir=check_task_dir,
        )
        if not candidate_errors:
            matched = True
            break
        if not first_candidate_errors:
            first_candidate_errors.extend(candidate_errors)

    if not matched:
        errors.append(
            "task_plan.md 已声明 `PROJECT-AUDIT` / project-audit task，但至少需要一个候选 task 满足正式门禁；"
            "不得进入 delivery"
        )
        errors.extend(first_candidate_errors)


def _validate_review_gate_evidence(task_dir: Path, report_path: Path, content: str, errors: list[str]) -> None:
    valid_decisions = {"skip", "recommended", "required"}
    decision = _extract_single_keyword_from_section(
        content,
        "Decision",
        valid_decisions,
        field_name="review_gate_decision",
    )
    if decision is None:
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 的 Decision 非法；只能是 skip / recommended / required"
        )

    valid_modes = {"lite", "full"}
    mode = _extract_single_keyword_from_section(
        content,
        "Mode",
        valid_modes,
        field_name="review_gate_mode",
    )
    if mode is None:
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 的 Mode 非法；只能是 lite / full"
        )
    elif decision == "required" and mode != "full":
        errors.append(
            f"{report_path.relative_to(task_dir).as_posix()} 的 Decision=`required` 时，Mode 必须为 `full`"
        )

    capability_gap_not_run = _review_gate_capability_gap_allows_not_run(
        task_dir,
        report_path,
        content,
        errors,
        decision=decision,
        mode=mode,
    )

    review_gate_dir = task_dir / "review-gate"
    report_name = report_path.stem
    round_suffix = report_name.removeprefix("review-gate-round-")
    reviewer_commands = review_gate_dir / f"reviewer-commands-round-{round_suffix}.md"
    review_root = _review_gate_tmp_root(task_dir)
    summary_round = review_root / f"summary-round-{round_suffix}.md"
    action_round = review_gate_dir / f"action-round-{round_suffix}.md"
    action_file = review_root / "action.md"
    reviewer_reports_dir = review_root

    if decision in {"recommended", "required"} and not reviewer_commands.is_file() and not capability_gap_not_run:
        errors.append(
            f"{reviewer_commands.relative_to(task_dir).as_posix()} 缺失；review-gate 缺少 reviewer 指令包"
        )

    reviewer_reports = sorted(reviewer_reports_dir.glob(f"review-round-{round_suffix}/*.md"))
    if decision == "recommended" and mode == "lite" and not reviewer_reports and not capability_gap_not_run:
        errors.append(
            "recommended + lite 的 review-gate 缺少真实 reviewer 报告；"
            "不能只生成指令包就视为补充审查完成"
        )
    if mode == "full" and decision in {"recommended", "required"} and len(reviewer_reports) < 2:
        errors.append(
            f"{decision} + full 的 review-gate reviewer 报告不足 2 份；"
            "不能视为 full 审查已完成"
        )

    if mode == "full" and not summary_round.is_file():
        errors.append(
            f"{summary_round.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺失；full 模式 review-gate 必须沉淀聚合摘要"
        )

    if summary_round.is_file():
        summary_content = summary_round.read_text(encoding="utf-8")
        if not _has_status_marker(summary_content):
            errors.append(
                f"{summary_round.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺少真实验证/采纳结论（pass / fail / not run）"
            )

    if action_round.is_file():
        action_content = action_round.read_text(encoding="utf-8")
        if not _has_action_decision_marker(action_content):
            errors.append(
                f"{action_round.relative_to(task_dir).as_posix()} 缺少采纳/拒绝决策记录；无法证明修复后闭环"
            )
    elif action_file.is_file():
        action_content = action_file.read_text(encoding="utf-8")
        if not _has_action_decision_marker(action_content):
            errors.append(
                f"{action_file.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺少采纳/拒绝决策记录；无法证明修复后闭环"
            )
    elif decision in {"recommended", "required"} and reviewer_reports:
        errors.append(
            f"{action_file.relative_to(_repo_root_from_task_dir(task_dir)).as_posix()} 缺失；已有 reviewer 报告时必须沉淀采纳/拒绝闭环记录"
        )


def _validate_delivery_doc_contract(task_dir: Path, errors: list[str]) -> None:
    contract = {
        "acceptance.md": (
            "Acceptance Criteria Status",
            "Blocking Findings",
            "Acceptance Gate",
            "当前交付状态",
        ),
        "deliverables.md": (
            "Closeout Assets",
            "Verification Evidence",
            "Current Status",
            "Residual Risks",
        ),
        "transfer-checklist.md": (
            "当前事件允许移交什么",
            "当前事件禁止标记为已移交什么",
            "触发条件 / 付款 / 权限 / 证明材料是否齐备",
        ),
    }
    delivery_dir = task_dir / "delivery"
    for filename, sections in contract.items():
        file_path = delivery_dir / filename
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        missing_sections = _missing_required_sections(content, sections)
        if missing_sections:
            errors.append(
                f"delivery/{filename} 缺少必要章节: {', '.join(missing_sections)}；delivery 文档契约未满足"
            )
        elif not _has_status_marker(content):
            errors.append(
                f"delivery/{filename} 缺少真实状态结论（pass / fail / not run）；delivery 文档契约未满足"
            )

    retrospective_path = delivery_dir / "retrospective.md"
    if retrospective_path.is_file():
        retrospective_content = retrospective_path.read_text(encoding="utf-8")
        missing_sections = _missing_required_sections(
            retrospective_content,
            ("本轮验收", "返工", "摩擦点"),
        )
        if missing_sections:
            errors.append(
                f"delivery/retrospective.md 缺少必要章节: {', '.join(missing_sections)}；delivery 文档契约未满足"
            )


def validate_plan_gate(task_dir: Path, errors: list[str]) -> None:
    gate_owner_dir = _resolve_plan_gate_owner_dir(task_dir)
    checklist_path = gate_owner_dir / TASK_CREATION_CHECKLIST_FILE
    if checklist_path.is_file():
        content = checklist_path.read_text(encoding="utf-8")
        if "`task_creation_confirmed`" in content:
            if not re.search(r'`task_creation_confirmed`\s*[：:]\s*`?yes`?', content):
                errors.append(
                    "task_creation_checklist.md 存在但 task_creation_confirmed 未确认为 yes；"
                    "不得进入执行阶段"
                )
        plan_path = gate_owner_dir / TASK_PLAN_FILE
        if not plan_path.is_file():
            errors.append(
                "task_creation_checklist.md 存在但缺少 task_plan.md；"
                "计划产物不完整，不得进入执行阶段"
            )
    run_gate_validator(
        "plan-validate.py",
        [str(gate_owner_dir)],
        errors,
        label="plan-validate.py 结构验证",
    )
    run_gate_validator(
        "delivery-control-validate.py",
        ["--phase", "plan", "--task-dir", str(gate_owner_dir)],
        errors,
        label="delivery-control-validate.py plan 校验",
    )
    run_gate_validator(
        "ownership-proof-validate.py",
        ["--phase", "plan", "--task-dir", str(gate_owner_dir)],
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
    if for_delivery and decision == "recommended":
        accepted_raw = extract_backticked_field(content, "recommended_review_skip_accepted_by_user")
        accepted = normalize_yes_no_field(accepted_raw)
        if accepted_raw is None:
            errors.append(
                "check.md 的 `review_gate_decision`=`recommended`；"
                "直接进入 delivery 前必须记录 `recommended_review_skip_accepted_by_user`"
            )
        elif accepted is not True:
            rendered = accepted_raw or "(missing)"
            errors.append(
                "check.md 的 `review_gate_decision`=`recommended`；"
                f"`recommended_review_skip_accepted_by_user` 必须为 `yes`，当前为 {rendered!r}"
            )
        acceptance_note = extract_backticked_field(content, "recommended_review_skip_acceptance_note")
        if accepted is True and is_placeholder_like(acceptance_note):
            errors.append(
                "check.md 的 `review_gate_decision`=`recommended`；"
                "缺少 `recommended_review_skip_acceptance_note`，无法证明用户已结构化接受跳过风险"
            )


def validate_check_gate(
    task_dir: Path,
    errors: list[str],
    *,
    for_delivery: bool = False,
    downstream_stage: str = "review-gate",
) -> None:
    check_path = task_dir / CHECK_MD_FILE
    if not check_path.is_file():
        errors.append(f"缺少 check.md；check 阶段产物未生成，不得进入 {downstream_stage}")
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
            f"check 阶段产物不完整，不得进入 {downstream_stage}"
        )
        return

    if not re.search(r"\b(pass|fail|not run)\b|通过|失败|未运行", content, re.IGNORECASE):
        errors.append(
            "check.md 缺少真实验证结论（pass / fail / not run）；"
            f"check 阶段产物不完整，不得进入 {downstream_stage}"
        )
        return

    gate_status = _extract_check_gate_status(content)
    if gate_status is None:
        if _should_enforce_missing_gate_status():
            errors.append(
                "check.md 缺少 `check_gate_status`；"
                "必须明确当前任务级 check 是否允许进入后续阶段"
            )
    elif _is_blocking_status(gate_status):
        errors.append(
            f"check.md 的 `check_gate_status`={gate_status!r}；"
            "当前任务级 check 尚未闭环，不得进入后续阶段"
        )
    elif gate_status == "pass":
        verification_body = _validate_equivalent_section_conflict(
            content,
            ("Verification Results", "验证结果"),
            errors,
            document_name="check.md",
        )
        for raw_line in verification_body.splitlines():
            line_status = _extract_backticked_status_from_text(raw_line)
            if line_status == "fail":
                errors.append(
                    "check.md 的 Verification Results 包含 fail，但 `check_gate_status` 仍是 `pass`"
                )
                break

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

    gate_status = _extract_finish_work_gate_status(content)
    if gate_status is None:
        if _should_enforce_missing_gate_status():
            errors.append(
                "finish-work-checklist.md 缺少 `finish_work_gate_status`；"
                "必须明确当前收尾冻结证据是否允许进入 delivery / finish-work"
            )
    elif _is_blocking_status(gate_status, allow_not_run=False):
        errors.append(
            f"finish-work-checklist.md 的 `finish_work_gate_status`={gate_status!r}；"
            "收尾冻结证据仍有阻断项，不得进入 delivery"
        )


def validate_project_audit_gate(
    task_dir: Path,
    errors: list[str],
    *,
    require_delivery_linkage: bool = False,
    require_exit_gate_status: bool = False,
    check_task_dir: Path | None = None,
) -> None:
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
    missing_sections = _missing_required_sections(content, required_sections)

    if missing_sections:
        errors.append(
            f"project-audit.md 缺少必要章节: {', '.join(missing_sections)}；"
            "project-audit 阶段证据不完整，不得进入后续阶段"
        )
        return

    mode = _extract_single_keyword_from_section(
        content,
        "Mode",
        {"formal", "pre_audit"},
        field_name="project_audit_mode",
    )
    if mode is None:
        errors.append("project-audit.md 的 `Mode` 未声明合法值；只能是 `formal` 或 `pre-audit`")
        return
    if require_delivery_linkage:
        _validate_project_audit_mode(content, errors)
    _validate_project_audit_evidence(content, errors)
    _validate_project_audit_multi_cli_review_artifacts(task_dir, content, errors)
    gate_status = _extract_project_audit_gate_status(content)
    if gate_status is None:
        if (require_delivery_linkage or require_exit_gate_status) and _should_enforce_missing_gate_status():
            errors.append(
                "project-audit.md 缺少 `project_audit_gate_status`；"
                "必须明确当前项目级审查是否允许进入后续阶段"
            )
    elif (require_delivery_linkage or require_exit_gate_status) and gate_status == "not_run":
        if require_delivery_linkage:
            errors.append(
                "project-audit.md 的 `project_audit_gate_status`=`not_run`；"
                "该值仅作为旧记录兼容输入保留，当前会阻断 delivery。"
                "请完成本轮 project-audit 并将其更新为 `pass` 或 `fail`。"
            )
        else:
            errors.append(
                "project-audit.md 的 `project_audit_gate_status`=`not_run`；"
                "该值仅作为旧记录兼容输入保留，当前会阻断后续阶段。"
                "请完成本轮 project-audit 并将其更新为 `pass` 或 `fail`。"
            )
    elif (require_delivery_linkage or require_exit_gate_status) and _is_blocking_status(gate_status, allow_not_run=False):
        if require_delivery_linkage:
            errors.append(
                f"project-audit.md 的 `project_audit_gate_status`={gate_status!r}；"
                "当前项目级审查仍存在阻断项，不得进入 delivery"
            )
        else:
            errors.append(
                f"project-audit.md 的 `project_audit_gate_status`={gate_status!r}；"
                "当前项目级审查仍存在阻断项，不得进入后续阶段"
            )
    if mode == "formal":
        _validate_project_audit_task_plan_completion(task_dir, errors)
    _validate_project_audit_results_consistency(content, errors)
    if require_delivery_linkage:
        _validate_project_audit_delivery_linkage(
            task_dir,
            content,
            errors,
            check_task_dir=check_task_dir,
        )


def _validate_formal_project_audit_task(
    task_dir: Path,
    errors: list[str],
    *,
    check_task_dir: Path | None = None,
) -> None:
    validate_project_audit_gate(
        task_dir,
        errors,
        require_delivery_linkage=True,
        require_exit_gate_status=True,
        check_task_dir=check_task_dir,
    )
    task_data = load_task_json(task_dir)
    if task_data is None:
        errors.append(f"formal PROJECT-AUDIT task 不可读: {task_dir.name}")


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
    missing_sections = _missing_required_sections(
        content,
        ("Decision", "Trigger Evidence", "Mode", "Recommended Next Step"),
    )

    if missing_sections:
        errors.append(
            f"{reports[-1].relative_to(task_dir).as_posix()} 缺少必要章节: {', '.join(missing_sections)}；"
            "review-gate 阶段证据不完整，不得进入后续阶段"
        )
        return

    closure_status = _extract_review_gate_closure_status(content)
    if closure_status is None:
        if _should_enforce_missing_gate_status():
            errors.append(
                f"{reports[-1].relative_to(task_dir).as_posix()} 缺少 `review_gate_closure_status`；"
                "必须明确本轮补充审查是否允许关闭或进入下游阶段"
            )
    elif _is_blocking_status(closure_status, allow_not_run=True):
        errors.append(
            f"{reports[-1].relative_to(task_dir).as_posix()} 的 `review_gate_closure_status`={closure_status!r}；"
            "当前补充审查仍未闭环，不得进入后续阶段"
        )

    _validate_review_gate_evidence(task_dir, reports[-1], content, errors)


def validate_delivery_gate(task_dir: Path, errors: list[str], repo_root: Path | None = None) -> None:
    check_task_dir = _resolve_delivery_check_task_dir(task_dir)
    missing = [
        artifact.as_posix()
        for artifact in DELIVERY_ARTIFACTS
        if not (task_dir / artifact).is_file()
    ]
    if missing:
        errors.append(f"缺少交付产物: {', '.join(missing)}；delivery 阶段未完成")
    if check_task_dir is not None:
        validate_check_gate(check_task_dir, errors, for_delivery=True, downstream_stage="delivery")
    validate_finish_work_gate(task_dir, errors)
    _validate_delivery_doc_contract(task_dir, errors)
    acceptance_path = task_dir / "delivery" / "acceptance.md"
    if acceptance_path.is_file():
        acceptance_content = acceptance_path.read_text(encoding="utf-8")
        delivery_gate_status = _extract_delivery_gate_status(acceptance_content)
        if delivery_gate_status is None:
            if _should_enforce_missing_gate_status():
                errors.append(
                    "delivery/acceptance.md 缺少 `delivery_gate_status`；"
                    "必须明确当前交付事件是否允许进入最终收尾"
                )
        elif _is_blocking_status(delivery_gate_status, allow_not_run=False):
            errors.append(
                f"delivery/acceptance.md 的 `delivery_gate_status`={delivery_gate_status!r}；"
                "当前交付仍存在阻断项，不得通过 delivery 门禁"
            )
    elif not missing:
        errors.append("delivery/acceptance.md 缺失，无法判断 `delivery_gate_status`")
    _validate_delivery_results_consistency(task_dir, errors)
    if repo_root is not None:
        _validate_required_formal_project_audit_for_delivery(
            task_dir,
            repo_root,
            errors,
            check_task_dir=check_task_dir,
        )
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
            else:
                complexity_decision = extract_backticked_field(task_content, "complexity_decision")
                if "implementation" in allowed_targets and complexity_decision != "L0":
                    rendered_value = complexity_decision or "(missing)"
                    errors.append(
                        f"{TASK_PRD.as_posix()} 的 `complexity_decision`={rendered_value!r}；"
                        "brainstorm 仅允许 `L0` 直接进入 implementation，其他复杂度必须先进入 design/plan"
                    )
                elif "implementation" in allowed_targets:
                    missing_direct_execution_markers = find_missing_markers(
                        task_prd,
                        L0_DIRECT_EXECUTION_MARKERS,
                    )
                    if missing_direct_execution_markers:
                        errors.append(
                            f"{TASK_PRD.as_posix()} 缺少 L0 直达 implementation 的基线来源字段: "
                            + ", ".join(missing_direct_execution_markers)
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
    current_allowed_targets = design_path_candidates_from_state(current_state)
    if new_stage != current_stage and new_stage not in current_allowed_targets:
        rendered_allowed = ", ".join(sorted(current_allowed_targets)) or "(none)"
        errors.append(
            f"阶段切换被拒绝: {current_stage!r} 当前 allowed-next 子集不包含 {new_stage!r}；"
            f"允许值为 {rendered_allowed}"
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

    if current_stage == "project-audit" and new_stage in {"check", "review-gate"}:
        report_path = task_dir / "project-audit.md"
        if report_path.is_file():
            handoff_errors: list[str] = []
            _validate_project_audit_task_level_handoff(
                task_dir,
                report_path.read_text(encoding="utf-8"),
                handoff_errors,
                target_stage=new_stage,
            )
            if handoff_errors:
                errors.extend(handoff_errors)
                return

    if current_state.get("stage") == "brainstorm":
        allowed_targets = {
            new_stage
        } if new_stage in STAGES else design_path_candidates_from_state(candidate_state)
        validate_brainstorm_exit_gate(
            {
                **current_state,
                "_allowed_next_override": sorted(allowed_targets),
            },
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
        _validate_required_formal_project_audit_for_delivery(
            task_dir,
            repo_root,
            errors,
            check_task_dir=task_dir,
        )

    if current_stage == "project-audit":
        check_task_dir = _resolve_task_level_check_task_dir(task_dir)
        validate_project_audit_gate(
            task_dir,
            errors,
            require_delivery_linkage=(new_stage == "delivery"),
            require_exit_gate_status=True,
            check_task_dir=check_task_dir,
        )
        if new_stage not in {"check", "delivery"} and (task_dir / "project-audit.md").is_file():
            content = (task_dir / "project-audit.md").read_text(encoding="utf-8")
            _validate_project_audit_non_check_exit(content, errors, target_stage=new_stage)
        if new_stage == "delivery":
            _validate_required_formal_project_audit_for_delivery(
                task_dir,
                repo_root,
                errors,
                check_task_dir=check_task_dir,
            )

    if current_stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)
        if new_stage == "delivery":
            validate_check_gate(task_dir, errors, for_delivery=True, downstream_stage="delivery")
            _validate_required_formal_project_audit_for_delivery(
                task_dir,
                repo_root,
                errors,
                check_task_dir=task_dir,
            )


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
        validate_project_audit_gate(
            task_dir,
            errors,
            require_exit_gate_status=state.get("status") in EXIT_READY_STATUSES,
        )
    elif stage == "review-gate":
        validate_review_gate_gate(task_dir, errors)
    elif stage == "delivery":
        validate_delivery_gate(task_dir, errors, repo_root)

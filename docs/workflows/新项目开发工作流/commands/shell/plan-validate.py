#!/usr/bin/env python3
"""任务拆解摘要结构验证。

用法: python3 plan-validate.py [task_dir]

本脚本校验 `task_plan.md` 是否符合新的摘要型契约：
- 真实执行单元以 Trellis task 为主
- `task_plan.md` 只保留任务图、依赖与门禁摘要
- 不再使用旧版执行矩阵字段
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from project_id_utils import find_repo_root, require_installed_project_id, workflow_install_record_exists
from workflow_common import PLACEHOLDER_MARKERS


REQUIRED_SECTIONS = [
    "概述",
    "项目域执行策略",
    "Trellis Task 清单",
    "当前推荐执行任务（待确认）",
    "依赖关系",
    "任务粒度判断",
    "早期探针与骨架任务",
    "自动化策略摘要",
    "范围收敛与降级预案",
    "门禁摘要",
    "任务图摘要",
    "阶段出口快照",
]
OPTIONAL_SECTIONS = {"外部项目交付控制（如适用）"}
REQUIRED_TASK_COLUMNS = ["任务路径", "类型", "项目域", "说明"]
TASK_CREATION_CHECKLIST_FILE = "task_creation_checklist.md"
CHECKLIST_REQUIRED_SECTIONS = [
    "概述",
    "拟创建的 Trellis Task",
    "依赖与项目域草案",
    "人工确认清单",
    "人工确认结果",
]
CHECKLIST_RESULT_FIELDS = ("`task_creation_confirmed`", "`confirmed_scope`", "`post_mainline_performance_task`")
CHECKLIST_OPTIONAL_DECISION_FIELDS = (
    "`project_audit_required`",
    "`project_audit_required_reason`",
    "`ui_frontend_baseline_task_required`",
    "`ui_frontend_baseline_task_reason`",
)
LEGACY_MARKERS = [
    "任务执行矩阵",
    "当前可开始任务",
    "等待中任务",
    "推荐并行组",
    "并行属性",
    "冲突说明",
]
TASK_CARD_MARKERS = ("任务路径", "任务标题", "本轮目标", "本轮不做", "前置依赖", "验收锚点", "风险提醒", "推荐主执行 CLI")
LEAF_PRD_REQUIRED_SECTIONS = (
    ("Goal", "目标"),
    ("In Scope", "范围"),
    ("Out of Scope", "不做"),
    ("Acceptance Anchors", "验收锚点"),
    ("Preferred CLI", "推荐主执行 CLI"),
)
GRANULARITY_FIELDS = (
    "`granularity_decision`",
    "`decision_reason`",
    "`closure_target`",
    "`non_split_risk`",
    "`human_judgement_notes`",
)
EARLY_PROBE_FIELDS = ("`walking_skeleton_or_smoke`", "`packaging_skeleton`", "`performance_probe`")
AUTOMATION_FIELDS = ("`ci_strategy`", "`local_vs_ci_boundary`")
SCOPE_FIELDS = ("`kill_criteria`", "`p1_downgrade_candidates`")
EXIT_SNAPSHOT_FIELDS = ("`frozen_lanes`", "`current_recommended_task`", "`open_blockers`", "`task_creation_confirmed`", "`reopen_conditions`")
PERFORMANCE_TASK_LABEL = "性能回归与优化任务"
PROJECT_AUDIT_MARKERS = ("PROJECT-AUDIT", "project-audit")
PROJECT_AUDIT_ORDER_MARKERS = ("不得早于", "不早于")
UI_BASELINE_TASK_LABEL = "UI -> 首版代码界面"


def print_result(ok: bool, success: str, failure: str) -> int:
    if ok:
        print(f"✅ {success}")
        return 1
    print(f"❌ {failure}")
    return 0


def find_section_lines(lines: list[str], title: str) -> list[str]:
    start = None
    heading = f"## {title}"
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return []

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].strip().startswith("## "):
            end = index
            break
    return lines[start:end]


def parse_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def extract_table(section_lines: list[str]) -> tuple[list[str], list[list[str]]]:
    table_lines = [line for line in section_lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return [], []
    header = parse_markdown_row(table_lines[0])
    rows = [parse_markdown_row(line) for line in table_lines[2:]]
    return header, rows


def has_meaningful_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return not is_placeholder_like(stripped)


def resolve_task_path(repo_root: Path, task_path: str) -> Path:
    normalized = task_path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("tasks/"):
        normalized = f".trellis/{normalized}"
    return repo_root / normalized


def load_task_parent(task_dir: Path) -> str | None:
    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return None
    match = re.search(r'"parent"\s*:\s*"([^"]+)"', task_json.read_text(encoding="utf-8"))
    if not match:
        return None
    parent_name = match.group(1).strip()
    return parent_name or None


def extract_task_card_value(section_lines: list[str], label: str) -> str:
    prefix = f"- {label}："
    for line in section_lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return ""


def find_matching_sections(lines: list[str], candidates: tuple[str, ...]) -> list[list[str]]:
    matches: list[list[str]] = []
    for title in candidates:
        section_lines = find_section_lines(lines, title)
        if section_lines:
            matches.append(section_lines)
    return matches


def is_placeholder_like(text: str) -> bool:
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


def has_meaningful_section_content(section_lines: list[str]) -> bool:
    meaningful_lines = [line.strip().lstrip("-").strip() for line in section_lines if line.strip()]
    if not meaningful_lines:
        return False
    return any(line and not is_placeholder_like(line) for line in meaningful_lines)


def section_text(section_lines: list[str]) -> str:
    return "\n".join(section_lines)


def validate_structured_fields(section_lines: list[str], fields: tuple[str, ...], section_title: str) -> tuple[bool, str]:
    text = section_text(section_lines)
    missing_fields = [field for field in fields if field not in text]
    if missing_fields:
        return False, f"{section_title} 缺少结构化字段: {', '.join(missing_fields)}"

    invalid_fields: list[str] = []
    for field in fields:
        pattern = rf"{re.escape(field)}\s*[：:]\s*(.+)"
        match = re.search(pattern, text)
        if not match or is_placeholder_like(match.group(1)):
            invalid_fields.append(field)
    if invalid_fields:
        return False, f"{section_title} 存在空值或占位内容: {', '.join(invalid_fields)}"
    return True, f"{section_title} 结构化字段完整"


def validate_leaf_prd(prd_path: Path) -> tuple[bool, str]:
    if not prd_path.is_file():
        return False, "当前推荐执行任务对应 leaf task 缺少最小 prd.md"

    content = prd_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    missing_sections: list[str] = []
    empty_sections: list[str] = []
    for candidates in LEAF_PRD_REQUIRED_SECTIONS:
        label = " / ".join(candidates)
        section_groups = find_matching_sections(lines, candidates)
        if not section_groups:
            missing_sections.append(label)
            continue
        if not any(has_meaningful_section_content(section_lines) for section_lines in section_groups):
            empty_sections.append(label)

    if missing_sections:
        return False, f"当前推荐执行任务对应 leaf task 的 prd.md 缺少章节: {', '.join(missing_sections)}"
    if empty_sections:
        return False, f"当前推荐执行任务对应 leaf task 的 prd.md 章节仍是空值或占位内容: {', '.join(empty_sections)}"
    return True, "当前推荐执行任务对应 leaf task 已补齐最小 prd.md"


def field_has_expected_value(section_lines: list[str], field: str, expected: str) -> bool:
    pattern = rf"{re.escape(field)}\s*[：:]\s*`?([^`\n]+?)`?(?:\s|$)"
    match = re.search(pattern, section_text(section_lines))
    if not match:
        return False
    return match.group(1).strip().lower() == expected.lower()


def field_has_allowed_value(section_lines: list[str], field: str, allowed: tuple[str, ...]) -> bool:
    pattern = rf"{re.escape(field)}\s*[：:]\s*`?([^`\n]+?)`?(?:\s|$)"
    match = re.search(pattern, section_text(section_lines))
    if not match:
        return False
    return match.group(1).strip().lower() in {value.lower() for value in allowed}


def extract_field_value(section_lines: list[str], field: str) -> str | None:
    pattern = rf"{re.escape(field)}\s*[：:]\s*`?([^`\n]+?)`?(?:\s|$)"
    match = re.search(pattern, section_text(section_lines))
    if not match:
        return None
    return match.group(1).strip()


def post_mainline_performance_task_required(checklist_path: Path) -> tuple[bool | None, str | None]:
    if not checklist_path.is_file():
        return None, None
    content = checklist_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    result_section = find_section_lines(lines, "人工确认结果")
    raw_value = extract_field_value(result_section, "`post_mainline_performance_task`")
    if raw_value is None:
        return None, None
    normalized = raw_value.lower()
    if normalized == "yes":
        return True, None
    if normalized == "no":
        return False, extract_field_value(result_section, "`post_mainline_performance_task_reason`")
    return None, None


def validate_task_creation_checklist(checklist_path: Path) -> tuple[bool, str]:
    if not checklist_path.is_file():
        return False, "缺少 task_creation_checklist.md；真实创建 Trellis task 前的人工确认依据不存在"

    content = checklist_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    missing_sections = [title for title in CHECKLIST_REQUIRED_SECTIONS if not find_section_lines(lines, title)]
    if missing_sections:
        return False, f"task_creation_checklist.md 缺少章节: {', '.join(missing_sections)}"

    result_section = find_section_lines(lines, "人工确认结果")
    result_ok, result_message = validate_structured_fields(
        result_section,
        CHECKLIST_RESULT_FIELDS,
        "task_creation_checklist.md / 人工确认结果",
    )
    if not result_ok:
        return False, result_message

    if not field_has_expected_value(result_section, "`task_creation_confirmed`", "yes"):
        return False, "task_creation_checklist.md 未明确记录 `task_creation_confirmed: yes`，不得进入真实 task 创建后的验证"

    performance_required, performance_reason = post_mainline_performance_task_required(checklist_path)
    if performance_required is None:
        return False, "task_creation_checklist.md 的 `post_mainline_performance_task` 只能填写 `yes` / `no`"
    if performance_required:
        if PERFORMANCE_TASK_LABEL not in content:
            return False, "task_creation_checklist.md 未列出必选的 `性能回归与优化任务`"
    else:
        if is_placeholder_like(performance_reason):
            return False, "task_creation_checklist.md 已声明不需要 `性能回归与优化任务`，但缺少 `post_mainline_performance_task_reason`"

    project_audit_required = extract_field_value(result_section, "`project_audit_required`")
    if project_audit_required is not None and project_audit_required.lower() not in {"yes", "no"}:
        return False, "task_creation_checklist.md 的 `project_audit_required` 只能填写 `yes` / `no`"
    if project_audit_required == "yes":
        project_audit_reason = extract_field_value(result_section, "`project_audit_required_reason`")
        if is_placeholder_like(project_audit_reason):
            return False, "task_creation_checklist.md 已声明需要 `PROJECT-AUDIT`，但缺少 `project_audit_required_reason`"

    ui_baseline_required = extract_field_value(result_section, "`ui_frontend_baseline_task_required`")
    if ui_baseline_required is not None and ui_baseline_required.lower() not in {"yes", "no"}:
        return False, "task_creation_checklist.md 的 `ui_frontend_baseline_task_required` 只能填写 `yes` / `no`"
    if ui_baseline_required == "yes":
        ui_baseline_reason = extract_field_value(result_section, "`ui_frontend_baseline_task_reason`")
        if is_placeholder_like(ui_baseline_reason):
            return False, "task_creation_checklist.md 已声明需要 `UI -> 首版代码界面` task，但缺少 `ui_frontend_baseline_task_reason`"

    return True, "task_creation_checklist.md 已存在且人工确认结果完整"


def extract_yes_no_field(section_lines: list[str], field: str) -> bool | None:
    raw_value = extract_field_value(section_lines, field)
    if raw_value is None:
        return None
    lowered = raw_value.lower()
    if lowered == "yes":
        return True
    if lowered == "no":
        return False
    return None


def project_audit_required(checklist_path: Path) -> tuple[bool, str | None]:
    if not checklist_path.is_file():
        return False, None
    lines = checklist_path.read_text(encoding="utf-8").splitlines()
    result_section = find_section_lines(lines, "人工确认结果")
    required = extract_yes_no_field(result_section, "`project_audit_required`")
    reason = extract_field_value(result_section, "`project_audit_required_reason`")
    return required is True, reason


def ui_frontend_baseline_task_required(checklist_path: Path) -> tuple[bool, str | None]:
    if not checklist_path.is_file():
        return False, None
    lines = checklist_path.read_text(encoding="utf-8").splitlines()
    result_section = find_section_lines(lines, "人工确认结果")
    required = extract_yes_no_field(result_section, "`ui_frontend_baseline_task_required`")
    reason = extract_field_value(result_section, "`ui_frontend_baseline_task_reason`")
    return required is True, reason


def validate_project_audit_dependency(section_lines: list[str]) -> tuple[bool, str]:
    normalized_lines = [line.strip().replace("`", "") for line in section_lines if line.strip()]
    if not normalized_lines:
        return False, "依赖关系章节为空，无法确认 PROJECT-AUDIT 的时序约束"

    for index, line in enumerate(normalized_lines):
        if not any(marker in line for marker in PROJECT_AUDIT_MARKERS):
            continue
        window_start = max(0, index - 1)
        window_end = min(len(normalized_lines), index + 2)
        window_text = "\n".join(normalized_lines[window_start:window_end])
        has_order_constraint = any(marker in window_text for marker in PROJECT_AUDIT_ORDER_MARKERS) or (
            re.search(r"(?<!不)晚于", window_text) is not None
        )
        mentions_performance_task = PERFORMANCE_TASK_LABEL in window_text
        if has_order_constraint and mentions_performance_task:
            return True, "依赖关系已写明 PROJECT-AUDIT 不得早于 `性能回归与优化任务`"

    return False, "依赖关系未写明 PROJECT-AUDIT 不得早于 `性能回归与优化任务` 的约束"


def task_plan_declares_project_audit(content: str) -> bool:
    return "PROJECT-AUDIT" in content or "project-audit" in content.lower()


def task_plan_mentions_ui_baseline(content: str) -> bool:
    return UI_BASELINE_TASK_LABEL in content


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print("用法: python3 plan-validate.py [task_dir]")
        print()
        print("校验 task_dir/task_plan.md 是否符合摘要型任务拆解契约。")
        print("未传 task_dir 时默认使用当前目录。")
        return 0

    task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    repo_root = find_repo_root(task_dir.resolve())
    if repo_root is None:
        print("❌ 无法定位 repo root，不能读取 workflow-installed.json project_id")
        return 1
    if workflow_install_record_exists(repo_root):
        try:
            require_installed_project_id(repo_root, "plan-validate.py")
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return 1
    plan_file = task_dir / "task_plan.md"
    checklist_file = task_dir / TASK_CREATION_CHECKLIST_FILE

    print("=== 任务拆解摘要结构验证 ===")

    checklist_ok, checklist_message = validate_task_creation_checklist(checklist_file)
    performance_task_required, _ = post_mainline_performance_task_required(checklist_file)
    project_audit_is_required, _project_audit_reason = project_audit_required(checklist_file)
    ui_baseline_required, _ui_baseline_reason = ui_frontend_baseline_task_required(checklist_file)
    checks = 1
    passed = print_result(
        checklist_ok,
        "task_creation_checklist.md 已存在且已完成真实 task 创建前人工确认",
        checklist_message,
    )

    if not plan_file.exists():
        print("❌ task_plan.md 不存在")
        return 1
    print("✅ task_plan.md 存在")

    content = plan_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    missing_sections = [title for title in REQUIRED_SECTIONS if not find_section_lines(lines, title)]
    checks += 1
    passed += print_result(
        not missing_sections,
        "包含新的摘要型章节结构",
        f"缺少章节: {', '.join(missing_sections)}",
    )

    has_legacy_markers = any(marker in content for marker in LEGACY_MARKERS)
    checks += 1
    passed += print_result(
        not has_legacy_markers,
        "未残留旧版执行矩阵字段",
        "仍包含旧版执行矩阵字段（任务执行矩阵 / 当前可开始任务 / 推荐并行组 等）",
    )

    lane_section = "\n".join(find_section_lines(lines, "项目域执行策略"))
    has_lane_rule = "串行" in lane_section and "不自动续跑" in lane_section
    checks += 1
    passed += print_result(
        has_lane_rule,
        "项目域执行策略已写清串行与不自动续跑",
        "项目域执行策略未写清“域内串行、不自动续跑”",
    )

    gates_section = "\n".join(find_section_lines(lines, "门禁摘要"))
    has_gate_summary = "项目级全局门禁" in gates_section and "before-dev.md" in gates_section
    checks += 1
    passed += print_result(
        has_gate_summary,
        "门禁摘要已区分项目级与 task 级门禁",
        "门禁摘要缺少项目级全局门禁或 before-dev.md 说明",
    )

    graph_section = "\n".join(find_section_lines(lines, "任务图摘要"))
    has_graph_summary = has_meaningful_text(graph_section) and ("→" in graph_section or "PROJECT-AUDIT" in graph_section)
    checks += 1
    passed += print_result(
        has_graph_summary,
        "任务图摘要已写明主链或终局任务",
        "任务图摘要为空，或未写主链/终局任务",
    )

    task_card_section = "\n".join(find_section_lines(lines, "当前推荐执行任务（待确认）"))
    task_card_lines = find_section_lines(lines, "当前推荐执行任务（待确认）")
    has_task_card = has_meaningful_text(task_card_section) and all(marker in task_card_section for marker in TASK_CARD_MARKERS)
    checks += 1
    passed += print_result(
        has_task_card,
        "当前推荐执行任务说明卡已完整填写",
        "当前推荐执行任务（待确认）缺少任务说明卡字段（任务路径/任务标题/本轮目标/本轮不做/前置依赖/验收锚点/风险提醒/推荐主执行 CLI）",
    )

    early_probe_section = find_section_lines(lines, "早期探针与骨架任务")
    early_probe_ok, early_probe_message = validate_structured_fields(
        early_probe_section,
        EARLY_PROBE_FIELDS,
        "早期探针与骨架任务",
    )
    checks += 1
    passed += print_result(
        early_probe_ok,
        "早期探针与骨架任务已写清 smoke / 打包骨架 / 性能探针",
        early_probe_message,
    )

    automation_section = find_section_lines(lines, "自动化策略摘要")
    automation_ok, automation_message = validate_structured_fields(
        automation_section,
        AUTOMATION_FIELDS,
        "自动化策略摘要",
    )
    checks += 1
    passed += print_result(
        automation_ok,
        "自动化策略摘要已写清 CI 方案与本地/CI 边界",
        automation_message,
    )

    scope_section = find_section_lines(lines, "范围收敛与降级预案")
    scope_ok, scope_message = validate_structured_fields(
        scope_section,
        SCOPE_FIELDS,
        "范围收敛与降级预案",
    )
    checks += 1
    passed += print_result(
        scope_ok,
        "范围收敛与降级预案已写清 kill criteria 与 P1 降级候选",
        scope_message,
    )

    exit_snapshot_section = find_section_lines(lines, "阶段出口快照")
    exit_snapshot_ok, exit_snapshot_message = validate_structured_fields(
        exit_snapshot_section,
        EXIT_SNAPSHOT_FIELDS,
        "阶段出口快照",
    )
    checks += 1
    passed += print_result(
        exit_snapshot_ok,
        "阶段出口快照已写清冻结 lanes、阻断项与 reopen 条件",
        exit_snapshot_message,
    )

    recommended_task_path = extract_task_card_value(task_card_lines, "任务路径")
    current_task_name = task_dir.name
    parent_task_name = load_task_parent(task_dir)
    recommended_task_prd_ok = False
    recommended_task_prd_message = "当前推荐执行任务对应 leaf task 缺少最小 prd.md"
    if recommended_task_path:
        recommended_task_dir = resolve_task_path(repo_root, recommended_task_path)
        if recommended_task_dir.name in {current_task_name, parent_task_name}:
            recommended_task_dir = task_dir
        recommended_task_prd_ok, recommended_task_prd_message = validate_leaf_prd(recommended_task_dir / "prd.md")

    checks += 1
    passed += print_result(
        recommended_task_prd_ok,
        "当前推荐执行任务对应 leaf task 已补齐最小 prd.md",
        recommended_task_prd_message,
    )

    task_section = find_section_lines(lines, "Trellis Task 清单")
    header, rows = extract_table(task_section)
    has_task_table = bool(header) and bool(rows)
    checks += 1
    passed += print_result(
        has_task_table,
        "Trellis Task 清单存在",
        "Trellis Task 清单缺少表头或数据行",
    )

    header_ok = header == REQUIRED_TASK_COLUMNS
    checks += 1
    passed += print_result(
        header_ok,
        "Trellis Task 清单列名正确",
        f"Trellis Task 清单列名应为: {' | '.join(REQUIRED_TASK_COLUMNS)}",
    )

    task_paths_ok = True
    meaningful_rows_ok = True
    project_audit_count = 0
    performance_task_count = 0
    if has_task_table and header_ok:
        for row in rows:
            if len(row) != len(header):
                meaningful_rows_ok = False
                task_paths_ok = False
                continue
            data = dict(zip(header, row))
            if not all(has_meaningful_text(data[col]) for col in REQUIRED_TASK_COLUMNS):
                meaningful_rows_ok = False
            task_path = data["任务路径"]
            resolved = resolve_task_path(repo_root, task_path)
            if not resolved.is_dir():
                task_paths_ok = False
            if data["类型"] == "project-audit":
                project_audit_count += 1
            row_text = " | ".join(row)
            if PERFORMANCE_TASK_LABEL in row_text:
                performance_task_count += 1

    checks += 1
    passed += print_result(
        meaningful_rows_ok,
        "Trellis Task 清单填写完整",
        "Trellis Task 清单存在空值或占位内容",
    )

    checks += 1
    passed += print_result(
        task_paths_ok,
        "Trellis Task 清单引用的任务目录真实存在",
        "Trellis Task 清单中存在不存在的任务路径",
    )

    checks += 1
    passed += print_result(
        project_audit_count <= 1,
        "project-audit 任务数量合法（0 或 1）",
        "Trellis Task 清单中的 project-audit 任务超过 1 个",
    )

    project_audit_declared = task_plan_declares_project_audit(content)
    checks += 1
    passed += print_result(
        (not project_audit_declared) or project_audit_count == 1,
        "PROJECT-AUDIT 声明与结构化 task 行保持一致",
        "任务图已声明 `PROJECT-AUDIT` / project-audit，但 Trellis Task 清单缺少唯一的 project-audit task 行",
    )

    checks += 1
    passed += print_result(
        (not project_audit_is_required) or project_audit_count == 1,
        "条件性必建 PROJECT-AUDIT 已落成真实 task",
        "task_creation_checklist.md 已声明当前轮必须生成 `PROJECT-AUDIT`，但 Trellis Task 清单缺少唯一的 project-audit task 行",
    )

    dependency_section = "\n".join(find_section_lines(lines, "依赖关系"))
    dependency_ok = has_meaningful_text(dependency_section)
    checks += 1
    passed += print_result(
        dependency_ok,
        "依赖关系章节已填写",
        "依赖关系章节为空或仍是占位内容",
    )

    ui_baseline_count = 0
    if has_task_table and header_ok:
        for row in rows:
            if len(row) != len(header):
                continue
            row_text = " | ".join(row)
            if UI_BASELINE_TASK_LABEL in row_text:
                ui_baseline_count += 1

    ui_baseline_summary_ok = (
        (UI_BASELINE_TASK_LABEL in gates_section or UI_BASELINE_TASK_LABEL in graph_section)
        and "design/frontend-ui-spec.md" in (gates_section + "\n" + graph_section)
    )
    checks += 1
    passed += print_result(
        (not ui_baseline_required) or ui_baseline_count == 1,
        "前端视觉首版基线 task 已落成真实 task",
        "task_creation_checklist.md 已声明需要 `UI -> 首版代码界面` task，但 Trellis Task 清单缺少唯一对应 task 行",
    )

    checks += 1
    passed += print_result(
        (not ui_baseline_required) or ui_baseline_summary_ok,
        "前端视觉首版基线链路已写清统一约束来源",
        "当前 plan 已声明存在前端视觉落地链路，但 `门禁摘要` / `任务图摘要` 未同时写清 `UI -> 首版代码界面` 与 `design/frontend-ui-spec.md`",
    )

    granularity_section = find_section_lines(lines, "任务粒度判断")
    granularity_ok, granularity_message = validate_structured_fields(
        granularity_section,
        GRANULARITY_FIELDS,
        "任务粒度判断",
    )
    checks += 1
    passed += print_result(
        granularity_ok,
        "任务粒度判断已写明是否继续细分与人工判断说明",
        granularity_message,
    )

    granularity_value_ok = field_has_allowed_value(
        granularity_section,
        "`granularity_decision`",
        ("split_further", "keep_current_granularity"),
    )
    checks += 1
    passed += print_result(
        granularity_value_ok,
        "`granularity_decision` 取值合法",
        "`granularity_decision` 只能填写 `split_further` 或 `keep_current_granularity`",
    )

    expected_performance_task_count = 1 if performance_task_required is not False else 0
    checks += 1
    passed += print_result(
        performance_task_count == expected_performance_task_count,
        (
            "Trellis Task 清单已包含唯一的后置 `性能回归与优化任务`"
            if performance_task_required is not False
            else "Trellis Task 清单已按适用性移除 `性能回归与优化任务`"
        ),
        (
            "Trellis Task 清单中缺少或重复定义 `性能回归与优化任务`"
            if performance_task_required is not False
            else "task_creation_checklist.md 已声明无需 `性能回归与优化任务`，但 Trellis Task 清单仍保留了该任务"
        ),
    )

    performance_dependency_ok = (
        PERFORMANCE_TASK_LABEL in dependency_section
        if performance_task_required is not False
        else PERFORMANCE_TASK_LABEL not in dependency_section
    )
    checks += 1
    passed += print_result(
        performance_dependency_ok,
        (
            "依赖关系已写明 `性能回归与优化任务` 的主干后置位置"
            if performance_task_required is not False
            else "依赖关系已按适用性移除 `性能回归与优化任务` 依赖"
        ),
        (
            "依赖关系未写明 `性能回归与优化任务` 的依赖位置"
            if performance_task_required is not False
            else "task_creation_checklist.md 已声明无需 `性能回归与优化任务`，但依赖关系仍包含该任务"
        ),
    )

    project_audit_dependency_ok = True
    project_audit_dependency_message = "当前任务图未声明 project-audit，可跳过 PROJECT-AUDIT 时序约束检查"
    if project_audit_count == 1 and performance_task_required is not False:
        project_audit_dependency_ok, project_audit_dependency_message = validate_project_audit_dependency(
            find_section_lines(lines, "依赖关系")
        )
    checks += 1
    passed += print_result(
        project_audit_dependency_ok,
        "依赖关系已写明 PROJECT-AUDIT 的性能任务后置约束",
        project_audit_dependency_message,
    )

    performance_graph_ok = (
        PERFORMANCE_TASK_LABEL in graph_section
        if performance_task_required is not False
        else PERFORMANCE_TASK_LABEL not in graph_section
    )
    checks += 1
    passed += print_result(
        performance_graph_ok,
        (
            "任务图摘要已包含 `性能回归与优化任务`"
            if performance_task_required is not False
            else "任务图摘要已按适用性移除 `性能回归与优化任务`"
        ),
        (
            "任务图摘要未包含 `性能回归与优化任务`"
            if performance_task_required is not False
            else "task_creation_checklist.md 已声明无需 `性能回归与优化任务`，但任务图摘要仍包含该任务"
        ),
    )

    performance_before_audit_ok = True
    if performance_task_required is not False and performance_graph_ok and "PROJECT-AUDIT" in graph_section:
        performance_index = graph_section.find(PERFORMANCE_TASK_LABEL)
        project_audit_index = graph_section.find("PROJECT-AUDIT")
        performance_before_audit_ok = performance_index <= project_audit_index
    checks += 1
    passed += print_result(
        performance_before_audit_ok,
        "任务图摘要已保证 `性能回归与优化任务` 不晚于 PROJECT-AUDIT",
        "任务图摘要中 `PROJECT-AUDIT` 早于 `性能回归与优化任务`，不符合主干后置优化要求",
    )

    print()
    print(f"验证结果: {passed}/{checks} 通过")
    print("说明: 本脚本校验摘要结构与任务路径存在性；依赖是否最优仍需人工复核。")

    if passed != checks:
        print("❌ task_plan.md 结构验证未通过，请补充后重试")
        return 1

    print("✅ task_plan.md 结构验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

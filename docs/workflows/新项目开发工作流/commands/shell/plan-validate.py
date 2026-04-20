#!/usr/bin/env python3
"""任务拆解摘要结构验证。

用法: python3 plan-validate.py [task_dir]

本脚本校验 `task_plan.md` 是否符合新的摘要型契约：
- 真实执行单元以 Trellis task 为主
- `task_plan.md` 只保留任务图、依赖与门禁摘要
- 不再使用旧版执行矩阵字段
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path


REQUIRED_SECTIONS = [
    "概述",
    "项目域执行策略",
    "Trellis Task 清单",
    "当前推荐执行任务（待确认）",
    "依赖关系",
    "门禁摘要",
    "任务图摘要",
]
OPTIONAL_SECTIONS = {"外部项目交付控制（如适用）"}
REQUIRED_TASK_COLUMNS = ["任务路径", "类型", "项目域", "说明"]
LEGACY_MARKERS = [
    "任务执行矩阵",
    "当前可开始任务",
    "等待中任务",
    "推荐并行组",
    "并行属性",
    "冲突说明",
]
PLACEHOLDER_MARKERS = ("待补充", "待定", "暂空", "后续补充", "TBD", "TODO", "FIXME", "...")
TASK_CARD_MARKERS = ("任务路径", "任务标题", "本轮目标", "本轮不做", "前置依赖", "验收锚点", "风险提醒", "推荐主执行 CLI")
LEAF_PRD_REQUIRED_SECTIONS = (
    ("Goal", "目标"),
    ("In Scope", "范围"),
    ("Out of Scope", "不做"),
    ("Acceptance Anchors", "验收锚点"),
    ("Preferred CLI", "推荐主执行 CLI"),
)


def print_result(ok: bool, success: str, failure: str) -> int:
    if ok:
        print(f"✅ {success}")
        return 1
    print(f"❌ {failure}")
    return 0


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while current != current.parent:
        if (current / ".trellis").is_dir():
            return current
        current = current.parent
    return start.resolve()


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


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print("用法: python3 plan-validate.py [task_dir]")
        print()
        print("校验 task_dir/task_plan.md 是否符合摘要型任务拆解契约。")
        print("未传 task_dir 时默认使用当前目录。")
        return 0

    task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    plan_file = task_dir / "task_plan.md"

    print("=== 任务拆解摘要结构验证 ===")

    if not plan_file.exists():
        print("❌ task_plan.md 不存在")
        return 1
    print("✅ task_plan.md 存在")

    repo_root = find_repo_root(task_dir)
    content = plan_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    checks = 0
    passed = 0

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

    recommended_task_path = extract_task_card_value(task_card_lines, "任务路径")
    recommended_task_prd_ok = False
    recommended_task_prd_message = "当前推荐执行任务对应 leaf task 缺少最小 prd.md"
    if recommended_task_path:
        recommended_task_dir = resolve_task_path(repo_root, recommended_task_path)
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

    dependency_section = "\n".join(find_section_lines(lines, "依赖关系"))
    dependency_ok = has_meaningful_text(dependency_section)
    checks += 1
    passed += print_result(
        dependency_ok,
        "依赖关系章节已填写",
        "依赖关系章节为空或仍是占位内容",
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

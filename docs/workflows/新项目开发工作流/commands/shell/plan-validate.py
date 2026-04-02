#!/usr/bin/env python3
"""任务拆解结构验证。

用法: python3 plan-validate.py [task_dir]

本脚本校验 `task_plan.md` 的结构完整性与关键字段一致性，不负责判断
依赖设计是否最优、冲突分析是否正确、或 Token 预算是否真实可行。
这些仍需人工复核。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ALLOWED_STATUSES = {"可开始", "等待中", "进行中", "已完成"}
ALLOWED_PARALLEL_ATTRIBUTES = {"候选可并行", "依赖不可并行"}
REQUIRED_SECTIONS = [
    "概述",
    "任务拆解 Checklist",
    "文件修改清单",
    "验收标准",
    "依赖关系",
    "执行安排",
    "任务执行矩阵",
]
REQUIRED_MATRIX_COLUMNS = [
    "任务ID",
    "前置任务",
    "当前状态",
    "开始条件",
    "等待原因",
    "并行属性",
    "冲突说明",
]
PLACEHOLDER_MARKERS = ("待补充", "TBD")


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
        stripped = lines[index].strip()
        if stripped.startswith("## "):
            end = index
            break
    return lines[start:end]


def has_meaningful_text(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    return not any(marker in stripped for marker in PLACEHOLDER_MARKERS)


def parse_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def extract_matrix(section_lines: list[str]) -> tuple[list[str], list[list[str]]]:
    table_lines = [line for line in section_lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return [], []

    header = parse_markdown_row(table_lines[0])
    rows = [parse_markdown_row(line) for line in table_lines[2:]]
    return header, rows


def print_result(ok: bool, success: str, failure: str) -> int:
    if ok:
        print(f"✅ {success}")
        return 1
    print(f"❌ {failure}")
    return 0


def main() -> int:
    task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    plan_file = task_dir / "task_plan.md"

    print("=== 任务拆解结构验证 ===")

    if not plan_file.exists():
        print("❌ task_plan.md 不存在")
        return 1
    print("✅ task_plan.md 存在")

    content = plan_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    checks = 0
    passed = 0

    checklist_items = len(re.findall(r"^-\s*\[[ x]\]", content, re.MULTILINE))
    has_phases = bool(re.search(r"^#{1,3}\s*Phase", content, re.MULTILINE))
    has_task_breakdown = has_phases or checklist_items > 0
    checks += 1
    passed += print_result(
        has_task_breakdown,
        "包含任务拆解",
        "缺少任务拆解 (Phase 或 Checklist)",
    )

    missing_sections = [title for title in REQUIRED_SECTIONS if not find_section_lines(lines, title)]
    checks += 1
    passed += print_result(
        not missing_sections,
        "包含完整章节结构",
        f"缺少章节: {', '.join(missing_sections)}",
    )

    acceptance_section = find_section_lines(lines, "验收标准")
    has_acceptance = bool(acceptance_section) and ("验收" in "\n".join(acceptance_section) or "- [ ]" in "\n".join(acceptance_section))
    checks += 1
    passed += print_result(
        has_acceptance,
        "包含验收标准",
        "缺少验收标准",
    )

    dependency_section = find_section_lines(lines, "依赖关系")
    dependency_text = "\n".join(dependency_section)
    has_dependency_fields = all(label in dependency_text for label in ["前置任务", "阻塞任务", "并行任务"])
    checks += 1
    passed += print_result(
        has_dependency_fields,
        "依赖关系字段完整",
        "依赖关系章节缺少前置任务/阻塞任务/并行任务字段",
    )

    execution_section = find_section_lines(lines, "执行安排")
    execution_text = "\n".join(execution_section)
    has_execution_fields = all(
        label in execution_text for label in ["当前可开始任务", "等待中任务", "推荐并行组", "串行主链"]
    )
    checks += 1
    passed += print_result(
        has_execution_fields,
        "执行安排字段完整",
        "执行安排章节缺少当前可开始任务/等待中任务/推荐并行组/串行主链字段",
    )

    matrix_section = find_section_lines(lines, "任务执行矩阵")
    header, rows = extract_matrix(matrix_section)
    has_matrix = bool(header) and bool(rows)
    checks += 1
    passed += print_result(
        has_matrix,
        "任务执行矩阵存在",
        "任务执行矩阵缺少表头或数据行",
    )

    matrix_columns_ok = header == REQUIRED_MATRIX_COLUMNS
    checks += 1
    passed += print_result(
        matrix_columns_ok,
        "任务执行矩阵列名正确",
        f"任务执行矩阵列名应为: {' | '.join(REQUIRED_MATRIX_COLUMNS)}",
    )

    status_ok = True
    parallel_ok = True
    start_wait_ok = True
    conflict_ok = True
    actionable_ok = False
    all_completed = True

    if has_matrix and matrix_columns_ok:
        for row in rows:
            if len(row) != len(header):
                status_ok = parallel_ok = start_wait_ok = conflict_ok = False
                all_completed = False
                continue

            data = dict(zip(header, row))
            status = data["当前状态"]
            parallel = data["并行属性"]
            start_condition = data["开始条件"]
            wait_reason = data["等待原因"]
            conflict_reason = data["冲突说明"]

            if status not in ALLOWED_STATUSES:
                status_ok = False
                all_completed = False
            if parallel not in ALLOWED_PARALLEL_ATTRIBUTES:
                parallel_ok = False
            if not has_meaningful_text(start_condition):
                start_wait_ok = False
            if status == "等待中" and (not has_meaningful_text(wait_reason) or wait_reason == "无"):
                start_wait_ok = False
            if not has_meaningful_text(conflict_reason):
                conflict_ok = False
            if status == "可开始":
                actionable_ok = True
            if status != "已完成":
                all_completed = False

    actionable_or_complete_ok = actionable_ok or all_completed

    checks += 1
    passed += print_result(
        status_ok,
        "当前状态只使用约定枚举",
        f"当前状态只能使用: {', '.join(sorted(ALLOWED_STATUSES))}",
    )

    checks += 1
    passed += print_result(
        parallel_ok,
        "并行属性只使用约定枚举",
        f"并行属性只能使用: {', '.join(sorted(ALLOWED_PARALLEL_ATTRIBUTES))}",
    )

    checks += 1
    passed += print_result(
        start_wait_ok,
        "开始条件与等待原因填写完整",
        "开始条件缺失，或等待中任务未写明有效等待原因",
    )

    checks += 1
    passed += print_result(
        conflict_ok,
        "并行属性与冲突说明填写完整",
        "冲突说明缺失，或仍使用占位内容",
    )

    checks += 1
    passed += print_result(
        actionable_or_complete_ok,
        "任务执行矩阵可支持当前执行判断",
        "任务执行矩阵中既未找到任何“可开始”任务，也不是“全部已完成”状态",
    )

    print(f"📊 待执行任务数: {checklist_items}")
    print()
    print(f"验证结果: {passed}/{checks} 通过")
    print("说明: 本脚本校验结构完整性；依赖是否合理、冲突是否准确仍需人工复核。")

    if passed != checks:
        print("❌ task_plan.md 结构验证未通过，请补充后重试")
        return 1

    print("✅ task_plan.md 结构验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

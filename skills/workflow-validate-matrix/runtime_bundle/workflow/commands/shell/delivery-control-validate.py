#!/usr/bin/env python3
"""双轨交付控制验证脚本。

验证外部项目在各阶段的双轨交付控制字段完整性和一致性。

用法:
  python3 delivery-control-validate.py --phase feasibility --task-dir <path>   # 验证 assessment.md
  python3 delivery-control-validate.py --phase plan --task-dir <path>         # 验证 task_plan.md
  python3 delivery-control-validate.py --phase delivery --task-dir <path>     # 验证 delivery/
  python3 delivery-control-validate.py --all --task-dir <path>              # 验证所有阶段
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from workflow_common import (
    MIN_KICKOFF_PAYMENT_RATIO,
    extract_backticked_field,
    extract_trellis_task_rows,
    find_assessment_in_lineage,
    resolve_task_table_path,
    task_note_matches_label,
)


VALID_ENGAGEMENT_TYPES = {"external_outsourcing", "non_outsourcing"}
VALID_EXTERNAL_TRACKS = {"hosted_deployment", "trial_authorization"}
VALID_BOOLEAN_VALUES = {"yes", "no"}


def _missing_sections(content: str, sections: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for section in sections:
        if not re.search(rf"^\s*##+\s*{re.escape(section)}\s*$", content, re.MULTILINE):
            missing.append(section)
    return missing


def print_result(ok: bool, success: str, failure: str) -> int:
    """打印验证结果，返回 1 表示通过，0 表示失败"""
    if ok:
        print(f"✅ {success}")
        return 1
    print(f"❌ {failure}")
    return 0


def load_delivery_control_track(assessment_file: Path) -> str | None:
    if not assessment_file.exists():
        return None
    content = assessment_file.read_text(encoding="utf-8")
    return extract_backticked_field(content, "delivery_control_track")


def _task_rows_by_note(content: str, task_name: str, task_dir: Path) -> list[Path]:
    matched: list[Path] = []
    for row in extract_trellis_task_rows(content):
        note = row.get("说明", "")
        if not task_note_matches_label(note, task_name):
            continue
        task_path = row.get("任务路径", "")
        if not task_path:
            continue
        matched.append(resolve_task_table_path(task_dir, task_path))
    return matched


def validate_assessment(assessment_file: Path) -> tuple[int, int, bool]:
    """
    验证 assessment.md 中的双轨字段。
    
    返回: (通过检查数, 总检查数, 是否为试运行授权轨道)
    """
    print("\n=== 验证 assessment.md (Feasibility 阶段) ===")
    
    if not assessment_file.exists():
        print(f"❌ {assessment_file} 不存在")
        return 0, 1, False
    
    content = assessment_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0
    is_trial = False
    
    # 1. 检查项目类别
    engagement_type = extract_backticked_field(content, "project_engagement_type")
    checks += 1
    if engagement_type is None:
        passed += print_result(False, "", "缺少 `project_engagement_type` 字段")
        return passed, checks, False
    if engagement_type not in VALID_ENGAGEMENT_TYPES:
        passed += print_result(False, "", f"`project_engagement_type` 值无效: {engagement_type}")
        return passed, checks, False
    passed += print_result(True, f"`project_engagement_type`: {engagement_type}", "")

    if engagement_type != "external_outsourcing":
        print("ℹ️  项目类别判定为非外包项目；跳过外包项目交付控制校验")
        return passed, checks, False

    print("检测到外包项目，验证开工款与交付控制字段...")

    # 2. 检查 kickoff_payment_ratio
    ratio_value = extract_backticked_field(content, "kickoff_payment_ratio")
    checks += 1
    if ratio_value:
        percentages = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", ratio_value)]
        if percentages and min(percentages) >= MIN_KICKOFF_PAYMENT_RATIO:
            passed += print_result(True, f"`kickoff_payment_ratio`: {ratio_value}", "")
        elif percentages:
            passed += print_result(
                False,
                "",
                f"`kickoff_payment_ratio` 至少应为 {int(MIN_KICKOFF_PAYMENT_RATIO)}%",
            )
        else:
            passed += print_result(False, "", "`kickoff_payment_ratio` 未写明有效百分比")
    else:
        passed += print_result(False, "", "缺少 `kickoff_payment_ratio` 字段")

    # 3. 检查 kickoff_payment_received
    kickoff_received = extract_backticked_field(content, "kickoff_payment_received")
    checks += 1
    if kickoff_received:
        if kickoff_received in VALID_BOOLEAN_VALUES:
            passed += print_result(True, f"`kickoff_payment_received`: {kickoff_received}", "")
        else:
            passed += print_result(False, "", "`kickoff_payment_received` 只能填写 `yes` / `no`")
    else:
        passed += print_result(False, "", "缺少 `kickoff_payment_received` 字段")

    # 4. 检查 delivery_control_track
    track_value = extract_backticked_field(content, "delivery_control_track")
    checks += 1
    if track_value:
        if track_value in VALID_EXTERNAL_TRACKS:
            passed += print_result(True, f"`delivery_control_track`: {track_value}", "")
            is_trial = (track_value == "trial_authorization")
        else:
            passed += print_result(False, "", f"`delivery_control_track` 值无效: {track_value}")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_track` 字段")

    # 5. 检查 delivery_control_handover_trigger
    trigger_value = extract_backticked_field(content, "delivery_control_handover_trigger")
    checks += 1
    if trigger_value:
        if trigger_value not in ["...", "例如"]:
            passed += print_result(True, f"`delivery_control_handover_trigger`: {trigger_value}", "")
        else:
            passed += print_result(False, "", "`delivery_control_handover_trigger` 未填写具体值")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_handover_trigger` 字段")

    # 6. 检查 delivery_control_retained_scope
    scope_value = extract_backticked_field(content, "delivery_control_retained_scope")
    checks += 1
    if scope_value:
        if scope_value != "...":
            passed += print_result(True, f"`delivery_control_retained_scope`: {scope_value}", "")
        else:
            passed += print_result(False, "", "`delivery_control_retained_scope` 未填写（若无保留范围，应写 `none`）")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_retained_scope` 字段")

    checks += 1
    milestone_schedule = extract_backticked_field(content, "milestone_payment_schedule")
    if milestone_schedule and milestone_schedule not in {"...", "例如"}:
        passed += print_result(True, f"`milestone_payment_schedule`: {milestone_schedule}", "")
    else:
        passed += print_result(False, "", "缺少 `milestone_payment_schedule` 字段")

    checks += 1
    remedy_path = extract_backticked_field(content, "non_payment_remedy_path")
    if remedy_path and remedy_path not in {"...", "例如"}:
        passed += print_result(True, f"`non_payment_remedy_path`: {remedy_path}", "")
    else:
        passed += print_result(False, "", "缺少 `non_payment_remedy_path` 字段")

    checks += 1
    dispute_path = extract_backticked_field(content, "dispute_escalation_path")
    if dispute_path and dispute_path not in {"...", "例如"}:
        passed += print_result(True, f"`dispute_escalation_path`: {dispute_path}", "")
    else:
        passed += print_result(False, "", "缺少 `dispute_escalation_path` 字段")

    # 7. 如果是 trial_authorization，检查 trial_authorization_terms
    if is_trial:
        print("\n检测到试运行授权轨道，检查授权条款...")
        required_terms = [
            ("trial_authorization_terms.validity", "有效期"),
            ("trial_authorization_terms.clock_source_or_usage_basis", "计时来源/使用基准"),
            ("trial_authorization_terms.expiration_behavior", "到期行为"),
            ("trial_authorization_terms.renewal_policy", "续期策略"),
            ("trial_authorization_terms.permanent_authorization_trigger", "永久授权触发条件"),
        ]
        
        for term, desc in required_terms:
            checks += 1
            term_match = re.search(rf'`{re.escape(term)}`:\s*(.+?)(?:\n|$)', content)
            if term_match:
                term_value = term_match.group(1).strip()
                if term_value and term_value not in ["...", ".", ""]:
                    passed += print_result(True, f"`{term}` 已填写", "")
                else:
                    passed += print_result(False, "", f"`{term}` ({desc}) 未填写具体值")
            else:
                passed += print_result(False, "", f"缺少 `{term}` ({desc}) 字段")
    
    # 5. 检查是否允许进入 brainstorm
    checks += 1
    brainstorm_match = re.search(r'是否允许进入 brainstorm[：:]\s*(\S+)', content)
    if brainstorm_match:
        brainstorm_value = brainstorm_match.group(1)
        if brainstorm_value in ["是", "否"]:
            passed += print_result(True, f"`是否允许进入 brainstorm`: {brainstorm_value}", "")
        else:
            passed += print_result(False, "", f"`是否允许进入 brainstorm` 值异常: {brainstorm_value}")
    else:
        passed += print_result(False, "", "未明确标注 `是否允许进入 brainstorm`")
    
    print(f"\n评估阶段验证: {passed}/{checks} 通过")
    return passed, checks, is_trial


def validate_task_plan(plan_file: Path, is_trial: bool) -> tuple[int, int]:
    """
    验证 task_plan.md 中的交付控制任务拆分。
    
    返回: (通过检查数, 总检查数)
    """
    print("\n=== 验证 task_plan.md (Plan 阶段) ===")
    
    if not plan_file.exists():
        print(f"❌ {plan_file} 不存在")
        return 0, 1
    
    content = plan_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0
    
    # 1. 检查是否有交付控制相关章节
    checks += 1
    has_delivery_section = "外部项目交付控制" in content or "交付控制" in content
    if has_delivery_section:
        passed += print_result(True, "包含交付控制相关章节", "")
    else:
        passed += print_result(False, "", "缺少 `外部项目交付控制` 章节")
    
    # 2. 检查是否拆分了关键交付控制任务
    required_tasks = [("开工授权确认任务", True), ("源码移交任务", True), ("控制权移交任务", True)]
    if is_trial:
        required_tasks.extend(
            [
                ("试运行版交付任务", True),
                ("永久授权切换任务", True),
            ]
        )
    else:
        required_tasks.append(("托管部署任务", True))
    
    print("\n检查交付控制任务拆分...")
    for task_name, is_required in required_tasks:
        checks += 1
        if task_name in content:
            passed += print_result(True, f"已拆分 `{task_name}`", "")
        elif is_required:
            passed += print_result(False, "", f"未拆分 `{task_name}`")
        else:
            checks -= 1  # 非必须任务，不计入检查
    
    # 3. 检查关键交付控制任务是否已落成真实 Trellis task
    for task_name, is_required in required_tasks:
        if not is_required:
            continue
        checks += 1
        matched_paths = _task_rows_by_note(content, task_name, plan_file.parent)
        if not matched_paths:
            passed += print_result(False, "", f"`{task_name}` 只出现在摘要文本中，未落成真实 Trellis task")
            continue
        existing_paths = [path for path in matched_paths if path.is_dir()]
        if not existing_paths:
            passed += print_result(False, "", f"`{task_name}` 已写入 task 清单，但对应任务目录不存在")
            continue
        passed += print_result(True, f"`{task_name}` 已落成真实 Trellis task", "")
    
    # 4. 检查是否有明确的开工款触发条件依赖
    checks += 1
    kickoff_trigger_patterns = ["启动款", "首款", "kickoff_payment", "开工授权"]
    has_kickoff_trigger = any(p in content for p in kickoff_trigger_patterns)
    if has_kickoff_trigger:
        passed += print_result(True, "任务计划包含开工款触发条件依赖", "")
    else:
        passed += print_result(False, "", "任务计划未明确开工款触发条件（如首款到账）")

    # 5. 检查是否有明确的最终移交触发条件依赖
    checks += 1
    final_trigger_patterns = ["尾款", "final_payment", "handover_trigger"]
    has_final_trigger = any(p in content for p in final_trigger_patterns)
    if has_final_trigger:
        passed += print_result(True, "任务计划包含最终移交触发条件依赖", "")
    else:
        passed += print_result(False, "", "任务计划未明确最终移交触发条件（如尾款到账）")

    checks += 1
    if "milestone_payment_schedule" in content:
        passed += print_result(True, "任务计划包含里程碑付款安排", "")
    else:
        passed += print_result(False, "", "任务计划未明确 `milestone_payment_schedule`")

    checks += 1
    if "non_payment_remedy_path" in content:
        passed += print_result(True, "任务计划包含拒付救济路径", "")
    else:
        passed += print_result(False, "", "任务计划未明确 `non_payment_remedy_path`")

    checks += 1
    if "dispute_escalation_path" in content:
        passed += print_result(True, "任务计划包含争议升级路径", "")
    else:
        passed += print_result(False, "", "任务计划未明确 `dispute_escalation_path`")
    
    print(f"\n计划阶段验证: {passed}/{checks} 通过")
    return passed, checks


def validate_delivery(delivery_dir: Path, is_trial: bool) -> tuple[int, int]:
    """
    验证 delivery/ 目录中的交付文档。
    
    返回: (通过检查数, 总检查数)
    """
    print("\n=== 验证 delivery/ 目录 (Delivery 阶段) ===")
    
    if not delivery_dir.exists():
        print(f"❌ {delivery_dir} 目录不存在")
        return 0, 1
    
    checks = 0
    passed = 0
    
    # 1. 检查必需的交付文档
    required_files = [
        ("transfer-checklist.md", True),
        ("deliverables.md", True),
        ("acceptance.md", True),
    ]
    
    print("检查交付文档...")
    for filename, is_required in required_files:
        checks += 1
        filepath = delivery_dir / filename
        if filepath.exists():
            passed += print_result(True, f"存在 `{filename}`", "")
        elif is_required:
            passed += print_result(False, "", f"缺少 `{filename}`")
        else:
            checks -= 1
    
    # 2. 检查 transfer-checklist.md 内容
    checklist_file = delivery_dir / "transfer-checklist.md"
    if checklist_file.exists():
        print("\n检查移交清单内容...")
        content = checklist_file.read_text(encoding="utf-8")
        checks += 1
        missing_sections = _missing_sections(
            content,
            (
                "当前事件允许移交什么",
                "当前事件禁止标记为已移交什么",
                "触发条件 / 付款 / 权限 / 证明材料是否齐备",
            ),
        )
        if missing_sections:
            passed += print_result(
                False,
                "",
                "移交清单缺少必要章节: " + ", ".join(missing_sections),
            )
        else:
            passed += print_result(True, "移交清单章节契约完整", "")
        
        # 检查是否有交付事件类型标注
        checks += 1
        event_patterns = ["retained-control delivery", "final control transfer", "trial delivery"]
        has_event_type = any(p in content for p in event_patterns)
        if has_event_type:
            passed += print_result(True, "移交清单标注了交付事件类型", "")
        else:
            passed += print_result(False, "", "移交清单未明确交付事件类型")

        checks += 1
        if "milestone_payment_schedule" in content:
            passed += print_result(True, "移交清单包含里程碑付款核对项", "")
        else:
            passed += print_result(False, "", "移交清单缺少 `milestone_payment_schedule` 核对项")

        checks += 1
        if "non_payment_remedy_path" in content:
            passed += print_result(True, "移交清单包含拒付救济核对项", "")
        else:
            passed += print_result(False, "", "移交清单缺少 `non_payment_remedy_path` 核对项")

        checks += 1
        if "dispute_escalation_path" in content:
            passed += print_result(True, "移交清单包含争议升级核对项", "")
        else:
            passed += print_result(False, "", "移交清单缺少 `dispute_escalation_path` 核对项")
        
        # 如果是试运行授权，检查是否有到期行为验证
        if is_trial:
            checks += 1
            trial_patterns = ["到期", "expiration", "授权", "authorization"]
            has_trial_check = any(p in content for p in trial_patterns)
            if has_trial_check:
                passed += print_result(True, "移交清单包含试运行授权检查项", "")
            else:
                passed += print_result(False, "", "移交清单缺少试运行授权相关检查项")
    
    # 3. 检查 deliverables.md 是否有交付物清单
    deliverables_file = delivery_dir / "deliverables.md"
    if deliverables_file.exists():
        print("\n检查交付物清单...")
        content = deliverables_file.read_text(encoding="utf-8")
        
        checks += 1
        missing_sections = _missing_sections(
            content,
            ("Closeout Assets", "Verification Evidence", "Current Status", "Residual Risks"),
        )
        if missing_sections:
            passed += print_result(False, "", "交付物清单缺少必要章节: " + ", ".join(missing_sections))
        else:
            passed += print_result(True, "交付物清单已定义", "")

    acceptance_file = delivery_dir / "acceptance.md"
    if acceptance_file.exists():
        print("\n检查验收文档...")
        content = acceptance_file.read_text(encoding="utf-8")
        checks += 1
        missing_sections = _missing_sections(
            content,
            ("Acceptance Criteria Status", "Blocking Findings", "Acceptance Gate", "当前交付状态"),
        )
        if missing_sections:
            passed += print_result(False, "", "验收文档缺少必要章节: " + ", ".join(missing_sections))
        else:
            passed += print_result(True, "验收文档契约完整", "")
    
    print(f"\n交付阶段验证: {passed}/{checks} 通过")
    return passed, checks


def load_engagement_type(assessment_file: Path) -> str | None:
    if not assessment_file.exists():
        return None
    content = assessment_file.read_text(encoding="utf-8")
    return extract_backticked_field(content, "project_engagement_type")


def validate_all_phases(task_dir: Path) -> int:
    """验证所有阶段的双轨交付控制完整性"""
    print("=" * 50)
    print("双轨交付控制完整验证")
    print("=" * 50)
    
    total_passed = 0
    total_checks = 0
    
    # Feasibility 阶段
    assessment_file = find_assessment_in_lineage(task_dir)
    passed, checks, is_trial = validate_assessment(assessment_file)
    total_passed += passed
    total_checks += checks
    
    if load_engagement_type(assessment_file) != "external_outsourcing":
        print("\n⚠️  未检测到外部项目特征，跳过后续验证")
        return 0 if total_passed == total_checks else 1
    
    # Plan 阶段
    plan_file = task_dir / "task_plan.md"
    passed, checks = validate_task_plan(plan_file, is_trial)
    total_passed += passed
    total_checks += checks
    
    # Delivery 阶段
    delivery_dir = task_dir / "delivery"
    passed, checks = validate_delivery(delivery_dir, is_trial)
    total_passed += passed
    total_checks += checks
    
    # 汇总
    print("\n" + "=" * 50)
    print(f"总计: {total_passed}/{total_checks} 通过")
    
    if total_passed == total_checks:
        print("✅ 双轨交付控制验证全部通过")
        return 0
    else:
        print("❌ 双轨交付控制验证未通过，请补充缺失内容")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="双轨交付控制验证脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 验证 feasibility 阶段
  python3 delivery-control-validate.py --phase feasibility --task-dir ./.trellis/tasks/my-task
  
  # 验证 plan 阶段
  python3 delivery-control-validate.py --phase plan --task-dir ./.trellis/tasks/my-task
  
  # 验证 delivery 阶段
  python3 delivery-control-validate.py --phase delivery --task-dir ./.trellis/tasks/my-task
  
  # 验证所有阶段
  python3 delivery-control-validate.py --all --task-dir ./.trellis/tasks/my-task
        """
    )
    parser.add_argument(
        "--phase",
        choices=["feasibility", "plan", "delivery"],
        help="验证特定阶段"
    )
    parser.add_argument(
        "--task-dir",
        type=Path,
        default=Path("."),
        help="任务目录路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="验证所有阶段"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    
    if args.all:
        return validate_all_phases(args.task_dir)
    
    if args.phase == "feasibility":
        passed, checks, _ = validate_assessment(find_assessment_in_lineage(args.task_dir))
        return 0 if passed == checks else 1

    if args.phase == "plan":
        assessment_file = find_assessment_in_lineage(args.task_dir)
        engagement_type = load_engagement_type(assessment_file)
        if engagement_type == "non_outsourcing":
            print("ℹ️  非外包项目无需执行外包项目交付控制 plan 校验")
            return 0
        is_trial = load_delivery_control_track(assessment_file) == "trial_authorization"
        
        passed, checks = validate_task_plan(args.task_dir / "task_plan.md", is_trial)
        return 0 if passed == checks else 1
    
    if args.phase == "delivery":
        assessment_file = find_assessment_in_lineage(args.task_dir)
        engagement_type = load_engagement_type(assessment_file)
        if engagement_type == "non_outsourcing":
            print("ℹ️  非外包项目无需执行外包项目交付控制 delivery 校验")
            return 0
        is_trial = load_delivery_control_track(assessment_file) == "trial_authorization"
        
        passed, checks = validate_delivery(args.task_dir / "delivery", is_trial)
        return 0 if passed == checks else 1
    
    # 默认行为：验证所有阶段
    return validate_all_phases(args.task_dir)


if __name__ == "__main__":
    raise SystemExit(main())

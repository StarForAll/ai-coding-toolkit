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
import re
import sys
from pathlib import Path
from typing import Optional


def print_result(ok: bool, success: str, failure: str) -> int:
    """打印验证结果，返回 1 表示通过，0 表示失败"""
    if ok:
        print(f"✅ {success}")
        return 1
    print(f"❌ {failure}")
    return 0


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
    
    # 检查是否为外部项目
    has_delivery_control = "delivery_control_track" in content
    if not has_delivery_control:
        print("ℹ️  未检测到双轨交付控制字段，假设为内部项目")
        return 0, 0, False
    
    print("检测到外部项目，验证双轨字段...")
    
    # 1. 检查 delivery_control_track
    track_match = re.search(r'`delivery_control_track`:\s*`([^`]+)`', content)
    checks += 1
    if track_match:
        track_value = track_match.group(1)
        valid_tracks = ["hosted_deployment", "trial_authorization", "undecided"]
        if track_value in valid_tracks:
            passed += print_result(True, f"`delivery_control_track`: {track_value}", "")
            is_trial = (track_value == "trial_authorization")
        else:
            passed += print_result(False, "", f"`delivery_control_track` 值无效: {track_value}")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_track` 字段")
    
    # 2. 检查 delivery_control_handover_trigger
    trigger_match = re.search(r'`delivery_control_handover_trigger`:\s*(.+?)(?:\n|$)', content)
    checks += 1
    if trigger_match:
        trigger_value = trigger_match.group(1).strip()
        if trigger_value and trigger_value not in ["...", "例如"]:
            passed += print_result(True, f"`delivery_control_handover_trigger`: {trigger_value}", "")
        else:
            passed += print_result(False, "", "`delivery_control_handover_trigger` 未填写具体值")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_handover_trigger` 字段")
    
    # 3. 检查 delivery_control_retained_scope
    scope_match = re.search(r'`delivery_control_retained_scope`:\s*(.+?)(?:\n|$)', content)
    checks += 1
    if scope_match:
        scope_value = scope_match.group(1).strip()
        if scope_value and scope_value != "...":
            passed += print_result(True, f"`delivery_control_retained_scope`: {scope_value}", "")
        else:
            passed += print_result(False, "", "`delivery_control_retained_scope` 未填写（若无保留范围，应写 `none`）")
    else:
        passed += print_result(False, "", "缺少 `delivery_control_retained_scope` 字段")
    
    # 4. 如果是 trial_authorization，检查 trial_authorization_terms
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
    required_tasks = [
        ("托管部署任务", True),  # (任务名, 是否必须)
        ("源码移交任务", True),
        ("控制权移交任务", True),
    ]
    
    if is_trial:
        required_tasks.extend([
            ("试运行版交付任务", True),
            ("永久授权切换任务", True),
        ])
    
    print("\n检查交付控制任务拆分...")
    for task_name, is_required in required_tasks:
        checks += 1
        if task_name in content:
            passed += print_result(True, f"已拆分 `{task_name}`", "")
        elif is_required:
            passed += print_result(False, "", f"未拆分 `{task_name}`")
        else:
            checks -= 1  # 非必须任务，不计入检查
    
    # 3. 检查任务执行矩阵中是否有交付控制任务
    checks += 1
    matrix_section = re.search(r'## 任务执行矩阵.*?(?=## |\Z)', content, re.DOTALL)
    if matrix_section:
        matrix_content = matrix_section.group(0)
        # 检查是否有交付控制相关任务ID
        delivery_tasks = ["交付", "移交", "授权", "部署"]
        has_delivery_task = any(task in matrix_content for task in delivery_tasks)
        if has_delivery_task:
            passed += print_result(True, "任务执行矩阵包含交付控制任务", "")
        else:
            passed += print_result(False, "", "任务执行矩阵缺少交付控制相关任务")
    else:
        passed += print_result(False, "", "未找到 `任务执行矩阵` 章节")
    
    # 4. 检查是否有明确的触发条件依赖
    checks += 1
    trigger_patterns = ["尾款", "final_payment", "handover_trigger"]
    has_trigger = any(p in content for p in trigger_patterns)
    if has_trigger:
        passed += print_result(True, "任务计划包含触发条件依赖", "")
    else:
        passed += print_result(False, "", "任务计划未明确触发条件（如尾款到账）")
    
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
        
        # 检查是否有交付事件类型标注
        checks += 1
        event_patterns = ["retained-control delivery", "final control transfer", "trial delivery"]
        has_event_type = any(p in content for p in event_patterns)
        if has_event_type:
            passed += print_result(True, "移交清单标注了交付事件类型", "")
        else:
            passed += print_result(False, "", "移交清单未明确交付事件类型")
        
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
        # 检查是否有明确的交付物分类
        if "交付物" in content or "交付清单" in content:
            passed += print_result(True, "交付物清单已定义", "")
        else:
            passed += print_result(False, "", "交付物清单未明确")
    
    print(f"\n交付阶段验证: {passed}/{checks} 通过")
    return passed, checks


def validate_all_phases(task_dir: Path) -> int:
    """验证所有阶段的双轨交付控制完整性"""
    print("=" * 50)
    print("双轨交付控制完整验证")
    print("=" * 50)
    
    total_passed = 0
    total_checks = 0
    
    # Feasibility 阶段
    assessment_file = task_dir / "assessment.md"
    passed, checks, is_trial = validate_assessment(assessment_file)
    total_passed += passed
    total_checks += checks
    
    if checks == 0:
        print("\n⚠️  未检测到外部项目特征，跳过后续验证")
        return 0
    
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
        passed, checks, _ = validate_assessment(args.task_dir / "assessment.md")
        return 0 if passed == checks else 1
    
    if args.phase == "plan":
        # 先检查是否为试运行授权
        assessment_file = args.task_dir / "assessment.md"
        is_trial = False
        if assessment_file.exists():
            content = assessment_file.read_text(encoding="utf-8")
            is_trial = '`delivery_control_track`: `trial_authorization`' in content
        
        passed, checks = validate_task_plan(args.task_dir / "task_plan.md", is_trial)
        return 0 if passed == checks else 1
    
    if args.phase == "delivery":
        # 先检查是否为试运行授权
        assessment_file = args.task_dir / "assessment.md"
        is_trial = False
        if assessment_file.exists():
            content = assessment_file.read_text(encoding="utf-8")
            is_trial = '`delivery_control_track`: `trial_authorization`' in content
        
        passed, checks = validate_delivery(args.task_dir / "delivery", is_trial)
        return 0 if passed == checks else 1
    
    # 默认行为：验证所有阶段
    return validate_all_phases(args.task_dir)


if __name__ == "__main__":
    raise SystemExit(main())

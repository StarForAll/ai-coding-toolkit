#!/usr/bin/env python3
"""任务拆解验证。

用法: python3 plan-validate.py [task_dir]
"""
import re
import sys
from pathlib import Path


def main():
    task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    plan_file = task_dir / "task_plan.md"

    print("=== 任务拆解验证 ===")

    if not plan_file.exists():
        print("❌ task_plan.md 不存在")
        sys.exit(1)
    print("✅ task_plan.md 存在")

    content = plan_file.read_text(encoding="utf-8")
    checks = 0
    passed = 0

    # 检查是否有任务拆解
    has_phases = bool(re.search(r"^#{1,3}\s*Phase", content, re.MULTILINE))
    has_checklist = bool(re.search(r"^-\s*\[[ x]\]", content, re.MULTILINE))
    if has_phases or has_checklist:
        print("✅ 包含任务拆解")
        passed += 1
    else:
        print("❌ 缺少任务拆解 (Phase 或 Checklist)")
    checks += 1

    # 检查验收标准
    if "验收" in content or "Acceptance" in content:
        print("✅ 包含验收标准")
        passed += 1
    else:
        print("❌ 缺少验收标准")
    checks += 1

    # 检查依赖关系
    has_deps = any(kw in content for kw in ["依赖", "前置", "并行"])
    if has_deps:
        print("✅ 包含依赖关系")
        passed += 1
    else:
        print("⚠️  未发现依赖关系描述")
    checks += 1

    # 统计任务数量
    task_count = len(re.findall(r"^-\s*\[[ x]\]", content, re.MULTILINE))
    print(f"📊 待执行任务数: {task_count}")

    print()
    print(f"验证结果: {passed}/{checks} 通过")

    if passed < 2:
        print("❌ 任务拆解不完整，请补充")
        sys.exit(1)
    else:
        print("✅ 任务拆解基本完整")


if __name__ == "__main__":
    main()

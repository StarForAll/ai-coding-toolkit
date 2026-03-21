#!/usr/bin/env python3
"""自审辅助检查。

用法: python3 self-review-check.py [task_dir]
"""
import subprocess
import sys
from pathlib import Path


def run_check(cmd, label):
    """运行检查命令并报告结果。"""
    print(f"\n--- {label} ---")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {label} 通过")
        else:
            print(f"❌ {label} 未通过")
            if result.stdout.strip():
                print(result.stdout.strip()[:500])
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⚠️  {label} 超时")
        return False
    except FileNotFoundError:
        print(f"⚠️  命令不存在，跳过")
        return None


def main():
    task_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    print("=== 自审检查 ===")

    # 1. 测试
    has_package_json = Path("package.json").exists()
    if has_package_json:
        run_check("pnpm test --reporter=dot 2>/dev/null", "测试状态")
    else:
        print("\n--- 测试状态 ---")
        print("⚠️  未检测到 package.json，跳过测试检查")

    # 2. Lint
    if has_package_json:
        run_check("pnpm lint 2>/dev/null", "Lint 状态")

    # 3. Type check
    if has_package_json:
        run_check("pnpm type-check 2>/dev/null", "Type Check 状态")

    # 4. Git 状态
    print("\n--- Git 状态 ---")
    try:
        changed = subprocess.run("git diff --name-only", shell=True, capture_output=True, text=True)
        untracked = subprocess.run("git ls-files --others --exclude-standard", shell=True, capture_output=True, text=True)
        changed_count = len(changed.stdout.strip().splitlines()) if changed.stdout.strip() else 0
        untracked_count = len(untracked.stdout.strip().splitlines()) if untracked.stdout.strip() else 0
        print(f"已修改文件: {changed_count}")
        print(f"未跟踪文件: {untracked_count}")
    except Exception:
        print("⚠️  git 不可用")

    # 5. 历史自审
    print("\n--- 历史自审 ---")
    review_file = task_dir / "self-review.md"
    if review_file.exists():
        print("⚠️  已有 self-review.md，建议对比差异")
    else:
        print("ℹ️  首次自审")

    print()
    print("=== 自审检查完成 ===")
    print("下一步：根据以上结果生成 self-review.md 偏差清单")


if __name__ == "__main__":
    main()

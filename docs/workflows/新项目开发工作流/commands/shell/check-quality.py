#!/usr/bin/env python3
"""质量检查辅助脚本。

用法: python3 check-quality.py [task_dir] [--test-cmd CMD] [--lint-cmd CMD] [--typecheck-cmd CMD]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run workflow quality checks with project-confirmed commands.")
    parser.add_argument("task_dir", nargs="?", default=".", help="Task directory used to inspect check.md")
    parser.add_argument("--test-cmd", dest="test_cmd", help="User-confirmed test command for the current project")
    parser.add_argument("--lint-cmd", dest="lint_cmd", help="User-confirmed lint command for the current project")
    parser.add_argument(
        "--typecheck-cmd",
        dest="typecheck_cmd",
        help="User-confirmed type-check command for the current project",
    )
    return parser.parse_args(argv)


def run_check(cmd: str, label: str) -> bool | None:
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


def run_optional_check(cmd: str | None, label: str) -> bool | None:
    if not cmd:
        print(f"\n--- {label} ---")
        print("⚠️  未提供已确认命令，跳过")
        return None
    return run_check(cmd, label)


def main() -> int:
    args = parse_args(sys.argv[1:])
    task_dir = Path(args.task_dir)

    print("=== 质量检查 ===")

    print("说明：测试 / lint / type-check 命令必须来自技术架构确认后由用户明确的项目化输入。")

    # 1. 测试
    run_optional_check(args.test_cmd, "测试状态")

    # 2. Lint
    run_optional_check(args.lint_cmd, "Lint 状态")

    # 3. Type check
    run_optional_check(args.typecheck_cmd, "Type Check 状态")

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

    # 5. 历史检查
    print("\n--- 历史检查 ---")
    review_file = task_dir / "check.md"
    if review_file.exists():
        print("⚠️  已有 check.md，建议对比差异")
    else:
        print("ℹ️  首次质量检查")

    print()
    print("=== 质量检查完成 ===")
    print("下一步：根据以上结果生成 check.md 检查结果")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""质量检查辅助脚本。

用法: python3 check-quality.py [task_dir] [--test-cmd CMD] [--lint-cmd CMD] [--typecheck-cmd CMD] [--extra-check LABEL=CMD]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    label: str
    command: str | None
    status: str
    detail: str | None = None


def _print_result(result: CheckResult) -> None:
    print(f"\n--- {result.label} ---")
    print(f"Result: {result.status}")
    if result.command:
        print(f"Command: {result.command}")
    if result.detail:
        print(result.detail)


def parse_extra_check(value: str) -> tuple[str, str]:
    label, sep, cmd = value.partition("=")
    label = label.strip()
    cmd = cmd.strip()
    if not sep or not label or not cmd:
        raise argparse.ArgumentTypeError("extra checks must use LABEL=COMMAND format")
    return label, cmd


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
    parser.add_argument(
        "--extra-check",
        dest="extra_checks",
        action="append",
        default=[],
        type=parse_extra_check,
        metavar="LABEL=COMMAND",
        help="Additional user-confirmed verification such as build/e2e/migration",
    )
    return parser.parse_args(argv)


def run_check(cmd: str, label: str) -> CheckResult:
    """运行检查命令并报告结果。"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return CheckResult(label=label, command=cmd, status="pass")

        details: list[str] = [f"Exit Code: {result.returncode}"]
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            details.append(f"stdout:\n{stdout[:800]}")
        if stderr:
            details.append(f"stderr:\n{stderr[:800]}")
        return CheckResult(label=label, command=cmd, status="fail", detail="\n".join(details))
    except subprocess.TimeoutExpired:
        return CheckResult(label=label, command=cmd, status="fail", detail="Reason: command timed out after 60s")


def run_optional_check(cmd: str | None, label: str) -> CheckResult:
    if not cmd:
        return CheckResult(label=label, command=None, status="not run", detail="Reason: 未提供已确认命令")
    return run_check(cmd, label)


def main() -> int:
    args = parse_args(sys.argv[1:])
    task_dir = Path(args.task_dir)

    print("=== 质量检查 ===")

    print("说明：测试 / lint / type-check / extra-check 命令必须来自技术架构确认后由用户明确的项目化输入。")

    results: list[CheckResult] = []

    # 1. 测试
    results.append(run_optional_check(args.test_cmd, "测试状态"))

    # 2. Lint
    results.append(run_optional_check(args.lint_cmd, "Lint 状态"))

    # 3. Type check
    results.append(run_optional_check(args.typecheck_cmd, "Type Check 状态"))

    for label, cmd in args.extra_checks:
        results.append(run_check(cmd, label))

    for result in results:
        _print_result(result)

    provided_commands = [
        cmd
        for cmd in (args.test_cmd, args.lint_cmd, args.typecheck_cmd, *(cmd for _, cmd in args.extra_checks))
        if cmd
    ]
    if not provided_commands:
        print()
        print("❌ 未提供任何已确认的验证命令；质量检查不能在无证据输入下视为通过")

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
    print("\n--- Summary ---")
    for result in results:
        print(f"- {result.label}: {result.status}")
    if not provided_commands:
        return 1
    if any(result.status == "fail" for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

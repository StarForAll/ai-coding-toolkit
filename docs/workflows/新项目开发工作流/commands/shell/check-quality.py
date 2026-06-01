#!/usr/bin/env python3
"""质量检查辅助脚本。

用法: python3 check-quality.py [task_dir] [--test-cmd CMD] [--lint-cmd CMD]
[--typecheck-cmd CMD] [--extra-check LABEL=CMD] [--scope frontend,backend,api]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from project_id_utils import find_repo_root, require_installed_project_id


SONAR_VERIFY_TIMEOUT_SECONDS = 300


class CheckResult(NamedTuple):
    label: str
    command: str | None
    status: str
    detail: str | None = None


def run_git_query(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


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
    parser.add_argument(
        "--scope",
        dest="scope",
        help="Manual cross-layer scope such as frontend,backend,api",
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


def run_sonar_verify(project_id: str) -> CheckResult:
    rendered_command = f"sonar verify -p {project_id}"
    command = ["sonar", "verify", "-p", project_id]
    timeout_raw = os.environ.get("WORKFLOW_SONAR_VERIFY_TIMEOUT_SECONDS", str(SONAR_VERIFY_TIMEOUT_SECONDS))
    timeout_note: str | None = None
    try:
        timeout_seconds = int(timeout_raw)
    except ValueError:
        timeout_seconds = SONAR_VERIFY_TIMEOUT_SECONDS
        timeout_note = (
            f"Reason: WORKFLOW_SONAR_VERIFY_TIMEOUT_SECONDS={timeout_raw!r} 无效，"
            f"已回退默认值 {SONAR_VERIFY_TIMEOUT_SECONDS}s"
        )
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    except FileNotFoundError:
        return CheckResult(
            label="Sonar Verify",
            command=rendered_command,
            status="fail",
            detail="\n".join(part for part in [timeout_note, "Reason: sonar command not found"] if part),
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            label="Sonar Verify",
            command=rendered_command,
            status="fail",
            detail="\n".join(
                part for part in [timeout_note, f"Reason: command timed out after {timeout_seconds}s"] if part
            ),
        )

    if result.returncode == 0:
        return CheckResult(label="Sonar Verify", command=rendered_command, status="pass")

    details: list[str] = [f"Exit Code: {result.returncode}"]
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        details.append(f"stdout:\n{stdout[:800]}")
    if stderr:
        details.append(f"stderr:\n{stderr[:800]}")
    if timeout_note:
        details.insert(0, timeout_note)
    return CheckResult(
        label="Sonar Verify",
        command=rendered_command,
        status="fail",
        detail="\n".join(details),
    )


def main() -> int:
    args = parse_args(sys.argv[1:])
    task_dir = Path(args.task_dir)
    repo_root = find_repo_root(task_dir.resolve())
    if repo_root is None:
        print("❌ 无法定位 repo root，不能读取 workflow-installed.json project_id")
        return 1
    try:
        project_id = require_installed_project_id(repo_root, "check-quality.py")
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    print("=== 质量检查 ===")

    print("说明：测试 / lint / type-check / extra-check 命令必须来自技术架构确认后由用户明确的项目化输入。")
    print("说明：本 workflow 强制先执行 `sonar verify -p <project-id>`；若失败，必须修复并排查同类问题后重新运行。")
    print(f"Project ID: {project_id}")
    if args.scope:
        print(f"手动指定跨层范围: {args.scope}")

    results: list[CheckResult] = []

    # 0. 强制质量平台门禁
    sonar_result = run_sonar_verify(project_id)
    results.append(sonar_result)
    if sonar_result.status == "fail":
        _print_result(sonar_result)
        print()
        print("❌ Sonar Verify 未通过；必须先修复当前问题。")
        print("❌ 还需要主动排查是否存在同类问题，并将同类问题一并修复。")
        print("❌ 完成修复后，重新执行 `sonar verify -p <project-id>`，通过后再重跑当前检查。")
        print("=== 质量检查完成 ===")
        print("下一步：修复 sonar 问题后重新执行 check-quality.py")
        print("\n--- Summary ---")
        if args.scope:
            print(f"- Cross-Layer Scope: {args.scope}")
        print(f"- {sonar_result.label}: {sonar_result.status}")
        return 1

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
        changed = run_git_query(["git", "diff", "--name-only"])
        untracked = run_git_query(["git", "ls-files", "--others", "--exclude-standard"])
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
    if args.scope:
        print(f"- Cross-Layer Scope: {args.scope}")
    for result in results:
        print(f"- {result.label}: {result.status}")
    if not provided_commands:
        return 1
    if any(result.status == "fail" for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

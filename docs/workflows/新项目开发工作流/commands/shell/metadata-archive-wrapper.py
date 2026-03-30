#!/usr/bin/env python3
"""元数据归档一键执行脚本。

在项目脚本不可修改的前提下，确保 guard 检查被执行。

用法:
    python3 metadata-archive-wrapper.py <task-name>
    python3 metadata-archive-wrapper.py <task-name> --no-commit

本脚本自动执行:
    1. Guard pre-check (当前任务边界 + staged 污染)
    2. task.py archive (实际归档)
    3. Guard post-check (验证 git 已清空)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path:
    """Find project root by looking for .trellis or .git directory."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".trellis").exists() or (candidate / ".git").exists():
            return candidate
    raise SystemExit("未找到项目根目录")


def run_guard_check(mode: str, task_dir: Path | None = None, project_root: Path | None = None) -> int:
    """Run metadata auto-commit guard check."""
    script_dir = Path(__file__).parent
    guard_script = script_dir / "metadata-autocommit-guard.py"

    if not guard_script.is_file():
        print(f"Error: guard script not found: {guard_script}", file=sys.stderr)
        return 1

    args = ["python3", str(guard_script), "--mode", mode, "--check", "pre"]
    if task_dir:
        args.extend(["--task-dir", str(task_dir)])
    if project_root:
        args.extend(["--project-root", str(project_root)])

    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="元数据归档一键执行脚本")
    parser.add_argument("task_name", help="要归档的任务名称")
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="跳过自动 git commit",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = find_project_root(script_dir)
    task_script = project_root / ".trellis" / "scripts" / "task.py"
    guard_script = script_dir / "metadata-autocommit-guard.py"

    print("========================================")
    print("元数据归档流程")
    print("========================================")
    print(f"任务: {args.task_name}")
    print()

    # Step 1: Guard pre-check
    print("[1/3] 执行 Guard pre-check...")
    task_dir = project_root / ".trellis" / "tasks" / args.task_name

    result = subprocess.run(
        [
            "python3",
            str(guard_script),
            "--mode",
            "archive",
            "--check",
            "pre",
            "--task-dir",
            str(task_dir),
            "--project-root",
            str(project_root),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ Guard pre-check 失败", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    print(result.stdout.strip())
    print()

    # Step 2: Execute archive
    print("[2/3] 执行归档...")
    archive_cmd = [sys.executable, str(task_script), "archive", args.task_name]
    if args.no_commit:
        archive_cmd.append("--no-commit")

    result = subprocess.run(archive_cmd, cwd=project_root, capture_output=True, text=True)
    print(result.stdout, file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ 归档失败: {result.stderr}", file=sys.stderr)
        return 1

    print()

    # Step 3: Guard post-check
    print("[3/3] 执行 Guard post-check...")
    result = subprocess.run(
        [
            "python3",
            str(guard_script),
            "--mode",
            "archive",
            "--check",
            "post",
            "--project-root",
            str(project_root),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ Guard post-check 失败", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return 1

    print(result.stdout.strip())
    print()
    print("========================================")
    print("✅ 归档流程完成")
    print("========================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
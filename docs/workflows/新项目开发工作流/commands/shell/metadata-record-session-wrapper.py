#!/usr/bin/env python3
"""元数据会话记录一键执行脚本。

在项目脚本不可修改的前提下，确保 guard 检查被执行。

用法:
    python3 metadata-record-session-wrapper.py --title "Session Title" --commit "hash"
    python3 metadata-record-session-wrapper.py --title "Session Title" --commit "hash" --no-commit

本脚本自动执行:
    1. Guard pre-check (当前任务边界 + staged 污染)
    2. add_session.py (实际记录)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="元数据会话记录一键执行脚本")
    parser.add_argument("--title", required=True, help="会话标题")
    parser.add_argument("--commit", default="-", help="Git commit hash，可多个逗号分隔")
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="跳过自动 git commit",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = find_project_root(script_dir)
    record_script = project_root / ".trellis" / "scripts" / "add_session.py"
    guard_script = script_dir / "metadata-autocommit-guard.py"

    print("========================================")
    print("元数据会话记录流程")
    print("========================================")
    print(f"标题: {args.title}")
    print(f"提交: {args.commit}")
    print()

    # Step 1: Guard pre-check
    print("[1/3] 执行 Guard pre-check...")
    result = subprocess.run(
        [
            "python3",
            str(guard_script),
            "--mode",
            "record-session",
            "--check",
            "pre",
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

    # Step 2: Execute record-session
    print("[2/3] 执行会话记录...")
    record_cmd = [
        sys.executable,
        str(record_script),
        "--title",
        args.title,
        "--commit",
        args.commit,
    ]
    if args.no_commit:
        record_cmd.append("--no-commit")

    result = subprocess.run(record_cmd, cwd=project_root, capture_output=True, text=True)
    print(result.stdout, file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ 会话记录失败: {result.stderr}", file=sys.stderr)
        return 1

    print()

    # Step 3: Guard post-check
    print("[3/3] 执行 Guard post-check...")
    result = subprocess.run(
        [
            "python3",
            str(guard_script),
            "--mode",
            "record-session",
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
    print("✅ 会话记录流程完成")
    print("========================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
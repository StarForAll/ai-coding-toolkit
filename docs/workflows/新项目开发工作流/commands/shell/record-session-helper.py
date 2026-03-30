#!/usr/bin/env python3
"""Run record-session with metadata closure checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_project_root(start: Path) -> Path:
    """Find project root by walking upward until .trellis or .git exists."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".trellis").exists() or (candidate / ".git").exists():
            return candidate
    raise SystemExit("未找到项目根目录，请使用 --project-root 指定")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行 record-session 并校验元数据闭环")
    parser.add_argument("--title", required=True, help="会话标题")
    parser.add_argument("--commit", default="-", help="Git commit hash，可多个逗号分隔")
    parser.add_argument("--summary", default="(Add summary)", help="会话摘要")
    parser.add_argument("--content-file", help="包含详细内容的文件路径")
    parser.add_argument("--package", help="包名标签（若项目支持）")
    parser.add_argument("--branch", help="分支名（可选）")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取详细内容")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="项目根目录（默认自动检测）",
    )
    return parser


def run_step(
    cmd: list[str],
    *,
    cwd: Path,
    step_name: str,
    input_text: str | None = None,
) -> int:
    """Run one step and mirror stdout/stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"❌ {step_name} 失败", file=sys.stderr)
    return result.returncode


def build_add_session_cmd(args: argparse.Namespace, repo_root: Path) -> list[str]:
    """Build the add_session.py invocation."""
    add_session_script = repo_root / ".trellis" / "scripts" / "add_session.py"
    cmd = [
        sys.executable,
        str(add_session_script),
        "--title",
        args.title,
        "--commit",
        args.commit,
        "--summary",
        args.summary,
    ]
    if args.content_file:
        cmd.extend(["--content-file", args.content_file])
    if args.package:
        cmd.extend(["--package", args.package])
    if args.branch:
        cmd.extend(["--branch", args.branch])
    if args.stdin:
        cmd.append("--stdin")
    return cmd


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = (
        args.project_root.resolve()
        if args.project_root is not None
        else find_project_root(Path.cwd())
    )
    script_dir = Path(__file__).resolve().parent
    guard_script = script_dir / "metadata-autocommit-guard.py"
    input_text = sys.stdin.read() if args.stdin else None

    print("========================================")
    print("record-session metadata closure")
    print("========================================")

    pre_cmd = [
        sys.executable,
        str(guard_script),
        "--mode",
        "record-session",
        "--check",
        "pre",
        "--project-root",
        str(repo_root),
    ]
    if run_step(pre_cmd, cwd=repo_root, step_name="record-session pre-check") != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    add_session_cmd = build_add_session_cmd(args, repo_root)
    if run_step(
        add_session_cmd,
        cwd=repo_root,
        step_name="add_session.py",
        input_text=input_text,
    ) != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    post_cmd = [
        sys.executable,
        str(guard_script),
        "--mode",
        "record-session",
        "--check",
        "post",
        "--project-root",
        str(repo_root),
    ]
    if run_step(post_cmd, cwd=repo_root, step_name="record-session post-check") != 0:
        print("record-session incomplete", file=sys.stderr)
        return 1

    print("✅ record-session completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

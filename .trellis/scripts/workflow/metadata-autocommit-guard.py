#!/usr/bin/env python3
"""Metadata auto-commit checks and commit-only execution for record-session."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ALLOWED_PREFIXES = {
    "record-session": [".trellis/workspace", ".trellis/tasks"],
}
COMMIT_TARGETS = [".trellis/workspace", ".trellis/tasks"]


def run_git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".trellis").exists() or (candidate / ".git").exists():
            return candidate
    raise SystemExit("未找到项目根目录，请使用 --project-root 指定")


def is_allowed_path(path: str, allowed_prefixes: list[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    for prefix in allowed_prefixes:
        clean = prefix.replace("\\", "/").lstrip("./")
        if normalized == clean or normalized.startswith(f"{clean}/"):
            return True
    return False


def get_staged_paths(repo_root: Path) -> tuple[bool, list[str] | str]:
    rc, out, err = run_git(repo_root, "diff", "--cached", "--name-only")
    if rc != 0:
        return False, err.strip() or "git diff --cached --name-only failed"
    paths = [line.strip() for line in out.splitlines() if line.strip()]
    return True, paths


def get_dirty_lines(repo_root: Path, *paths: str) -> tuple[bool, list[str] | str]:
    rc, out, err = run_git(repo_root, "status", "--short", "--", *paths)
    if rc != 0:
        return False, err.strip() or "git status --short failed"
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return True, lines


def validate_pre_check(repo_root: Path, mode: str) -> int:
    ok, staged = get_staged_paths(repo_root)
    if not ok:
        print(f"❌ metadata auto-commit pre-check failed: {staged}", file=sys.stderr)
        return 1

    assert isinstance(staged, list)
    outside_scope = [
        path for path in staged if not is_allowed_path(path, ALLOWED_PREFIXES[mode])
    ]
    if outside_scope:
        print("❌ Auto-commit blocked: staged changes outside metadata scope", file=sys.stderr)
        for path in outside_scope:
            print(f"  - {path}", file=sys.stderr)
        return 1

    ok, dirty_lines = get_dirty_lines(repo_root, ".trellis/tasks")
    if not ok:
        print(f"❌ record-session blocked: {dirty_lines}", file=sys.stderr)
        return 1
    assert isinstance(dirty_lines, list)
    if dirty_lines:
        print(
            "❌ record-session blocked: .trellis/tasks must be clean before final close-out",
            file=sys.stderr,
        )
        for line in dirty_lines:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(f"✅ metadata auto-commit pre-check passed ({mode})")
    return 0


def validate_post_check(repo_root: Path, mode: str) -> int:
    rc, out, err = run_git(
        repo_root,
        "status",
        "--short",
        "--",
        *ALLOWED_PREFIXES[mode],
    )
    if rc != 0:
        print(
            f"❌ metadata auto-commit post-check failed: "
            f"{err.strip() or 'git status --short failed'}",
            file=sys.stderr,
        )
        return 1

    dirty_lines = [line for line in out.splitlines() if line.strip()]
    if dirty_lines:
        print("❌ metadata auto-commit post-check found dirty paths", file=sys.stderr)
        for line in dirty_lines:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(f"✅ metadata auto-commit post-check passed ({mode})")
    return 0


def commit_metadata(repo_root: Path, commit_message: str) -> int:
    add_result = subprocess.run(
        ["git", "add", "-A", *COMMIT_TARGETS],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if add_result.returncode != 0:
        print(
            f"❌ metadata git add failed (exit {add_result.returncode}): {add_result.stderr.strip()}",
            file=sys.stderr,
        )
        return add_result.returncode or 1

    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *COMMIT_TARGETS],
        cwd=repo_root,
        check=False,
    )
    if diff_result.returncode == 0:
        print("✅ metadata commit skipped: no staged .trellis changes")
        return 0

    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if commit_result.returncode != 0:
        print(
            f"❌ metadata git commit failed (exit {commit_result.returncode}): {commit_result.stderr.strip()}",
            file=sys.stderr,
        )
        return commit_result.returncode or 1

    print(f"✅ metadata auto-commit succeeded: {commit_message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="元数据自动提交门禁检查与提交执行")
    parser.add_argument("--mode", choices=["record-session"], required=True)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--check", choices=["pre", "post"])
    parser.add_argument("--commit-message", help="commit-only 模式下使用的 commit message")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = args.project_root.resolve() if args.project_root else find_project_root(Path.cwd())

    if args.check == "pre":
        return validate_pre_check(repo_root, args.mode)
    if args.check == "post":
        return validate_post_check(repo_root, args.mode)
    if args.commit_message:
        return commit_metadata(repo_root, args.commit_message)

    parser.error("必须提供 --check 或 --commit-message")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

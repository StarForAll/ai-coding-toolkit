#!/usr/bin/env python3
"""收尾型 record-session 的元数据闭环门禁检查。

用法:
  python3 metadata-autocommit-guard.py --mode archive --check pre --task-dir <path>
  python3 metadata-autocommit-guard.py --mode archive --check post
  python3 metadata-autocommit-guard.py --mode record-session --check pre
  python3 metadata-autocommit-guard.py --mode record-session --check post
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ALLOWED_PREFIXES = {
    "archive": [".trellis/tasks", ".trellis/.current-task"],
    "record-session": [".trellis/workspace", ".trellis/tasks"],
}


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


def get_current_task(repo_root: Path) -> str | None:
    current_file = repo_root / ".trellis" / ".current-task"
    if not current_file.is_file():
        return None
    try:
        content = current_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return content or None


def normalize_repo_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def is_allowed_path(path_str: str, allowed_prefixes: list[str]) -> bool:
    normalized = path_str.strip().replace("\\", "/")
    for prefix in allowed_prefixes:
        clean = prefix.rstrip("/")
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
    """Return git status --short lines for the given paths."""
    rc, out, err = run_git(repo_root, "status", "--short", "--", *paths)
    if rc != 0:
        return False, err.strip() or "git status --short failed"
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return True, lines


def validate_pre_check(repo_root: Path, mode: str, task_dir: Path | None) -> int:
    current_task = get_current_task(repo_root)

    if mode == "archive":
        if not current_task:
            print("❌ Auto-commit blocked: no current task", file=sys.stderr)
            return 1
        if task_dir is None:
            print("❌ Auto-commit blocked: archive pre-check requires --task-dir", file=sys.stderr)
            return 1
        target_task = normalize_repo_path(repo_root, task_dir)
        if target_task != current_task:
            print(
                f"❌ Auto-commit blocked: target is not current task "
                f"(target={target_task}, current={current_task})",
                file=sys.stderr,
            )
            return 1

    ok, staged = get_staged_paths(repo_root)
    if not ok:
        print(f"❌ Auto-commit blocked: {staged}", file=sys.stderr)
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

    if mode == "record-session":
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="元数据自动提交门禁检查")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["archive", "record-session"],
        help="收尾模式",
    )
    parser.add_argument(
        "--check",
        required=True,
        choices=["pre", "post"],
        help="检查阶段",
    )
    parser.add_argument(
        "--task-dir",
        type=Path,
        help="归档目标任务目录（archive pre-check 必需）",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="项目根目录（默认自动检测）",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = (
        args.project_root.resolve()
        if args.project_root is not None
        else find_project_root(Path.cwd())
    )

    task_dir = None
    if args.task_dir is not None:
        task_dir = args.task_dir if args.task_dir.is_absolute() else repo_root / args.task_dir

    if args.check == "pre":
        return validate_pre_check(repo_root, args.mode, task_dir)
    return validate_post_check(repo_root, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

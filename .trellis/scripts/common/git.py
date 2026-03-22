"""
Git command execution utility.

Single source of truth for running git commands across all Trellis scripts.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr).

    Uses UTF-8 encoding with -c i18n.logOutputEncoding=UTF-8 to ensure
    consistent output across all platforms (Windows, macOS, Linux).
    """
    try:
        git_args = ["git", "-c", "i18n.logOutputEncoding=UTF-8"] + args
        result = subprocess.run(
            git_args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def auto_commit_paths(
    paths: list[str], cwd: Path, commit_msg: str,
) -> tuple[str, str]:
    """Stage and commit the given paths.

    Returns:
        ("committed", "") when a commit was created
        ("clean", "") when no staged changes exist for the given paths
        ("failed", "<reason>") when staging, diff, or commit fails
    """
    rc, _, err = run_git(["add", "-A", "--", *paths], cwd=cwd)
    if rc != 0:
        reason = err.strip() or "git add failed"
        return "failed", f"git add failed: {reason}"

    rc, _, err = run_git(["diff", "--cached", "--quiet", "--", *paths], cwd=cwd)
    if rc == 0:
        return "clean", ""
    if rc != 1:
        reason = err.strip() or "git diff --cached failed"
        return "failed", f"git diff --cached failed: {reason}"

    rc, out, err = run_git(["commit", "-m", commit_msg], cwd=cwd)
    if rc != 0:
        reason = err.strip() or out.strip() or "git commit failed"
        return "failed", f"git commit failed: {reason}"

    return "committed", ""

"""
Safe git-add helpers for Trellis-owned paths.

Why this module exists
----------------------
A real user incident: a project's `.gitignore` listed `.trellis/` (company-wide
template / personal habit). When `add_session.py` and `task.py archive` ran
their auto-commit and `git add` failed with `ignored by .gitignore`, the AI
agent driving the workflow "fixed" it by retrying with
`git add -f .trellis/` — which fan-out-included every ignored subtree
(`.trellis/.backup-*/`, `.trellis/worktrees/`, `.trellis/.template-hashes.json`,
`.trellis/.runtime/`), committing 548 files / 83474 lines of caches/backups.

Design
------
- Scripts only stage SPECIFIC product paths (journal files, index.md, the
  current task dir, the archive dir). Never the whole `.trellis/` tree.
- If plain `git add <specific>` fails with "ignored by", DO NOT retry with
  `-f`. The ignored state is treated as user intent to keep Trellis-owned
  data local-only unless the project is reconfigured explicitly.
- If `git add` fails, print an explicit warning that includes a negative
  example: ``Do NOT use `git add -f .trellis/` ...`` and point at
  `session_auto_commit: false` as the supported opt-out.

The wider-grain forbidden command stays forbidden.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .git import run_git
from .paths import (
    DIR_ARCHIVE,
    DIR_TASKS,
    DIR_WORKFLOW,
    DIR_WORKSPACE,
    FILE_JOURNAL_PREFIX,
    get_current_task,
    get_developer,
)


# Paths under .trellis/ that must NEVER be auto-staged. Listed here so the
# warning to the user can show concrete subpaths to ignore individually
# instead of ignoring the whole `.trellis/` tree.
TRELLIS_IGNORED_SUBPATHS = (
    ".trellis/.backup-*",
    ".trellis/worktrees/",
    ".trellis/.template-hashes.json",
    ".trellis/.runtime/",
    ".trellis/.cache/",
)


def safe_trellis_paths_to_add(repo_root: Path) -> list[str]:
    """Return the list of repo-relative paths the auto-commit should stage.

    Only includes paths that exist on disk so callers don't pass non-existent
    arguments to git. The caller is responsible for `git diff --cached`
    checking afterwards.

    Included:
      - .trellis/workspace/<developer>/journal-*.md
      - .trellis/workspace/<developer>/index.md
      - .trellis/tasks/<current-task>/ if a current task exists
      - .trellis/tasks/archive/      (whole archive subtree, if present)

    Excluded (intentionally — these must not be staged):
      - .trellis/.backup-*, .trellis/worktrees/,
        .trellis/.template-hashes.json, .trellis/.runtime/, .trellis/.cache/
    """
    paths: list[str] = []

    # Workspace journal files + index.md
    developer = get_developer(repo_root)
    if developer:
        ws = repo_root / DIR_WORKFLOW / DIR_WORKSPACE / developer
        if ws.is_dir():
            for f in sorted(ws.glob(f"{FILE_JOURNAL_PREFIX}*.md")):
                if f.is_file():
                    paths.append(
                        f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/{f.name}"
                    )
            index_md = ws / "index.md"
            if index_md.is_file():
                paths.append(
                    f"{DIR_WORKFLOW}/{DIR_WORKSPACE}/{developer}/index.md"
                )

    # Session recording may need the current task metadata when journaling
    # against an active task, but must not sweep unrelated parallel tasks.
    tasks_dir = repo_root / DIR_WORKFLOW / DIR_TASKS
    if tasks_dir.is_dir():
        current_task = get_current_task(repo_root)
        if current_task:
            current_task_path = repo_root / current_task
            if current_task_path.is_dir():
                paths.append(current_task)

        archive_dir = tasks_dir / DIR_ARCHIVE
        if archive_dir.is_dir():
            paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}")

    return list(dict.fromkeys(paths))


def safe_archive_paths_to_add(
    repo_root: Path,
    task_name: str,
    related_task_names: list[str] | None = None,
) -> list[str]:
    """Return paths to stage after `task.py archive`.

    Limited to the archive subtree (where the freshly-moved task lives) plus
    the specific active-task directories that may have been touched by archive
    bookkeeping. This captures the source-path deletion for the archived task
    and any explicitly-known related task metadata updates without sweeping
    unrelated parallel task directories into the same commit.
    """
    paths: list[str] = []
    tasks_dir = repo_root / DIR_WORKFLOW / DIR_TASKS
    if tasks_dir.is_dir():
        # The archive copy.
        archive_dir = tasks_dir / DIR_ARCHIVE
        if archive_dir.is_dir():
            paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{DIR_ARCHIVE}")
        source_task_dir = tasks_dir / task_name
        source_task_rel = f"{DIR_WORKFLOW}/{DIR_TASKS}/{task_name}"
        source_task_probe = f"{source_task_rel}/task.json"
        if source_task_dir.is_dir() or _path_is_tracked(source_task_probe, repo_root):
            paths.append(source_task_rel)
        for related_name in related_task_names or []:
            if not related_name or related_name == task_name:
                continue
            related_dir = tasks_dir / related_name
            if related_dir.is_dir():
                paths.append(f"{DIR_WORKFLOW}/{DIR_TASKS}/{related_name}")
    return list(dict.fromkeys(paths))


def _path_is_tracked(path: str, repo_root: Path) -> bool:
    """Return True when git already tracks the given repo-relative path."""
    rc, _, _ = run_git(["ls-files", "--error-unmatch", "--", path], cwd=repo_root)
    return rc == 0


def _stderr_indicates_ignored(stderr: str) -> bool:
    """git add error indicates the path is excluded by .gitignore."""
    if not stderr:
        return False
    lowered = stderr.lower()
    return "ignored by" in lowered


def safe_git_add(
    paths: list[str],
    repo_root: Path,
    include_removals: bool = False,
) -> tuple[bool, bool, str]:
    """Run `git add` on specific paths without overriding user ignore rules.

    Returns (success, used_force, stderr). On success, callers should still
    `git diff --cached` to detect whether anything was actually staged.

    Behavior:
      - No paths passed → success, no force, empty stderr.
      - Plain `git add <paths>` succeeds → return.
      - Plain fails (ignored or other error) → return failure without retry.
      - `used_force` is kept for caller compatibility and is always False.
    """
    if not paths:
        return True, False, ""

    add_args = ["add"]
    if include_removals:
        add_args.append("-A")
    add_args.extend(["--", *paths])

    rc, _, err = run_git(add_args, cwd=repo_root)
    if rc == 0:
        return True, False, ""

    return False, False, err


def print_gitignore_warning(paths: list[str]) -> None:
    """Explain to the user (and any AI reading the log) what to do.

    CRITICAL: includes the negative example
    ``Do NOT use `git add -f .trellis/``` — agents reading the warning are
    known to invent that command, which fans out to ignored caches/backups.
    """
    print(
        "[WARN] git add failed because .trellis/ paths are ignored by your .gitignore.",
        file=sys.stderr,
    )
    print(
        "[WARN] Trellis manages these specific paths and they should be tracked:",
        file=sys.stderr,
    )
    if paths:
        for p in paths:
            print(f"[WARN]   {p}", file=sys.stderr)
    else:
        print(
            "[WARN]   .trellis/workspace/<developer>/{journal-*.md,index.md}",
            file=sys.stderr,
        )
        print(
            "[WARN]   .trellis/tasks/<task-dir>/",
            file=sys.stderr,
        )
        print(
            "[WARN]   .trellis/tasks/archive/",
            file=sys.stderr,
        )
    print("[WARN]", file=sys.stderr)
    print(
        "[WARN] Recommended: change your .gitignore from `.trellis/` to specific",
        file=sys.stderr,
    )
    print(
        "[WARN] subpaths that should remain ignored, e.g.:",
        file=sys.stderr,
    )
    for sub in TRELLIS_IGNORED_SUBPATHS:
        print(f"[WARN]   {sub}", file=sys.stderr)
    print("[WARN]", file=sys.stderr)
    print(
        "[WARN] If you intentionally keep Trellis state local-only, set",
        file=sys.stderr,
    )
    print(
        "[WARN] `session_auto_commit: false` in `.trellis/config.yaml`.",
        file=sys.stderr,
    )
    print("[WARN]", file=sys.stderr)
    print(
        "[WARN] Do NOT use `git add -f .trellis/` — it pulls in backups, worktrees,",
        file=sys.stderr,
    )
    print(
        "[WARN] and runtime caches that should never be committed.",
        file=sys.stderr,
    )

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / ".trellis" / "scripts"))

import common.task_store as task_store  # noqa: E402


class TaskStoreArchiveAutocommitTests(unittest.TestCase):
    def git(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_repo(self) -> tuple[Path, Path]:
        repo_root = Path(tempfile.mkdtemp(prefix="task-store-archive-"))
        self.addCleanup(shutil.rmtree, repo_root)

        self.git(repo_root, "init")
        self.git(repo_root, "config", "user.email", "test@example.com")
        self.git(repo_root, "config", "user.name", "Task Store Tester")

        task_dir = repo_root / ".trellis" / "tasks" / "04-16-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status": "planning"}\n', encoding="utf-8")

        self.git(repo_root, "add", ".")
        self.git(repo_root, "commit", "-m", "init")
        return repo_root, task_dir

    def test_auto_commit_archive_commits_archived_task_metadata(self) -> None:
        repo_root, task_dir = self.create_repo()

        archive_dir = repo_root / ".trellis" / "tasks" / "archive" / "2026-04"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived_task = archive_dir / task_dir.name
        shutil.move(str(task_dir), str(archived_task))

        ok = task_store._auto_commit_archive(task_dir.name, repo_root, [task_dir.name])
        self.assertTrue(ok)

        status = self.git(repo_root, "status", "--short", "--", ".trellis/tasks")
        self.assertEqual(status.stdout.strip(), "", msg=status.stdout + status.stderr)

        show = self.git(repo_root, "show", "--name-only", "--format=", "HEAD")
        self.assertIn(f'.trellis/tasks/archive/2026-04/{task_dir.name}/task.json', show.stdout)


    def test_auto_commit_archive_skips_when_no_task_changes_are_staged(self) -> None:
        repo_root, task_dir = self.create_repo()

        ok = task_store._auto_commit_archive(task_dir.name, repo_root, [task_dir.name])
        self.assertTrue(ok)

        log = self.git(repo_root, "log", "--oneline", "-1")
        self.assertIn("init", log.stdout)

        status = self.git(repo_root, "status", "--short", "--", ".trellis/tasks")
        self.assertEqual(status.stdout.strip(), "", msg=status.stdout + status.stderr)

    def test_archive_respects_session_auto_commit_config(self) -> None:
        repo_root, task_dir = self.create_repo()
        args = type("Args", (), {"name": task_dir.name, "no_commit": False})()
        with patch.object(task_store, "get_repo_root", return_value=repo_root):
            with patch.object(task_store, "get_session_auto_commit", return_value=False):
                with patch.object(task_store, "_auto_commit_archive") as auto_commit_mock:
                    rc = task_store.cmd_archive(args)

        self.assertEqual(rc, 0)
        auto_commit_mock.assert_not_called()

    def test_auto_commit_archive_respects_session_auto_commit_config(self) -> None:
        repo_root, _ = self.create_repo()

        stderr = StringIO()
        with patch.object(task_store, "get_session_auto_commit", return_value=False):
            with patch.object(task_store, "safe_git_add") as safe_git_add_mock:
                with redirect_stderr(stderr):
                    ok = task_store._auto_commit_archive(
                        "04-16-sample-task",
                        repo_root,
                        ["04-16-sample-task"],
                    )

        self.assertTrue(ok)
        safe_git_add_mock.assert_not_called()
        self.assertIn("session_auto_commit: false", stderr.getvalue())

    def test_auto_commit_archive_reports_git_failure_on_readonly_failure(self) -> None:
        repo_root, _ = self.create_repo()

        stderr = StringIO()
        with patch.object(
            task_store,
            "run_git",
            side_effect=[
                (128, "", "fatal: cannot create '.git/index.lock': Read-only file system"),
                (128, "", "fatal: cannot create '.git/index.lock': Read-only file system"),
            ],
        ):
            with redirect_stderr(stderr):
                ok = task_store._auto_commit_archive(
                    "04-16-sample-task",
                    repo_root,
                    ["04-16-sample-task"],
                )

        self.assertFalse(ok)
        output = stderr.getvalue()
        self.assertIn("Auto-commit failed", output)
        self.assertIn("Read-only file system", output)


if __name__ == "__main__":
    unittest.main()

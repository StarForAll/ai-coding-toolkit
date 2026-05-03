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

        ok = task_store._auto_commit_archive(task_dir.name, repo_root)
        self.assertTrue(ok)

        status = self.git(repo_root, "status", "--short", "--", ".trellis/tasks")
        self.assertEqual(status.stdout.strip(), "", msg=status.stdout + status.stderr)

        show = self.git(repo_root, "show", "--name-only", "--format=", "HEAD")
        self.assertIn(f'.trellis/tasks/archive/2026-04/{task_dir.name}/task.json', show.stdout)


    def test_auto_commit_archive_skips_when_no_task_changes_are_staged(self) -> None:
        repo_root, task_dir = self.create_repo()

        ok = task_store._auto_commit_archive(task_dir.name, repo_root)
        self.assertTrue(ok)

        log = self.git(repo_root, "log", "--oneline", "-1")
        self.assertIn("init", log.stdout)

        status = self.git(repo_root, "status", "--short", "--", ".trellis/tasks")
        self.assertEqual(status.stdout.strip(), "", msg=status.stdout + status.stderr)

    def test_auto_commit_archive_reports_resume_command_on_readonly_failure(self) -> None:
        repo_root, _ = self.create_repo()

        stderr = StringIO()
        with patch.object(
            task_store,
            "run_git",
            side_effect=[
                (128, "", "fatal: cannot create '.git/index.lock': Read-only file system"),
            ],
        ):
            with redirect_stderr(stderr):
                ok = task_store._auto_commit_archive("04-16-sample-task", repo_root)

        self.assertFalse(ok)
        output = stderr.getvalue()
        self.assertIn("archive-commit-only 04-16-sample-task", output)
        self.assertIn("TRELLIS_AUTO_ESCALATE_COMMAND=", output)


if __name__ == "__main__":
    unittest.main()

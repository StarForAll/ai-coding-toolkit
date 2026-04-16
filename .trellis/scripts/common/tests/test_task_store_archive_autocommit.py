from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / ".trellis" / "scripts"))

from common.task_store import _auto_commit_archive  # noqa: E402


class TaskStoreArchiveAutocommitTests(unittest.TestCase):
    def git(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_repo(self) -> tuple[Path, Path, Path]:
        repo_root = Path(tempfile.mkdtemp(prefix="task-store-archive-"))
        self.addCleanup(shutil.rmtree, repo_root)

        self.git(repo_root, "init")
        self.git(repo_root, "config", "user.email", "test@example.com")
        self.git(repo_root, "config", "user.name", "Task Store Tester")

        task_dir = repo_root / ".trellis" / "tasks" / "04-16-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status": "planning"}\n', encoding="utf-8")

        current_task = repo_root / ".trellis" / ".current-task"
        current_task.parent.mkdir(parents=True, exist_ok=True)
        current_task.write_text('.trellis/tasks/04-16-sample-task\n', encoding="utf-8")

        self.git(repo_root, "add", ".")
        self.git(repo_root, "commit", "-m", "init")
        return repo_root, task_dir, current_task

    def test_auto_commit_archive_includes_current_task_cleanup(self) -> None:
        repo_root, task_dir, current_task = self.create_repo()

        archive_dir = repo_root / ".trellis" / "tasks" / "archive" / "2026-04"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived_task = archive_dir / task_dir.name
        shutil.move(str(task_dir), str(archived_task))
        current_task.unlink()

        ok = _auto_commit_archive(task_dir.name, repo_root)

        self.assertTrue(ok)
        status = self.git(repo_root, "status", "--short", "--", ".trellis/tasks", ".trellis/.current-task")
        self.assertEqual(status.stdout.strip(), "", msg=status.stdout + status.stderr)

        show = self.git(repo_root, "show", "--name-only", "--format=", "HEAD")
        self.assertIn('.trellis/.current-task', show.stdout)
        self.assertIn(f'.trellis/tasks/archive/2026-04/{task_dir.name}/task.json', show.stdout)


if __name__ == "__main__":
    unittest.main()

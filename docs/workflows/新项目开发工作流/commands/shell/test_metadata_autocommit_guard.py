from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "metadata-autocommit-guard.py"


class MetadataAutocommitGuardTests(unittest.TestCase):
    def run_script(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), "--project-root", str(repo_root), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def git(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_repo(self) -> tuple[Path, Path, Path]:
        repo_root = Path(tempfile.mkdtemp(prefix="metadata-autocommit-guard-"))
        self.addCleanup(shutil.rmtree, repo_root)

        self.git(repo_root, "init")
        self.git(repo_root, "config", "user.email", "test@example.com")
        self.git(repo_root, "config", "user.name", "Workflow Tester")

        task_dir = repo_root / ".trellis" / "tasks" / "03-30-sample-task"
        workspace_dir = repo_root / ".trellis" / "workspace" / "tester"
        task_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        (task_dir / "task.json").write_text('{"status": "in_progress"}\n', encoding="utf-8")
        (workspace_dir / "index.md").write_text("# tester\n", encoding="utf-8")
        (repo_root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/03-30-sample-task",
            encoding="utf-8",
        )
        (repo_root / "README.md").write_text("# fixture\n", encoding="utf-8")

        self.git(repo_root, "add", ".")
        self.git(repo_root, "commit", "-m", "init")
        return repo_root, task_dir, workspace_dir

    def test_pre_archive_fails_when_target_is_not_current_task(self) -> None:
        repo_root, _, _ = self.create_repo()
        other_task = repo_root / ".trellis" / "tasks" / "03-30-other-task"
        other_task.mkdir(parents=True, exist_ok=True)
        (other_task / "task.json").write_text('{"status": "completed"}\n', encoding="utf-8")

        result = self.run_script(
            repo_root,
            "--mode",
            "archive",
            "--check",
            "pre",
            "--task-dir",
            str(other_task),
        )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("not current task", result.stdout + result.stderr)

    def test_pre_record_session_fails_when_staged_changes_escape_metadata_scope(self) -> None:
        repo_root, _, _ = self.create_repo()
        (repo_root / "README.md").write_text("# modified\n", encoding="utf-8")
        self.git(repo_root, "add", "README.md")

        result = self.run_script(
            repo_root,
            "--mode",
            "record-session",
            "--check",
            "pre",
        )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("outside metadata scope", result.stdout + result.stderr)

    def test_pre_record_session_fails_when_tasks_are_still_dirty(self) -> None:
        repo_root, task_dir, _ = self.create_repo()
        (task_dir / "task.json").write_text('{"status": "completed"}\n', encoding="utf-8")

        result = self.run_script(
            repo_root,
            "--mode",
            "record-session",
            "--check",
            "pre",
        )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn(".trellis/tasks must be clean", result.stdout + result.stderr)

    def test_post_archive_detects_dirty_current_task_pointer(self) -> None:
        repo_root, _, _ = self.create_repo()
        current_task = repo_root / ".trellis" / ".current-task"
        current_task.unlink()

        result = self.run_script(
            repo_root,
            "--mode",
            "archive",
            "--check",
            "post",
        )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn(".trellis/.current-task", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

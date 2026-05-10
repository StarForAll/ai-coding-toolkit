from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
import sys

sys.path.insert(0, str(REPO_ROOT / ".trellis" / "scripts"))

import common.safe_commit as safe_commit  # noqa: E402


class SafeCommitPathSelectionTests(unittest.TestCase):
    def create_repo(self) -> Path:
        repo_root = Path(tempfile.mkdtemp(prefix="safe-commit-"))
        self.addCleanup(shutil.rmtree, repo_root)

        workspace_dir = repo_root / ".trellis" / "workspace" / "tester"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "journal-1.md").write_text("# Journal\n", encoding="utf-8")
        (workspace_dir / "index.md").write_text("# Index\n", encoding="utf-8")

        tasks_dir = repo_root / ".trellis" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / "05-10-current").mkdir()
        (tasks_dir / "05-10-other").mkdir()
        (tasks_dir / "archive").mkdir()

        (repo_root / ".trellis" / ".developer").write_text(
            "name=tester\n",
            encoding="utf-8",
        )
        (repo_root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/05-10-current\n",
            encoding="utf-8",
        )
        runtime_dir = repo_root / ".trellis" / ".runtime" / "sessions"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        session_key = "codex_test-session"
        (runtime_dir / f"{session_key}.json").write_text(
            '{"current_task": ".trellis/tasks/05-10-current"}\n',
            encoding="utf-8",
        )
        self._old_session_id = os.environ.get("CODEX_SESSION_ID")
        os.environ["CODEX_SESSION_ID"] = "test-session"
        self.addCleanup(self._restore_session_id)
        return repo_root

    def _restore_session_id(self) -> None:
        if self._old_session_id is None:
            os.environ.pop("CODEX_SESSION_ID", None)
        else:
            os.environ["CODEX_SESSION_ID"] = self._old_session_id

    def test_safe_trellis_paths_only_include_current_task_not_other_active_tasks(self) -> None:
        repo_root = self.create_repo()

        paths = safe_commit.safe_trellis_paths_to_add(repo_root)

        self.assertIn(".trellis/workspace/tester/journal-1.md", paths)
        self.assertIn(".trellis/workspace/tester/index.md", paths)
        self.assertIn(".trellis/tasks/05-10-current", paths)
        self.assertIn(".trellis/tasks/archive", paths)
        self.assertNotIn(".trellis/tasks/05-10-other", paths)

    def test_safe_archive_paths_include_explicit_related_tasks_only(self) -> None:
        repo_root = self.create_repo()

        paths = safe_commit.safe_archive_paths_to_add(
            repo_root,
            "05-10-current",
            ["05-10-related", "05-10-other"],
        )

        self.assertIn(".trellis/tasks/05-10-current", paths)
        self.assertIn(".trellis/tasks/05-10-other", paths)
        self.assertIn(".trellis/tasks/archive", paths)
        self.assertNotIn(".trellis/tasks/05-10-related", paths)


if __name__ == "__main__":
    unittest.main()

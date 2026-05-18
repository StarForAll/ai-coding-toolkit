from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / ".trellis" / "scripts"))

import add_session  # noqa: E402


class AddSessionAutoCommitConfigTests(unittest.TestCase):
    def git(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_repo(self) -> Path:
        repo_root = Path(tempfile.mkdtemp(prefix="add-session-autocommit-"))
        self.addCleanup(shutil.rmtree, repo_root)

        self.git(repo_root, "init")
        self.git(repo_root, "config", "user.email", "test@example.com")
        self.git(repo_root, "config", "user.name", "Add Session Tester")

        workflow_dir = repo_root / ".trellis"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "config.yaml").write_text(
            "session_auto_commit: false\n",
            encoding="utf-8",
        )
        return repo_root

    def test_main_passes_auto_commit_flag_to_add_session(self) -> None:
        repo_root = self.create_repo()

        with patch.object(add_session, "get_repo_root", return_value=repo_root):
            with patch.object(add_session, "get_current_task", return_value=None):
                with patch.object(add_session, "add_session", return_value=0) as add_session_mock:
                    with patch.object(
                        sys,
                        "argv",
                        ["add_session.py", "--title", "Test Title"],
                    ):
                        rc = add_session.main()

        self.assertEqual(rc, 0)
        # 0.5.17: main() passes auto_commit=not args.no_commit directly;
        # session_auto_commit is checked inside _auto_commit_workspace().
        # With no --no-commit flag, auto_commit is True.
        self.assertEqual(add_session_mock.call_args.kwargs["auto_commit"], True)


if __name__ == "__main__":
    unittest.main()

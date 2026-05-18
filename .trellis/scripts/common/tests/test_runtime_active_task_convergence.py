from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / ".trellis" / "scripts"
ACTIVE_TASK_PATH = SCRIPTS_DIR / "common" / "active_task.py"
TASK_PATH = SCRIPTS_DIR / "task.py"
STATUSLINE_PATH = REPO_ROOT / ".claude" / "hooks" / "statusline.py"
PYTHON = "/ops/softwares/python/bin/python3"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RuntimeActiveTaskConvergenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        cls.active_task = _load_module("trellis_active_task_runtime_test", ACTIVE_TASK_PATH)
        cls.task_module = _load_module("trellis_task_runtime_test", TASK_PATH)
        cls.statusline = _load_module("trellis_statusline_runtime_test", STATUSLINE_PATH)

    def make_repo(self, *, task_name: str = "05-14-sample-task", status: str = "planning") -> Path:
        root = Path(tempfile.mkdtemp(prefix="trellis-runtime-contract-"))
        (root / ".trellis" / ".runtime" / "sessions").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(
            json.dumps(
                {
                    "id": task_name,
                    "name": task_name,
                    "title": "Sample Task",
                    "status": status,
                    "priority": "P2",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return root

    def run_node(self, script: str) -> subprocess.CompletedProcess[str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("TRELLIS_", "CLAUDE_", "OPENCODE_"))
        }
        return subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_cmd_start_without_session_identity_does_not_persist_pointer(self) -> None:
        repo_root = self.make_repo()
        self.addCleanup(shutil.rmtree, repo_root)
        task_dir = repo_root / ".trellis" / "tasks" / "05-14-sample-task"
        args = argparse.Namespace(dir=str(task_dir))

        with (
            patch.object(self.task_module, "get_repo_root", return_value=repo_root),
            patch.object(self.task_module, "resolve_context_key", return_value=None),
            patch.object(self.task_module, "run_task_hooks", return_value=None),
        ):
            exit_code = self.task_module.cmd_start(args)

        self.assertEqual(exit_code, 0)
        task_data = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
        self.assertEqual(task_data["status"], "in_progress")

        # Degraded mode removed in 0.5.17: no fallback file is written.
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        self.assertFalse(
            degraded_path.is_file(),
            "degraded fallback file should NOT be written after degraded mode removal",
        )

    def test_cmd_start_without_session_identity_prints_degraded_hint(self) -> None:
        repo_root = self.make_repo()
        self.addCleanup(shutil.rmtree, repo_root)
        task_dir = repo_root / ".trellis" / "tasks" / "05-14-sample-task"
        args = argparse.Namespace(dir=str(task_dir))
        stdout = io.StringIO()

        with (
            patch.object(self.task_module, "get_repo_root", return_value=repo_root),
            patch.object(self.task_module, "resolve_context_key", return_value=None),
            patch.object(self.task_module, "run_task_hooks", return_value=None),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = self.task_module.cmd_start(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("degraded mode", stdout.getvalue())

    def test_resolve_active_task_returns_none_when_no_session_context(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)

        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertIsNone(active.task_path)
        self.assertEqual(active.source, "none")

    def test_resolve_active_task_prefers_session_fallback_over_none(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        session_path = repo_root / ".trellis" / ".runtime" / "sessions" / "only-session.json"
        session_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertEqual(active.source, "session-fallback:only-session")
        self.assertEqual(active.task_path, ".trellis/tasks/05-14-sample-task")

    def test_resolve_active_task_skips_degraded_when_context_key_exists(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)

        with patch.object(self.active_task, "resolve_context_key", return_value="codex_demo"):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertIsNone(active.task_path)
        self.assertEqual(active.source_type, "none")
        self.assertEqual(active.context_key, "codex_demo")

    def test_clear_active_task_without_session_identity_returns_none(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)

        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            previous = self.active_task.clear_active_task(repo_root)

        self.assertIsNone(previous.task_path)
        self.assertEqual(previous.source, "none")

    def test_clear_task_from_sessions_only_clears_session_files(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)

        cleared = self.active_task.clear_task_from_sessions(
            ".trellis/tasks/05-14-sample-task",
            repo_root,
        )

        # No session files exist for this task, so nothing is cleared.
        self.assertEqual(cleared, 0)

    def test_statusline_keeps_stale_task_visible(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        active = self.active_task.ActiveTask(
            ".trellis/tasks/05-14-stale-task",
            "session",
            "demo",
            stale=True,
        )

        fake_active_task_module = types.ModuleType("common.active_task")
        fake_active_task_module.resolve_active_task = lambda *args, **kwargs: active
        fake_common = types.ModuleType("common")
        fake_common.active_task = fake_active_task_module

        with patch.dict(
            sys.modules,
            {
                "common": fake_common,
                "common.active_task": fake_active_task_module,
            },
        ):
            task = self.statusline._get_current_task(repo_root / ".trellis", {})

        self.assertIsNotNone(task, "statusline should surface stale task state")
        assert task is not None
        self.assertEqual(task["status"], "stale")

    def test_statusline_does_not_surface_degraded_suffix(self) -> None:
        rendered = self.statusline._render_task_line(
            {
                "title": "Sample Task",
                "status": "in_progress",
                "priority": "P2",
                "source": "degraded",
            }
        )

        self.assertIn("(in_progress)", rendered)
        self.assertNotIn("degraded", rendered)

if __name__ == "__main__":
    unittest.main()

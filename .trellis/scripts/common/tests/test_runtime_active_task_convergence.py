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

    def test_cmd_start_without_session_identity_persists_degraded_fallback(self) -> None:
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

        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        self.assertTrue(
            degraded_path.is_file(),
            "degraded mode should persist a fallback active-task file",
        )
        degraded_data = json.loads(degraded_path.read_text(encoding="utf-8"))
        self.assertEqual(
            degraded_data.get("current_task"),
            ".trellis/tasks/05-14-sample-task",
        )

    def test_cmd_start_warns_when_replacing_different_degraded_task(self) -> None:
        repo_root = self.make_repo()
        self.addCleanup(shutil.rmtree, repo_root)
        old_task_dir = repo_root / ".trellis" / "tasks" / "05-14-old-task"
        old_task_dir.mkdir(parents=True, exist_ok=True)
        (old_task_dir / "task.json").write_text(
            json.dumps({"id": "05-14-old-task", "title": "Old Task", "status": "in_progress"}) + "\n",
            encoding="utf-8",
        )
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-old-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
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
        self.assertIn("replacing degraded fallback task", stdout.getvalue())

    def test_resolve_active_task_uses_degraded_fallback_when_no_session_context(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps(
                {
                    "current_task": ".trellis/tasks/05-14-sample-task",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertEqual(active.task_path, ".trellis/tasks/05-14-sample-task")
        self.assertEqual(active.source, "degraded")
        self.assertFalse(active.stale)

    def test_resolve_active_task_prefers_session_fallback_over_degraded(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        session_path = repo_root / ".trellis" / ".runtime" / "sessions" / "only-session.json"
        session_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-other-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertEqual(active.source, "session-fallback:only-session")
        self.assertEqual(active.task_path, ".trellis/tasks/05-14-sample-task")

    def test_resolve_active_task_skips_degraded_when_context_key_exists(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        with patch.object(self.active_task, "resolve_context_key", return_value="codex_demo"):
            active = self.active_task.resolve_active_task(repo_root)

        self.assertIsNone(active.task_path)
        self.assertEqual(active.source_type, "none")
        self.assertEqual(active.context_key, "codex_demo")

    def test_clear_active_task_without_session_identity_clears_degraded_fallback(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps(
                {
                    "current_task": ".trellis/tasks/05-14-sample-task",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        with patch.object(self.active_task, "resolve_context_key", return_value=None):
            previous = self.active_task.clear_active_task(repo_root)

        self.assertEqual(previous.task_path, ".trellis/tasks/05-14-sample-task")
        self.assertEqual(previous.source, "degraded")
        self.assertFalse(degraded_path.exists())

    def test_clear_task_from_sessions_clears_matching_degraded_fallback(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        cleared = self.active_task.clear_task_from_sessions(
            ".trellis/tasks/05-14-sample-task",
            repo_root,
        )

        self.assertEqual(cleared, 1)
        self.assertFalse(degraded_path.exists())

    def test_set_degraded_active_task_rejects_missing_task(self) -> None:
        repo_root = self.make_repo()
        self.addCleanup(shutil.rmtree, repo_root)

        active = self.active_task.set_degraded_active_task(
            ".trellis/tasks/does-not-exist",
            repo_root,
        )

        self.assertIsNone(active)

    def test_same_task_reference_none_none_is_false(self) -> None:
        repo_root = self.make_repo()
        self.addCleanup(shutil.rmtree, repo_root)

        same = self.active_task._same_task_reference(None, None, repo_root)

        self.assertFalse(same)

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

    def test_statusline_marks_degraded_tasks_in_output(self) -> None:
        payload = {
            "model": {"display_name": "Claude"},
            "context_window": {"used_percentage": 12, "context_window_size": 128000},
            "cost": {"total_duration_ms": 120000},
            "rate_limits": {},
        }
        stdout = io.StringIO()

        with (
            patch.object(
                self.statusline,
                "_get_current_task",
                return_value={
                    "title": "Sample Task",
                    "status": "in_progress",
                    "priority": "P2",
                    "source": "degraded",
                },
            ),
            patch.object(self.statusline, "_find_trellis_dir", return_value=REPO_ROOT / ".trellis"),
            patch.object(self.statusline, "_get_developer", return_value="xzc"),
            patch.object(self.statusline, "_count_active_tasks", return_value=1),
            patch.object(self.statusline, "_get_git_branch", return_value="main"),
            patch("sys.stdin", io.StringIO(json.dumps(payload))),
            contextlib.redirect_stdout(stdout),
        ):
            self.statusline.main()

        self.assertIn("degraded", stdout.getvalue())

    def test_opencode_js_uses_degraded_fallback_when_no_session_context(self) -> None:
        repo_root = self.make_repo(status="in_progress")
        self.addCleanup(shutil.rmtree, repo_root)
        degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
        degraded_path.write_text(
            json.dumps({"current_task": ".trellis/tasks/05-14-sample-task"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        script = f"""
import {{ TrellisContext }} from './.opencode/lib/trellis-context.js'
const ctx = new TrellisContext({json.dumps(str(repo_root))})
console.log(JSON.stringify(ctx.getActiveTask(null)))
"""
        with patch.dict(
            os.environ,
            {
                "TRELLIS_CONTEXT_ID": "leaked-session",
                "OPENCODE_RUN_ID": "leaked-opencode-run",
                "CLAUDE_SESSION_ID": "leaked-claude-session",
            },
            clear=False,
        ):
            result = self.run_node(script)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        active = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(active["taskPath"], ".trellis/tasks/05-14-sample-task")
        self.assertEqual(active["source"], "degraded")


if __name__ == "__main__":
    unittest.main()

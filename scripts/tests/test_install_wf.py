import contextlib
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]


def _load():
    path = REPO / "scripts" / "install-wf.py"
    spec = importlib.util.spec_from_file_location("install_wf", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallWfTest(unittest.TestCase):
    def setUp(self):
        self.module = _load()

    def test_env_base_wins_and_trailing_slash_is_removed(self):
        with mock.patch.dict(os.environ, {"WF_FORGEJO_BASE": "https://forgejo.example:13785/"}):
            self.assertEqual(self.module.resolve_base(), "https://forgejo.example:13785")

    def test_missing_base_fails_without_tty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                with self.assertRaises(self.module.InstallError):
                    self.module.resolve_base()

    def test_token_comes_from_environment(self):
        with mock.patch.dict(os.environ, {"FORGEJO_TOKEN": "secret"}):
            self.assertEqual(self.module.resolve_token(), "secret")

    def test_missing_token_is_allowed_noninteractively(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                self.assertEqual(self.module.resolve_token(), "")

    def test_main_runs_local_bootstrap_with_base_and_token_env(self):
        old = self.module.BOOTSTRAP
        self.addCleanup(lambda: setattr(self.module, "BOOTSTRAP", old))
        self.assertTrue(old.is_file())
        captured = {}

        def fake_run(command, env=None, check=False):
            captured["command"] = command
            captured["env"] = env
            class Result:
                returncode = 0
            return Result()

        with mock.patch.dict(os.environ, {"FORGEJO_TOKEN": "secret"}, clear=True):
            with mock.patch.object(self.module.subprocess, "run", fake_run):
                code = self.module.main(["--base", "https://forgejo.example:13785"])
        self.assertEqual(code, 0)
        self.assertEqual(captured["command"][0], sys.executable)
        self.assertTrue(captured["command"][1].endswith("docs/workflows/wf-cli/install.py"))
        self.assertEqual(captured["env"]["WF_FORGEJO_BASE"], "https://forgejo.example:13785")
        self.assertEqual(captured["env"]["FORGEJO_TOKEN"], "secret")

    def test_token_is_not_a_cli_argument(self):
        source = (REPO / "scripts" / "install-wf.py").read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--token"', source)
        self.assertIn("getpass", source)


if __name__ == "__main__":
    unittest.main()

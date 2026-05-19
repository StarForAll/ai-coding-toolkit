#!/usr/bin/env python3
"""Tests for check-quality.py."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "check-quality.py"
PYTHON = sys.executable


class CheckQualityScriptTests(unittest.TestCase):
    def make_task_dir(self) -> Path:
        task_dir = Path(tempfile.mkdtemp(prefix="check-quality-test-"))
        self.addCleanup(shutil.rmtree, task_dir, True)
        return task_dir

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def python_cmd(self, code: str) -> str:
        return f"{shlex.quote(PYTHON)} -c {shlex.quote(code)}"

    def test_reports_not_run_and_fails_when_no_commands_are_provided(self) -> None:
        task_dir = self.make_task_dir()

        result = self.run_script(str(task_dir))

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertGreaterEqual(result.stdout.count("Result: not run"), 3)
        self.assertIn("未提供任何已确认的验证命令", result.stdout)

    def test_omitted_checks_are_not_run_but_do_not_fail_when_other_checks_pass(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")

        result = self.run_script(str(task_dir), "--test-cmd", test_cmd)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("- 测试状态: pass", result.stdout)
        self.assertIn("- Lint 状态: not run", result.stdout)
        self.assertIn("- Type Check 状态: not run", result.stdout)

    def test_extra_checks_capture_stderr_and_fail_summary(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")
        failing_cmd = self.python_cmd("import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)")

        result = self.run_script(
            str(task_dir),
            "--test-cmd", test_cmd,
            "--extra-check", f"Build={failing_cmd}",
        )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("Result: pass", result.stdout)
        self.assertIn("--- Build ---", result.stdout)
        self.assertIn("Result: fail", result.stdout)
        self.assertIn("stdout:\nout", result.stdout)
        self.assertIn("stderr:\nerr", result.stdout)


if __name__ == "__main__":
    unittest.main()

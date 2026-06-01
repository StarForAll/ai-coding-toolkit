#!/usr/bin/env python3
"""Tests for check-quality.py."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock

import importlib.util
from unittest import mock


SCRIPT = Path(__file__).resolve().parent / "check-quality.py"
PYTHON = sys.executable
SPEC = importlib.util.spec_from_file_location("check_quality_module", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECK_QUALITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_QUALITY)


class CheckQualityScriptTests(unittest.TestCase):
    def make_task_dir(self) -> Path:
        task_dir = Path(tempfile.mkdtemp(prefix="check-quality-test-"))
        self.addCleanup(shutil.rmtree, task_dir, True)
        (task_dir / ".trellis").mkdir(parents=True, exist_ok=True)
        (task_dir / ".trellis" / "workflow-installed.json").write_text(
            '{"project_id":"workflowfixture","profile":"outsourcing"}\n',
            encoding="utf-8",
        )
        return task_dir

    def write_install_record(self, task_dir: Path, payload: dict[str, object]) -> None:
        (task_dir / ".trellis" / "workflow-installed.json").write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def make_fake_sonar_bin(self, *, exit_code: int = 0) -> Path:
        bin_dir = Path(tempfile.mkdtemp(prefix="fake-sonar-bin-"))
        self.addCleanup(shutil.rmtree, bin_dir, True)
        sonar = bin_dir / "sonar"
        sonar.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
        sonar.chmod(0o755)
        return bin_dir

    def run_script(self, *args: str, fake_sonar_exit_code: int | None = 0) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if fake_sonar_exit_code is not None:
            bin_dir = self.make_fake_sonar_bin(exit_code=fake_sonar_exit_code)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        else:
            empty_bin = Path(tempfile.mkdtemp(prefix="empty-sonar-bin-"))
            self.addCleanup(shutil.rmtree, empty_bin, True)
            env["PATH"] = str(empty_bin)
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def python_cmd(self, code: str) -> str:
        return f"{shlex.quote(PYTHON)} -c {shlex.quote(code)}"

    def test_reports_not_run_and_fails_when_no_commands_are_provided(self) -> None:
        task_dir = self.make_task_dir()

        result = self.run_script(str(task_dir))

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("Sonar Verify", result.stdout)
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

    def test_sonar_verify_nonzero_exit_fails_main_check(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")

        result = self.run_script(str(task_dir), "--test-cmd", test_cmd, fake_sonar_exit_code=7)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("--- Sonar Verify ---", result.stdout)
        self.assertIn("Result: fail", result.stdout)
        self.assertIn("Exit Code: 7", result.stdout)
        self.assertNotIn("--- 测试状态 ---", result.stdout)
        self.assertIn("主动排查是否存在同类问题", result.stdout)
        self.assertIn("重新执行 `sonar verify -p <project-id>`", result.stdout)

    def test_sonar_command_missing_fails_main_check(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")

        result = self.run_script(str(task_dir), "--test-cmd", test_cmd, fake_sonar_exit_code=None)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("sonar command not found", result.stdout)
        self.assertNotIn("--- 测试状态 ---", result.stdout)

    def test_sonar_timeout_reports_configured_timeout(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")
        with mock.patch.object(
            CHECK_QUALITY.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["sonar", "verify"], timeout=12),
        ):
            with mock.patch.dict(os.environ, {"WORKFLOW_SONAR_VERIFY_TIMEOUT_SECONDS": "12"}, clear=False):
                with mock.patch.object(sys, "argv", [str(SCRIPT), str(task_dir), "--test-cmd", test_cmd]):
                    exit_code = CHECK_QUALITY.main()

        self.assertEqual(exit_code, 1)

    def test_invalid_sonar_timeout_env_falls_back_to_default(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")
        with mock.patch.object(
            CHECK_QUALITY.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["sonar", "verify"], timeout=300),
        ):
            with mock.patch.dict(os.environ, {"WORKFLOW_SONAR_VERIFY_TIMEOUT_SECONDS": "abc"}, clear=False):
                with mock.patch.object(sys, "argv", [str(SCRIPT), str(task_dir), "--test-cmd", test_cmd]):
                    exit_code = CHECK_QUALITY.main()

        self.assertEqual(exit_code, 1)

    def test_missing_project_id_hard_stops_before_checks(self) -> None:
        task_dir = self.make_task_dir()
        self.write_install_record(task_dir, {"profile": "outsourcing"})
        test_cmd = self.python_cmd("print('ok')")

        result = self.run_script(str(task_dir), "--test-cmd", test_cmd)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("缺少有效 project_id", result.stdout + result.stderr)
        self.assertNotIn("=== 质量检查 ===", result.stdout)

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

    def test_scope_is_reported_in_output(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")

        result = self.run_script(
            str(task_dir),
            "--test-cmd", test_cmd,
            "--scope", "frontend,backend,api",
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("手动指定跨层范围: frontend,backend,api", result.stdout)
        self.assertIn("- Cross-Layer Scope: frontend,backend,api", result.stdout)

    def test_git_queries_use_list_form_subprocess_calls(self) -> None:
        task_dir = self.make_task_dir()
        test_cmd = self.python_cmd("print('ok')")
        with mock.patch.object(
            CHECK_QUALITY,
            "run_git_query",
            side_effect=[
                subprocess.CompletedProcess(["git", "diff", "--name-only"], 0, stdout="", stderr=""),
                subprocess.CompletedProcess(
                    ["git", "ls-files", "--others", "--exclude-standard"], 0, stdout="", stderr=""
                ),
            ],
        ) as mocked_git:
            with mock.patch.object(
                CHECK_QUALITY,
                "run_sonar_verify",
                return_value=CHECK_QUALITY.CheckResult(
                    label="Sonar Verify",
                    command="sonar verify -p workflowfixture",
                    status="pass",
                ),
            ):
                with mock.patch.object(sys, "argv", [str(SCRIPT), str(task_dir), "--test-cmd", test_cmd]):
                    exit_code = CHECK_QUALITY.main()

        self.assertEqual(exit_code, 0)
        mocked_git.assert_any_call(["git", "diff", "--name-only"])
        mocked_git.assert_any_call(["git", "ls-files", "--others", "--exclude-standard"])

if __name__ == "__main__":
    unittest.main()

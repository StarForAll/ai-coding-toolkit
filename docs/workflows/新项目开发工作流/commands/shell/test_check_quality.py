from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "check-quality.py"


class CheckQualityScriptTests(unittest.TestCase):
    def run_script(self, project_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        fake_bin = project_dir / "fake-bin"
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(
            [PYTHON, str(SCRIPT), str(project_dir), *extra_args],
            cwd=project_dir,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def write_package_manager_stub(self, project_dir: Path, name: str) -> None:
        fake_bin = project_dir / "fake-bin"
        fake_bin.mkdir(exist_ok=True)
        log_file = project_dir / "commands.log"
        script = fake_bin / name
        script.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                echo "{name} $@" >> "{log_file}"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)

    def test_runs_explicit_commands_from_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            project_dir = Path(temp_root)
            self.write_package_manager_stub(project_dir, "npm")
            self.write_package_manager_stub(project_dir, "pytest")

            result = self.run_script(
                project_dir,
                "--test-cmd",
                "pytest -q",
                "--lint-cmd",
                "npm run lint",
                "--typecheck-cmd",
                "npm run type-check",
            )

            log_text = (project_dir / "commands.log").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("pytest -q", log_text)
        self.assertIn("npm run lint", log_text)
        self.assertIn("npm run type-check", log_text)

    def test_skips_checks_when_commands_are_not_provided(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            project_dir = Path(temp_root)
            result = self.run_script(project_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("未提供已确认命令，跳过", result.stdout)
        self.assertFalse((project_dir / "commands.log").exists())


if __name__ == "__main__":
    unittest.main()

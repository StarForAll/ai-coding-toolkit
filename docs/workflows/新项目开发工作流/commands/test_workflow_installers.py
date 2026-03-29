from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
COMMANDS_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands"
INSTALL_SCRIPT = COMMANDS_DIR / "install-workflow.py"
UPGRADE_SCRIPT = COMMANDS_DIR / "upgrade-compat.py"
UNINSTALL_SCRIPT = COMMANDS_DIR / "uninstall-workflow.py"
PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"


class WorkflowInstallerTests(unittest.TestCase):
    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_fixture(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="workflow-installers-"))
        (root / ".claude" / "commands" / "trellis").mkdir(parents=True)
        (root / ".trellis").mkdir(parents=True)
        (root / ".claude" / "commands" / "trellis" / "start.md").write_text(
            "# /trellis:start\n\n"
            "Original baseline start command for fixture testing.\n\n"
            "## Operation Types\n\n"
            "| Marker | Meaning |\n"
            "|--------|---------|\n"
            "| `[AI]` | tool calls |\n"
            "| `[USER]` | user actions |\n",
            encoding="utf-8",
        )
        (root / ".trellis" / ".version").write_text("2.0.0\n", encoding="utf-8")
        return root

    def install_workflow(self, fixture_root: Path) -> subprocess.CompletedProcess[str]:
        return self.run_script(INSTALL_SCRIPT, "--project-root", str(fixture_root))

    def test_upgrade_check_detects_phase_router_drift_even_when_versions_match(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        backup_start = fixture / ".claude" / "commands" / "trellis" / ".backup-original" / "start.md"
        target_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        shutil.copy2(backup_start, target_start)

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Phase Router 丢失", result.stdout)

    def test_upgrade_check_detects_missing_helper_scripts(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        helper = fixture / ".trellis" / "scripts" / "workflow" / "plan-validate.py"
        helper.unlink()
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--check", "--project-root", str(fixture))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("辅助脚本缺失", result.stdout)
        self.assertIn("plan-validate.py", result.stdout)

    def test_force_recovers_start_from_backup_when_injection_marker_is_missing(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        broken_start = fixture / ".claude" / "commands" / "trellis" / "start.md"
        broken_start.write_text(
            "# broken start\n\n"
            "This file intentionally lacks the expected injection marker.\n",
            encoding="utf-8",
        )
        (fixture / ".trellis" / ".version").write_text("2.1.0\n", encoding="utf-8")

        result = self.run_script(UPGRADE_SCRIPT, "--force", "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(PHASE_ROUTER_MARKER, broken_start.read_text(encoding="utf-8"))
        self.assertNotIn("无法自动注入", result.stdout)

    def test_uninstall_tolerates_corrupted_install_record(self) -> None:
        fixture = self.create_fixture()
        self.addCleanup(shutil.rmtree, fixture)

        install = self.install_workflow(fixture)
        self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)

        record = fixture / ".trellis" / "workflow-installed.json"
        record.write_text("{ invalid json", encoding="utf-8")

        result = self.run_script(UNINSTALL_SCRIPT, "--project-root", str(fixture))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-installed.json", result.stdout)
        self.assertFalse(record.exists())
        self.assertFalse((fixture / ".trellis" / "scripts" / "workflow").exists())
        self.assertTrue((fixture / ".claude" / "commands" / "trellis" / "start.md").exists())


if __name__ == "__main__":
    unittest.main()

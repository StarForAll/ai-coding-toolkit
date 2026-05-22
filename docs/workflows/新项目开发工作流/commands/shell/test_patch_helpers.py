from __future__ import annotations

import importlib.util
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
SHELL_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell"
PATCH_SCRIPTS = [
    SHELL_DIR / "patch-inject-workflow-state.py",
    SHELL_DIR / "patch-session-start-strong-gate.py",
    SHELL_DIR / "patch-task-start-strong-gate.py",
    SHELL_DIR / "patch-task-create-preserve-active.py",
    SHELL_DIR / "patch-task-status-view-strong-gate.py",
    SHELL_DIR / "patch-workflow-phase.py",
    SHELL_DIR / "patch-workflow-phase-strong-gate.py",
]


class PatchHelperScriptTests(unittest.TestCase):
    def test_patch_helpers_support_help(self) -> None:
        for script in PATCH_SCRIPTS:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [PYTHON, str(script), "--help"],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                self.assertIn("usage:", result.stdout.lower())
                self.assertNotIn("does not exist", result.stdout + result.stderr)
                self.assertNotIn("不存在", result.stdout + result.stderr)

    def test_patch_workflow_phase_preserves_docstring(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="workflow-phase-docstring-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "workflow_phase.py"
        target.write_text(
            "def get_step(step_id):\n"
            "    \"\"\"Return the legacy step body.\"\"\"\n"
            "    return f'legacy step {step_id}'\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_workflow_phase", SHELL_DIR / "patch-workflow-phase.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_workflow_phase(target)
        self.assertTrue(applied, "patch_workflow_phase should patch the docstring fixture")

        runtime_spec = importlib.util.spec_from_file_location("patched_workflow_phase_docstring", target)
        self.assertIsNotNone(runtime_spec)
        self.assertIsNotNone(runtime_spec.loader)
        runtime_module = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime_module)

        self.assertEqual(runtime_module.get_step.__doc__, "Return the legacy step body.")


if __name__ == "__main__":
    unittest.main()

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

    def test_patch_inject_workflow_state_maps_stale_suffixes_to_stale_block(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="inject-workflow-state-stale-"))
        self.addCleanup(shutil.rmtree, root)
        target = root / "inject-workflow-state.py"
        target.write_text(
            "import re\n"
            "from pathlib import Path\n"
            "from typing import Optional\n\n"
            "def get_active_task(root: Path, input_data: dict):\n"
            "    active = input_data['active']\n"
            "    task_id = active.task_path\n"
            "    task_dir = root / task_id\n"
            "    if active.stale:\n"
            "        return task_dir.name, f\"stale_{active.source_type}\", active.source\n"
            "    data = {'status': 'planning'}\n"
            "    status = data.get('status', '')\n"
            "    if not status:\n"
            "        return None\n"
            "    return task_id, status, active.source\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Breadcrumb loading: parse workflow.md, fall back to hardcoded defaults\n"
            "# ---------------------------------------------------------------------------\n"
            "def load_breadcrumbs(root: Path) -> dict[str, str]:\n"
            "    workflow = root / \".trellis\" / \"workflow.md\"\n"
            "    if not workflow.is_file():\n"
            "        return {}\n"
            "    try:\n"
            "        content = workflow.read_text(encoding=\"utf-8\")\n"
            "    except OSError:\n"
            "        return {}\n"
            "    result: dict[str, str] = {}\n"
            "    return result\n\n"
            "def build_breadcrumb(\n"
            "    task_id: Optional[str],\n"
            "    status: str,\n"
            "    templates: dict[str, str],\n"
            "    source: str | None = None,\n"
            "    breadcrumb_key: str | None = None,\n"
            ") -> str:\n"
            "    lookup_key = breadcrumb_key or status\n"
            "    body = templates.get(lookup_key)\n"
            "    if body is None and lookup_key != status:\n"
            "        body = templates.get(status)\n"
            "    if body is None:\n"
            "        body = 'Refer to workflow.md for current step.'\n"
            "    header_lines = [f'Status: {status}' if task_id is None else f'Task: {task_id} ({status})']\n"
            "    if source:\n"
            "        header_lines.append(f'Source: {source}')\n"
            "    header = '\\n'.join(header_lines)\n"
            "    return f'<workflow-state>\\n{header}\\n{body}\\n</workflow-state>'\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Entry\n"
            "# ---------------------------------------------------------------------------\n"
            "def main() -> int:\n"
            "    templates = {}\n"
            "    task = ('task', 'stale_session', 'session:demo')\n"
            "    if task is None:\n"
            "        return 0\n"
            "    else:\n"
            "        task_id, status, source = task\n"
            "        status_key = status\n"
            "        breadcrumb = build_breadcrumb(\n"
            "            task_id, status, templates, source, breadcrumb_key=status_key\n"
            "        )\n"
            "    return 0\n",
            encoding="utf-8",
        )

        spec = importlib.util.spec_from_file_location("patch_inject_workflow_state", SHELL_DIR / "patch-inject-workflow-state.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        applied = module.patch_python_hook(target)
        self.assertTrue(applied, "patch_python_hook should patch stale suffix handling")

        patched = target.read_text(encoding="utf-8")
        self.assertIn('status.startswith("stale_")', patched)
        self.assertIn('lookup_key.startswith("stale_")', patched)
        self.assertIn('lookup_key = "stale"', patched)
        self.assertIn('display_status = "stale"', patched)


if __name__ == "__main__":
    unittest.main()

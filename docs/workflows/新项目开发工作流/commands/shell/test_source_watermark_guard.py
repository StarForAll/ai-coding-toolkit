from __future__ import annotations

import json
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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "source-watermark-guard.py"

PLAN = """\
# Source Watermark Plan

## WMID
- `WMID`: `wm_demo_001`

## Protected Watermark Snippets

### `src/protected.py`
- `id`: `visible-header`
- `expected`: `# watermark: wm_demo_001`
- `repair`: `replace-if-missing`
- `insert-after`: `# module: protected`
- `notes`: `visible watermark header`
"""


class SourceWatermarkGuardTests(unittest.TestCase):
    def seed_install_record(self, root: Path) -> None:
        (root / ".trellis").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "workflow-installed.json").write_text(
            '{"project_id":"workflowfixture","profile":"outsourcing"}\n',
            encoding="utf-8",
        )

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_task_dir(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="source-watermark-guard-"))
        self.addCleanup(shutil.rmtree, path)
        self.seed_install_record(path)
        return path

    def seed_task(self, task_dir: Path, *, plan: str = PLAN, source_text: str = "") -> None:
        design_dir = task_dir / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "source-watermark-plan.md").write_text(plan, encoding="utf-8")
        src_dir = task_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "protected.py").write_text(source_text, encoding="utf-8")

    def test_check_passes_when_expected_snippet_present(self) -> None:
        task_dir = self.make_task_dir()
        self.seed_task(
            task_dir,
            source_text="# module: protected\n# watermark: wm_demo_001\nprint('ok')\n",
        )
        result = self.run_script("--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_check_fails_when_snippet_missing(self) -> None:
        task_dir = self.make_task_dir()
        self.seed_task(task_dir, source_text="# module: protected\nprint('ok')\n")
        result = self.run_script("--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("watermark-preservation-broken", result.stdout + result.stderr)

    def test_repair_reinserts_missing_snippet(self) -> None:
        task_dir = self.make_task_dir()
        self.seed_task(task_dir, source_text="# module: protected\nprint('ok')\n")
        result = self.run_script("--task-dir", str(task_dir), "--mode", "repair")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("watermark-repaired", result.stdout)
        repaired = (task_dir / "src" / "protected.py").read_text(encoding="utf-8")
        self.assertIn("# watermark: wm_demo_001", repaired)

    def test_repair_fails_without_anchor(self) -> None:
        task_dir = self.make_task_dir()
        self.seed_task(task_dir, source_text="print('ok')\n")
        result = self.run_script("--task-dir", str(task_dir), "--mode", "repair")
        self.assertEqual(result.returncode, 1)
        self.assertIn("watermark-repair-blocked", result.stdout + result.stderr)

    def test_warns_when_plan_has_no_protected_snippets(self) -> None:
        task_dir = self.make_task_dir()
        self.seed_task(
            task_dir,
            plan="# Source Watermark Plan\n\n## WMID\n- `WMID`: `wm_demo_001`\n",
            source_text="# module: protected\nprint('ok')\n",
        )
        result = self.run_script("--task-dir", str(task_dir), "--json")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["code"], "missing-protected-snippets")


if __name__ == "__main__":
    unittest.main()

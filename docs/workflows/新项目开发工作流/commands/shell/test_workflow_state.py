from __future__ import annotations

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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "workflow-state.py"


class WorkflowStateScriptTests(unittest.TestCase):
    def run_script(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_fixture(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="workflow-state-test-"))
        self.addCleanup(shutil.rmtree, root)
        (root / ".trellis" / "tasks").mkdir(parents=True, exist_ok=True)
        task_dir = root / ".trellis" / "tasks" / "04-15-sample-task"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text('{"status":"planning","children":[]}\n', encoding="utf-8")
        (root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/04-15-sample-task\n",
            encoding="utf-8",
        )
        return root, task_dir

    def test_init_and_validate_pass_with_current_task_pointer(self) -> None:
        root, task_dir = self.make_fixture()
        (root / "docs" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "requirements" / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")

        init = self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(init.returncode, 0, msg=init.stdout + init.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)
        self.assertIn("workflow-state 校验通过", validate.stdout)

    def test_validate_rejects_unknown_state_version(self) -> None:
        root, task_dir = self.make_fixture()
        (root / "docs" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "requirements" / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        state_path = task_dir / "workflow-state.json"
        text = state_path.read_text(encoding="utf-8").replace('"version": 1', '"version": 999')
        state_path.write_text(text, encoding="utf-8")

        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("version 非法或暂不支持", validate.stdout)

    def test_validate_fails_when_current_task_is_empty(self) -> None:
        root, task_dir = self.make_fixture()
        (root / "docs" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "requirements" / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")
        (root / ".trellis" / ".current-task").write_text("", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn(".trellis/.current-task 不能为空", validate.stdout)

    def test_validate_fails_when_current_task_points_to_another_task(self) -> None:
        root, task_dir = self.make_fixture()
        (root / ".trellis" / ".current-task").write_text(
            ".trellis/tasks/04-15-other-task\n",
            encoding="utf-8",
        )
        (root / "docs" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "requirements" / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "brainstorm")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("与当前 task", validate.stdout)

    def test_validate_fails_when_task_has_children(self) -> None:
        root, task_dir = self.make_fixture()
        (task_dir / "task.json").write_text('{"status":"planning","children":["04-15-child-task"]}\n', encoding="utf-8")
        (root / "docs" / "requirements").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "requirements" / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "plan")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("不应继续作为执行态叶子任务", validate.stdout)

    def test_validate_fails_when_design_before_arch_confirm_has_developer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        requirements_dir.mkdir(parents=True, exist_ok=True)
        (requirements_dir / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 1, msg=validate.stdout + validate.stderr)
        self.assertIn("developer-facing-prd.md", validate.stdout)

    def test_validate_passes_after_arch_confirm_with_developer_prd(self) -> None:
        root, task_dir = self.make_fixture()
        requirements_dir = root / "docs" / "requirements"
        requirements_dir.mkdir(parents=True, exist_ok=True)
        (requirements_dir / "customer-facing-prd.md").write_text("# customer\n", encoding="utf-8")
        (requirements_dir / "developer-facing-prd.md").write_text("# developer\n", encoding="utf-8")

        self.run_script("init", str(task_dir), "--stage", "design")
        self.run_script(
            "set",
            str(task_dir),
            "--architecture-confirmed",
            "true",
            "--stage-status",
            "in_progress",
        )
        validate = self.run_script("validate", str(task_dir), "--project-root", str(root))

        self.assertEqual(validate.returncode, 0, msg=validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()

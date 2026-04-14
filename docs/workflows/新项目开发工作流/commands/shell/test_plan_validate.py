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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "plan-validate.py"

VALID_PLAN = """# Task Plan: Sample

## 概述
- 需求来源：示例
- 目标：验证脚本

## 项目域执行策略
- 后端域：.trellis/tasks/04-14-task-a → .trellis/tasks/04-14-task-b（域内串行，不自动续跑）

## Trellis Task 清单

| 任务路径 | 类型 | 项目域 | 说明 |
|---------|------|--------|------|
| .trellis/tasks/04-14-task-a | implementation | 后端域 | 完成基础能力 |
| .trellis/tasks/04-14-task-b | implementation | 后端域 | 依赖 task-a |
| .trellis/tasks/04-14-project-audit | project-audit | 全局 | 全部代码相关 task 完成后才允许开始 |

## 依赖关系

- .trellis/tasks/04-14-task-b 依赖 .trellis/tasks/04-14-task-a
- .trellis/tasks/04-14-project-audit 依赖全部代码相关 task 完成

## 门禁摘要

- 项目级全局门禁：lint / typecheck / test / quality gate
- task 级门禁：进入某个 task 实现前，由 /trellis:start 自动执行 before-dev，并把当前有效门禁落到 $TASK_DIR/before-dev.md

## 任务图摘要

- 主链：.trellis/tasks/04-14-task-a → .trellis/tasks/04-14-task-b
- 全局终局任务：.trellis/tasks/04-14-project-audit
"""

LEGACY_PLAN = VALID_PLAN + """

## 执行安排
- 当前可开始任务：TASK-A
- 等待中任务：TASK-B
- 推荐并行组：无
- 串行主链：TASK-A → TASK-B
"""


class PlanValidateScriptTests(unittest.TestCase):
    def run_script(self, task_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), str(task_dir)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_task_fixture(self, root: Path) -> Path:
        task_root = root / ".trellis" / "tasks"
        task_root.mkdir(parents=True, exist_ok=True)
        current_task = task_root / "04-14-plan-root"
        current_task.mkdir(parents=True, exist_ok=True)
        for name in ("04-14-task-a", "04-14-task-b", "04-14-project-audit"):
            (task_root / name).mkdir(parents=True, exist_ok=True)
        return current_task

    def write_plan(self, directory: Path, content: str) -> None:
        (directory / "task_plan.md").write_text(content, encoding="utf-8")

    def test_valid_plan_passes_structure_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Trellis Task 清单列名正确", result.stdout)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_legacy_execution_markers_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_plan(task_dir, LEGACY_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("仍包含旧版执行矩阵字段", result.stdout)

    def test_missing_required_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_plan(task_dir, VALID_PLAN.replace("\n## 门禁摘要\n", "\n"))

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("缺少章节: 门禁摘要", result.stdout)

    def test_missing_task_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            shutil.rmtree(root / ".trellis" / "tasks" / "04-14-task-b")
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("存在不存在的任务路径", result.stdout)

    def test_missing_before_dev_marker_in_gate_summary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            broken = VALID_PLAN.replace("before-dev.md", "task-gate.md")
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("门禁摘要缺少项目级全局门禁或 before-dev.md 说明", result.stdout)

    def test_positive_auto_continue_wording_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            broken = VALID_PLAN.replace("域内串行，不自动续跑", "域内串行，自动续跑")
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("项目域执行策略未写清“域内串行、不自动续跑”", result.stdout)


if __name__ == "__main__":
    unittest.main()

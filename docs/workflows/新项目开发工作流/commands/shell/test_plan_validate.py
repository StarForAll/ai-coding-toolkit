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

## 当前推荐执行任务（待确认）
- 任务路径：.trellis/tasks/04-14-task-a
- 任务标题：TASK-A
- 本轮目标：完成基础能力
- 本轮不做：不推进 task-b
- 前置依赖：无
- 验收锚点：基础能力可验证
- 风险提醒：边界变化先回 plan
- 推荐主执行 CLI：Codex

## 依赖关系

- .trellis/tasks/04-14-task-b 依赖 .trellis/tasks/04-14-task-a
- .trellis/tasks/04-14-project-audit 依赖全部代码相关 task 完成

## 早期探针与骨架任务

- `walking_skeleton_or_smoke`: ST0 先打通最短路径 smoke
- `packaging_skeleton`: ST1 先产出最小打包骨架；纯后端项目可写 not_applicable + 原因
- `performance_probe`: ST1B 输出首次性能基线

## 自动化策略摘要

- `ci_strategy`: GitHub Actions 负责 lint/typecheck/test/build
- `local_vs_ci_boundary`: 本地只跑 typecheck + unit test，CI 跑完整矩阵

## 范围收敛与降级预案

- `kill_criteria`: 若跨平台基线在 ST1 仍未成立，则回退并缩减平台承诺
- `p1_downgrade_candidates`: Linux 高级安装体验可降为 P1

## 门禁摘要

- 项目级全局门禁：lint / typecheck / test / quality gate
- task 级门禁：进入某个 task 实现前，由 /trellis:start 自动执行 before-dev，并把当前有效门禁落到 $TASK_DIR/before-dev.md

## 任务图摘要

- 主链：.trellis/tasks/04-14-task-a → .trellis/tasks/04-14-task-b
- 全局终局任务：.trellis/tasks/04-14-project-audit

## 阶段出口快照

- `frozen_lanes`: backend, qa, packaging
- `current_recommended_task`: .trellis/tasks/04-14-task-a
- `open_blockers`: none
- `reopen_conditions`: 若 smoke / packaging skeleton 失败则回到 plan
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

    def run_help(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), "--help"],
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

    def write_leaf_prd(self, root: Path, task_name: str) -> None:
        task_dir = root / ".trellis" / "tasks" / task_name
        (task_dir / "prd.md").write_text(
            "# Leaf Task\n\n## Goal\n\n验证 leaf task ready 产物。\n\n## In Scope\n\n- 校验最小 task-ready 产物。\n\n## Out of Scope\n\n- 不进入实现。\n\n## Acceptance Anchors\n\n- 校验脚本通过。\n\n## Preferred CLI\n\n- Codex\n",
            encoding="utf-8",
        )

    def write_leaf_prd_with_content(self, root: Path, task_name: str, content: str) -> None:
        task_dir = root / ".trellis" / "tasks" / task_name
        (task_dir / "prd.md").write_text(content, encoding="utf-8")

    def write_plan(self, directory: Path, content: str) -> None:
        (directory / "task_plan.md").write_text(content, encoding="utf-8")

    def test_valid_plan_passes_structure_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Trellis Task 清单列名正确", result.stdout)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_help_exits_without_requiring_task_plan(self) -> None:
        result = self.run_help()

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("用法: python3 plan-validate.py [task_dir]", result.stdout)
        self.assertNotIn("task_plan.md 不存在", result.stdout)

    def test_legacy_execution_markers_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            self.write_plan(task_dir, LEGACY_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("仍包含旧版执行矩阵字段", result.stdout)

    def test_missing_required_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            self.write_plan(task_dir, VALID_PLAN.replace("\n## 门禁摘要\n", "\n"))

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("缺少章节: 门禁摘要", result.stdout)

    def test_missing_early_probe_fields_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            broken = VALID_PLAN.replace("- `performance_probe`: ST1B 输出首次性能基线\n", "")
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("早期探针与骨架任务 缺少结构化字段", result.stdout)

    def test_placeholder_scope_downgrade_fields_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            broken = VALID_PLAN.replace(
                "- `p1_downgrade_candidates`: Linux 高级安装体验可降为 P1\n",
                "- `p1_downgrade_candidates`: TBD\n",
            )
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("范围收敛与降级预案 存在空值或占位内容", result.stdout)

    def test_missing_task_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            shutil.rmtree(root / ".trellis" / "tasks" / "04-14-task-b")
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("存在不存在的任务路径", result.stdout)

    def test_missing_before_dev_marker_in_gate_summary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            broken = VALID_PLAN.replace("before-dev.md", "task-gate.md")
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("门禁摘要缺少项目级全局门禁或 before-dev.md 说明", result.stdout)

    def test_positive_auto_continue_wording_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            broken = VALID_PLAN.replace("域内串行，不自动续跑", "域内串行，自动续跑")
            self.write_plan(task_dir, broken)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("项目域执行策略未写清“域内串行、不自动续跑”", result.stdout)

    def test_missing_recommended_leaf_prd_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("当前推荐执行任务对应 leaf task 缺少最小 prd.md", result.stdout)

    def test_recommended_leaf_prd_placeholder_content_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd_with_content(
                root,
                "04-14-task-a",
                "# Leaf Task\n\n## Goal\n\nTBD\n\n## In Scope\n\n- 待补充\n\n## Out of Scope\n\n- ...\n\n## Acceptance Anchors\n\n- TBD\n\n## Preferred CLI\n\n- 待补充\n",
            )
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("章节仍是空值或占位内容", result.stdout)

    def test_recommended_leaf_prd_missing_required_sections_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd_with_content(
                root,
                "04-14-task-a",
                "# Leaf Task\n\n## Goal\n\n验证 leaf task ready 产物。\n",
            )
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("prd.md 缺少章节", result.stdout)

    def test_tasks_prefix_path_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            plan_with_tasks_prefix = VALID_PLAN.replace(
                ".trellis/tasks/04-14-task-a",
                "tasks/04-14-task-a",
            ).replace(
                ".trellis/tasks/04-14-task-b",
                "tasks/04-14-task-b",
            ).replace(
                ".trellis/tasks/04-14-project-audit",
                "tasks/04-14-project-audit",
            )
            self.write_plan(task_dir, plan_with_tasks_prefix)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_dot_slash_tasks_prefix_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            plan_with_dot_slash_tasks_prefix = VALID_PLAN.replace(
                ".trellis/tasks/04-14-task-a",
                "./tasks/04-14-task-a",
            ).replace(
                ".trellis/tasks/04-14-task-b",
                "./tasks/04-14-task-b",
            ).replace(
                ".trellis/tasks/04-14-project-audit",
                "./tasks/04-14-project-audit",
            )
            self.write_plan(task_dir, plan_with_dot_slash_tasks_prefix)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_bilingual_section_falls_back_to_non_empty_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd_with_content(
                root,
                "04-14-task-a",
                "# Leaf Task\n\n## Goal\n\nTBD\n\n## 目标\n\n验证 leaf task ready 产物。\n\n## In Scope\n\nTBD\n\n## 范围\n\n- 校验最小 task-ready 产物。\n\n## Out of Scope\n\nTBD\n\n## 不做\n\n- 不进入实现。\n\n## Acceptance Anchors\n\nTBD\n\n## 验收锚点\n\n- 校验脚本通过。\n\n## Preferred CLI\n\nTBD\n\n## 推荐主执行 CLI\n\n- Codex\n",
            )
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("当前推荐执行任务对应 leaf task 已补齐最小 prd.md", result.stdout)

    def test_placeholder_variants_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd_with_content(
                root,
                "04-14-task-a",
                "# Leaf Task\n\n## Goal\n\n待补充。\n\n## In Scope\n\n- TODO later\n\n## Out of Scope\n\n- 后续补充\n\n## Acceptance Anchors\n\n- FIXME\n\n## Preferred CLI\n\n- TBD soon\n",
            )
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("章节仍是空值或占位内容", result.stdout)

    def test_placeholder_prefix_collision_does_not_fail_valid_leaf_prd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd_with_content(
                root,
                "04-14-task-a",
                "# Leaf Task\n\n## Goal\n\nTODOist integration\n\n## In Scope\n\n- 处理 FIXME-1234 缺陷同步。\n\n## Out of Scope\n\n- 不进入实现。\n\n## Acceptance Anchors\n\n- 校验脚本通过。\n\n## Preferred CLI\n\n- Codex\n",
            )
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("当前推荐执行任务对应 leaf task 已补齐最小 prd.md", result.stdout)

    def test_task_table_description_with_todoist_is_not_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            task_dir = self.create_task_fixture(root)
            self.write_leaf_prd(root, "04-14-task-a")
            plan_with_valid_todoist_description = VALID_PLAN.replace(
                "完成基础能力",
                "实现 TODOist 集成模块",
                1,
            )
            self.write_plan(task_dir, plan_with_valid_todoist_description)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Trellis Task 清单填写完整", result.stdout)


if __name__ == "__main__":
    unittest.main()

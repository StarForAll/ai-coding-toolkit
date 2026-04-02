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
- 预估工时：2小时

## 任务拆解 Checklist

### Phase 1: 基础设施
- [ ] TASK-A：完成基础能力
- [ ] TASK-A2：准备独立支线

### Phase 2: 核心功能
- [ ] TASK-B：依赖 TASK-A
- [ ] TASK-C：依赖 TASK-B

## 文件修改清单

| 文件路径 | 操作类型 | 说明 |
|---------|---------|------|
| src/a.ts | 修改 | 示例 |

## 验收标准

- [ ] 标准1：结构完整
- [ ] 标准2：状态合法

## 依赖关系

- 前置任务：TASK-B 依赖 TASK-A；TASK-C 依赖 TASK-B
- 阻塞任务：TASK-A 阻塞 TASK-B；TASK-B 阻塞 TASK-C
- 并行任务：TASK-A2 可与 TASK-A 并行

## 执行安排

- 当前可开始任务：TASK-A, TASK-A2
- 等待中任务：
  - TASK-B（等待 TASK-A 完成）
  - TASK-C（等待 TASK-B 完成）
- 推荐并行组：TASK-A + TASK-A2
- 串行主链：TASK-A → TASK-B → TASK-C

## 任务执行矩阵

| 任务ID | 前置任务 | 当前状态 | 开始条件 | 等待原因 | 并行属性 | 冲突说明 |
|-------|---------|---------|---------|---------|---------|---------|
| TASK-A | 无 | 可开始 | 需求、接口、环境、资源已就绪 | 无 | 候选可并行 | 当前可与 TASK-A2 并行，不可与其后续依赖任务并行 |
| TASK-B | TASK-A | 等待中 | TASK-A 完成后可开始 | 等待 TASK-A 完成 | 依赖不可并行 | 依赖 TASK-A 输出 |
| TASK-C | TASK-B | 等待中 | TASK-B 完成后可开始 | 等待 TASK-B 完成 | 依赖不可并行 | 依赖 TASK-B 输出 |
| TASK-A2 | 无 | 可开始 | 需求、接口、环境、资源已就绪 | 无 | 候选可并行 | 不修改主链核心模块 |
"""

ALL_COMPLETED_PLAN = VALID_PLAN.replace("| TASK-A | 无 | 可开始 |", "| TASK-A | 无 | 已完成 |").replace(
    "| TASK-A2 | 无 | 可开始 |", "| TASK-A2 | 无 | 已完成 |"
).replace(
    "| TASK-B | TASK-A | 等待中 | TASK-A 完成后可开始 | 等待 TASK-A 完成 |",
    "| TASK-B | TASK-A | 已完成 | TASK-A 完成后可开始 | 已完成，无等待 |",
).replace(
    "| TASK-C | TASK-B | 等待中 | TASK-B 完成后可开始 | 等待 TASK-B 完成 |",
    "| TASK-C | TASK-B | 已完成 | TASK-B 完成后可开始 | 已完成，无等待 |",
).replace(
    "- 当前可开始任务：TASK-A, TASK-A2\n- 等待中任务：\n  - TASK-B（等待 TASK-A 完成）\n  - TASK-C（等待 TASK-B 完成）\n- 推荐并行组：TASK-A + TASK-A2\n- 串行主链：TASK-A → TASK-B → TASK-C",
    "- 当前可开始任务：无\n- 等待中任务：无\n- 推荐并行组：无\n- 串行主链：TASK-A → TASK-B → TASK-C（已全部完成）",
)


class PlanValidateScriptTests(unittest.TestCase):
    def run_script(self, task_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), str(task_dir)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_plan(self, directory: Path, content: str) -> None:
        (directory / "task_plan.md").write_text(content, encoding="utf-8")

    def test_valid_plan_passes_structure_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            self.write_plan(task_dir, VALID_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("任务执行矩阵列名正确", result.stdout)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_missing_execution_matrix_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            content = VALID_PLAN.replace("\n## 任务执行矩阵\n\n| 任务ID | 前置任务 | 当前状态 | 开始条件 | 等待原因 | 并行属性 | 冲突说明 |\n|-------|---------|---------|---------|---------|---------|---------|\n| TASK-A | 无 | 可开始 | 需求、接口、环境、资源已就绪 | 无 | 候选可并行 | 当前可与 TASK-A2 并行，不可与其后续依赖任务并行 |\n| TASK-B | TASK-A | 等待中 | TASK-A 完成后可开始 | 等待 TASK-A 完成 | 依赖不可并行 | 依赖 TASK-A 输出 |\n| TASK-C | TASK-B | 等待中 | TASK-B 完成后可开始 | 等待 TASK-B 完成 | 依赖不可并行 | 依赖 TASK-B 输出 |\n| TASK-A2 | 无 | 可开始 | 需求、接口、环境、资源已就绪 | 无 | 候选可并行 | 不修改主链核心模块 |\n", "")
            self.write_plan(task_dir, content)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("缺少章节: 任务执行矩阵", result.stdout)
        self.assertIn("结构验证未通过", result.stdout)

    def test_invalid_status_enum_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            content = VALID_PLAN.replace("| TASK-A | 无 | 可开始 |", "| TASK-A | 无 | ready |")
            self.write_plan(task_dir, content)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("当前状态只能使用", result.stdout)
        self.assertIn("结构验证未通过", result.stdout)

    def test_waiting_task_without_reason_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            content = VALID_PLAN.replace("| TASK-B | TASK-A | 等待中 | TASK-A 完成后可开始 | 等待 TASK-A 完成 |", "| TASK-B | TASK-A | 等待中 | TASK-A 完成后可开始 | 无 |")
            self.write_plan(task_dir, content)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertIn("等待中任务未写明有效等待原因", result.stdout)
        self.assertIn("结构验证未通过", result.stdout)

    def test_non_waiting_task_with_empty_wait_reason_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            content = VALID_PLAN.replace(
                "| TASK-A | 无 | 可开始 | 需求、接口、环境、资源已就绪 | 无 | 候选可并行 | 当前可与 TASK-A2 并行，不可与其后续依赖任务并行 |",
                "| TASK-A | 无 | 可开始 | 需求、接口、环境、资源已就绪 |  | 候选可并行 | 当前可与 TASK-A2 并行，不可与其后续依赖任务并行 |",
            )
            self.write_plan(task_dir, content)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("开始条件与等待原因填写完整", result.stdout)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_bracket_references_are_treated_as_meaningful_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            content = (
                VALID_PLAN
                .replace("TASK-A 完成后可开始", "[TASK-A] 完成后可开始", 1)
                .replace("等待 TASK-A 完成", "[TASK-A] 尚未完成", 1)
                .replace("依赖 TASK-A 输出", "[TASK-A] 输出未就绪", 1)
            )
            self.write_plan(task_dir, content)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("并行属性与冲突说明填写完整", result.stdout)
        self.assertIn("task_plan.md 结构验证通过", result.stdout)

    def test_all_completed_plan_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            task_dir = Path(temp_root)
            self.write_plan(task_dir, ALL_COMPLETED_PLAN)

            result = self.run_script(task_dir)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("任务执行矩阵可支持当前执行判断", result.stdout)
        self.assertIn("结构验证通过", result.stdout)


if __name__ == "__main__":
    unittest.main()

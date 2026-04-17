from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "ownership-proof-validate.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))

COMPLETE_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
- `source_watermark_level`: `hybrid`
- `source_watermark_channels`: `visible,zero-width,subtle-markers,zero-watermark`
- `zero_width_watermark_enabled`: `yes`
- `subtle_code_marker_enabled`: `yes`
- `ownership_proof_required`: `yes`
"""

MINIMAL_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
"""

BASIC_VISIBLE_ASSESSMENT = """\
# 评估
- 总体决策：接
- 是否允许进入 brainstorm：是
- `source_watermark_level`: `basic`
- `source_watermark_channels`: `visible`
- `zero_width_watermark_enabled`: `no`
- `subtle_code_marker_enabled`: `no`
- `ownership_proof_required`: `yes`
"""

SOURCE_WATERMARK_PLAN = """\
# Source Watermark Plan

## WMID
- `WMID`: `wm_demo_001`

## Watermark Channels
- visible
- zero-width
- subtle
- zero-watermark

## Zero-Width Channel
- 只允许放在注释、文档字符串、markdown 中
- 禁止放入标识符、配置键、SQL、路径

## Subtle Marker Channel
- 在稳定 helper 中放置 subtle marker fragment

## Excluded Paths
- vendor/
- generated/
- migrations/

## Extraction
- 记录提取步骤和片段组合方式

## Verification
- 记录验证命令、校验 hash 和复核方式
"""

VISIBLE_ONLY_WATERMARK_PLAN = """\
# Source Watermark Plan

## WMID
- `WMID`: `wm_demo_001`

## Watermark Channels
- visible

## Excluded Paths
- vendor/
- generated/
- migrations/

## Extraction
- 记录提取步骤和片段组合方式

## Verification
- 记录验证命令、校验 hash 和复核方式
"""

PLAN_WITH_WATERMARK_TASKS = """\
# Task Plan

## 当前推荐执行任务（待确认）

- 可见源码水印任务
- 零宽字符水印任务
- 隐蔽代码标识任务
- 水印验证任务
- 归属证明包任务

## 依赖关系

- 先完成 `source-watermark-plan.md`
"""

DELIVERY_DIR_CONTENT = {
    "ownership-proof.md": "# Ownership Proof\n\n- WMID: wm_demo_001\n- SHA256: abcdef\n- timestamp: 2026-04-17T12:00:00Z\n",
    "source-watermark-verification.md": "# Source Watermark Verification\n\n- visible watermark: pass\n- zero-width watermark: pass\n- subtle marker verification: pass\n- zero-watermark fingerprint: pass\n",
    "deliverables.md": "# Deliverables\n\n- ownership-proof.md\n- source-watermark-verification.md\n- WMID reference\n",
    "transfer-checklist.md": "# Transfer Checklist\n\n- ownership-proof.md 已附带\n- source-watermark-verification.md 已附带\n- WMID 已记录\n",
}


class OwnershipProofValidateTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def _make_task_dir(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="ownership-proof-"))
        self.addCleanup(shutil.rmtree, path)
        return path

    def test_feasibility_fails_when_assessment_missing(self) -> None:
        task_dir = self._make_task_dir()
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)

    def test_feasibility_fails_when_watermark_policy_missing(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(MINIMAL_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("source_watermark_level", result.stdout + result.stderr)

    def test_feasibility_passes_when_policy_complete(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_feasibility_fails_when_zero_width_enabled_but_channel_missing(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace(
            "`source_watermark_channels`: `visible,zero-width,subtle-markers,zero-watermark`",
            "`source_watermark_channels`: `visible,subtle-markers,zero-watermark`",
        )
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("zero-width", result.stdout + result.stderr)

    def test_feasibility_fails_when_subtle_enabled_but_channel_missing(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace(
            "`source_watermark_channels`: `visible,zero-width,subtle-markers,zero-watermark`",
            "`source_watermark_channels`: `visible,zero-width,zero-watermark`",
        )
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("subtle-markers", result.stdout + result.stderr)

    def test_feasibility_fails_when_ownership_required_but_level_none(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace("`source_watermark_level`: `hybrid`", "`source_watermark_level`: `none`")
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("source_watermark_level", result.stdout + result.stderr)

    def test_feasibility_fails_when_visible_channel_missing(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace(
            "`source_watermark_channels`: `visible,zero-width,subtle-markers,zero-watermark`",
            "`source_watermark_channels`: `zero-width,subtle-markers,zero-watermark`",
        )
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "feasibility", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("visible", result.stdout + result.stderr)

    def test_design_fails_when_plan_missing(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("source-watermark-plan", result.stdout + result.stderr)

    def test_design_skips_when_ownership_proof_not_required(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace("`ownership_proof_required`: `yes`", "`ownership_proof_required`: `no`")
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("跳过", result.stdout)

    def test_design_passes_when_plan_complete(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        design_dir = task_dir / "design"
        design_dir.mkdir()
        (design_dir / "source-watermark-plan.md").write_text(SOURCE_WATERMARK_PLAN, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_design_passes_for_basic_level_with_visible_only_channel(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(BASIC_VISIBLE_ASSESSMENT, encoding="utf-8")
        design_dir = task_dir / "design"
        design_dir.mkdir()
        (design_dir / "source-watermark-plan.md").write_text(VISIBLE_ONLY_WATERMARK_PLAN, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_design_fails_when_plan_allows_zero_width_in_identifier(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        design_dir = task_dir / "design"
        design_dir.mkdir()
        content = SOURCE_WATERMARK_PLAN + "\n- 零宽字符可以放入标识符中\n"
        (design_dir / "source-watermark-plan.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("禁区位置", result.stdout + result.stderr)

    def test_plan_fails_when_required_tasks_missing(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        (task_dir / "task_plan.md").write_text("# Task Plan\n", encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("零宽字符水印任务", result.stdout + result.stderr)

    def test_plan_passes_when_required_tasks_exist(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        (task_dir / "task_plan.md").write_text(PLAN_WITH_WATERMARK_TASKS, encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_plan_skips_when_ownership_proof_not_required(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace("`ownership_proof_required`: `yes`", "`ownership_proof_required`: `no`")
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "plan", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("跳过", result.stdout)

    def test_design_fails_when_ownership_required_but_level_missing(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace("`source_watermark_level`: `hybrid`\n", "")
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "design", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("source_watermark_level", result.stdout + result.stderr)

    def test_delivery_fails_when_required_files_missing(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 1)

    def test_delivery_passes_when_required_files_exist(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        delivery_dir = task_dir / "delivery"
        delivery_dir.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery_dir / name).write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_delivery_skips_zero_watermark_when_channel_not_enabled(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace(
            "`source_watermark_channels`: `visible,zero-width,subtle-markers,zero-watermark`",
            "`source_watermark_channels`: `visible,zero-width,subtle-markers`",
        )
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        delivery_dir = task_dir / "delivery"
        delivery_dir.mkdir()
        modified = dict(DELIVERY_DIR_CONTENT)
        modified["source-watermark-verification.md"] = (
            "# Source Watermark Verification\n\n"
            "- visible watermark: pass\n"
            "- zero-width watermark: pass\n"
            "- subtle marker verification: pass\n"
        )
        for name, file_content in modified.items():
            (delivery_dir / name).write_text(file_content, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_delivery_skips_when_ownership_proof_not_required(self) -> None:
        task_dir = self._make_task_dir()
        content = COMPLETE_ASSESSMENT.replace("`ownership_proof_required`: `yes`", "`ownership_proof_required`: `no`")
        (task_dir / "assessment.md").write_text(content, encoding="utf-8")
        result = self.run_script("--phase", "delivery", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("跳过", result.stdout)

    def test_parse_channels_normalizes_chinese_aliases(self) -> None:
        spec = importlib.util.spec_from_file_location("ownership_proof_validate", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        parsed = module.parse_channels("可见,零宽,隐蔽,零水印")
        self.assertEqual(parsed, {"visible", "zero-width", "subtle-markers", "zero-watermark"})

    def test_all_phases_reports_total(self) -> None:
        task_dir = self._make_task_dir()
        (task_dir / "assessment.md").write_text(COMPLETE_ASSESSMENT, encoding="utf-8")
        design_dir = task_dir / "design"
        design_dir.mkdir()
        (design_dir / "source-watermark-plan.md").write_text(SOURCE_WATERMARK_PLAN, encoding="utf-8")
        (task_dir / "task_plan.md").write_text(PLAN_WITH_WATERMARK_TASKS, encoding="utf-8")
        delivery_dir = task_dir / "delivery"
        delivery_dir.mkdir()
        for name, content in DELIVERY_DIR_CONTENT.items():
            (delivery_dir / name).write_text(content, encoding="utf-8")
        result = self.run_script("--all", "--task-dir", str(task_dir))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("总计", result.stdout)


if __name__ == "__main__":
    unittest.main()

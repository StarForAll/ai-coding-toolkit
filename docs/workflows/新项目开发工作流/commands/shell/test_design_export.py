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
SCRIPT = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands" / "shell" / "design-export.py"
VALID_TAD = """# TAD

## 架构冻结清单
- `runtime_host`: tauri2
- `application_stack`: react + typescript + vite
- `persistence_strategy`: sqlite
- `primary_processing_stack`: pdfium + libvips
- `distribution_strategy`: desktop bundle + prompt update
- `remaining_unfrozen_items`: none
- `reopen_conditions`: 仅当运行时宿主、分发策略或主处理引擎变化时 reopen

## 系统边界与外部依赖
- `system_boundary`: 桌面端 PDF 处理应用
- `external_dependencies`: pdfium, libvips, OS file system
- `boundary_crossings`: renderer -> backend command, local file IO
- `ownership_boundaries`: 核心处理链路由本项目负责，OS shell 不可控
- `fallback_assumptions`: 若 PDFium 不可用则停止发布并回到 design

## 风险与回退
- 主要风险：打包体积与跨平台兼容
- 回退策略：优先保留 walking skeleton 与 canary build

## 阶段出口快照
- `completed_blocks`: A,B,C,D
- `current_status`: waiting_user_confirmation
- `open_risks`: linux package canary 待在 plan 执行
"""


class DesignExportTests(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def _make_design_dir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="design-export-test-"))
        self.addCleanup(shutil.rmtree, d)
        return d

    def _write_required(self, d: Path) -> None:
        (d / "index.md").write_text("# index\n\n- design 索引\n", encoding="utf-8")
        (d / "TAD.md").write_text(VALID_TAD, encoding="utf-8")
        (d / "ODD-dev.md").write_text("# ODD-dev\n\n## 开发操作流\n- 进入实现前先确认 contracts。\n", encoding="utf-8")
        (d / "ODD-user.md").write_text("# ODD-user\n\n## 用户操作流\n- 用户先选文件再确认导出。\n", encoding="utf-8")

    # ── validate ──

    def test_validate_fails_when_dir_missing(self) -> None:
        result = self.run_script("--validate", "/tmp/nonexistent-design-dir-xyz")
        self.assertEqual(result.returncode, 1)
        self.assertIn("目录不存在", result.stdout)

    def test_validate_fails_when_required_files_missing(self) -> None:
        d = self._make_design_dir()
        (d / "index.md").write_text("# index\n\n- valid body\n", encoding="utf-8")
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("缺失", result.stdout)

    def test_validate_passes_with_all_required_files(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("完整性检查通过", result.stdout)
        self.assertIn("不等于 design 阶段可退出", result.stdout)
        self.assertIn("workflow-state.py validate", result.stdout)

    def test_validate_fails_when_tad_missing_freeze_fields(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        (d / "TAD.md").write_text("# TAD\n\n## 架构冻结清单\n- `runtime_host`: tauri2\n", encoding="utf-8")
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("TAD.md 缺少结构化冻结字段", result.stdout)

    def test_validate_fails_when_required_file_has_only_title(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        (d / "ODD-user.md").write_text("# ODD-user\n", encoding="utf-8")
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("只有标题或占位内容", result.stdout)

    def test_validate_marks_optional_files(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        result = self.run_script("--validate", str(d))
        self.assertIn("条件文档", result.stdout)

    def test_validate_passes_without_conditional_files(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_validate_passes_without_pages_dir(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        # Do NOT create pages/
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_validate_fails_when_stitch_prompt_missing_baseline_terms(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        (d / "STITCH-PROMPT.md").write_text("# STITCH-PROMPT\n", encoding="utf-8")
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 1)
        self.assertIn("缺少 Stitch DESIGN.md / 去 AI 味基线项", result.stdout)

    def test_validate_passes_with_full_stitch_prompt_baseline_terms(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        (d / "STITCH-PROMPT.md").write_text(
            "\n".join(
                [
                    "# STITCH-PROMPT",
                    "该文件同时承担 Stitch DESIGN.md 的设计系统语义",
                    "UI 界面文案默认使用中文",
                    "给 Stitch 的执行 prompt 默认使用英文",
                    "先在 Stitch 生成首版原型，再进入 Figma 做现代视觉风格参考",
                    "Figma 只作为整体视觉风格参考，不作为具体内容布局照抄依据",
                    "不要通用 SaaS 模板感",
                    "不要廉价渐变和无意义炫光装饰",
                    "不要过度圆角、过度玻璃拟态、过度悬浮阴影",
                    "不要无信息密度的卡片堆砌",
                    "不要与业务无关的装饰性图形或占位文案",
                    "不要“英雄区 + 三栏卖点 + 泛化插画”的通用 AI 生成组合",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.run_script("--validate", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    # ── scaffold ──

    def test_scaffold_creates_all_docs_and_dirs(self) -> None:
        d = self._make_design_dir()
        result = self.run_script("--scaffold", str(d))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        for name in [
            "index",
            "TAD",
            "ODD-dev",
            "ODD-user",
            "DDD",
            "IDD",
            "AID",
            "STITCH-PROMPT",
        ]:
            self.assertTrue((d / f"{name}.md").exists(), f"{name}.md should be created")
        self.assertTrue((d / "specs").is_dir())
        self.assertTrue((d / "pages").is_dir())

    def test_scaffold_does_not_overwrite_existing(self) -> None:
        d = self._make_design_dir()
        (d / "TAD.md").write_text("# custom TAD\n", encoding="utf-8")
        self.run_script("--scaffold", str(d))
        self.assertEqual((d / "TAD.md").read_text(encoding="utf-8"), "# custom TAD\n")


if __name__ == "__main__":
    unittest.main()

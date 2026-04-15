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
        for name in ["index.md", "TAD.md", "ODD-dev.md", "ODD-user.md"]:
            (d / name).write_text(f"# {name}\n", encoding="utf-8")

    # ── validate ──

    def test_validate_fails_when_dir_missing(self) -> None:
        result = self.run_script("--validate", "/tmp/nonexistent-design-dir-xyz")
        self.assertEqual(result.returncode, 1)
        self.assertIn("目录不存在", result.stdout)

    def test_validate_fails_when_required_files_missing(self) -> None:
        d = self._make_design_dir()
        (d / "index.md").write_text("# index\n", encoding="utf-8")
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
        self.assertIn("缺少去 AI 味基线项", result.stdout)

    def test_validate_passes_with_full_stitch_prompt_baseline_terms(self) -> None:
        d = self._make_design_dir()
        self._write_required(d)
        (d / "STITCH-PROMPT.md").write_text(
            "\n".join(
                [
                    "# STITCH-PROMPT",
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

"""Regression tests for scripts/validate-wf-design.py.

The checker is the only mechanical guard on the wf design contract, so it must
prove it still catches the failures it claims to catch. Each test runs the real
script against mutated document copies (WF_DESIGN_ROOT override),
never against the working tree.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "validate-wf-design.py"
FILES = (
    "wf-framework-design.md", "wf-framework-charter.md",
    "wf-framework-design.index.md", "wf-framework-design.sources.md",
    "wf-framework-mechanism.md",
)


class CheckerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "docs" / "workflows").mkdir(parents=True)
        for name in FILES:
            shutil.copy(REPO / "docs" / "workflows" / name, self.tmp / "docs" / "workflows" / name)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_checker(self):
        env = dict(os.environ, WF_DESIGN_ROOT=str(self.tmp))
        return subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env
        )

    def edit(self, name, old, new):
        path = self.tmp / "docs" / "workflows" / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_clean_copy_passes(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_consumer_section_fails(self):
        # Remove one section from a lexical-candidate cell; the checker must
        # report it as a missing consumer. The row is picked from the file, so
        # the test does not break when the index is renumbered or rewritten.
        path = self.tmp / "docs" / "workflows" / "wf-framework-design.index.md"
        lines = path.read_text(encoding="utf-8").split("\n")
        mutated = False
        for i, ln in enumerate(lines):
            if not ln.startswith("| ") or "---" in ln or "定义（名称" in ln:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) >= 6 and cells[2].count("§") >= 2:
                refs = cells[2].split("、")
                cells[2] = "、".join(refs[:-1])
                lines[i] = "| " + " | ".join(cells) + " |"
                mutated = True
                break
        self.assertTrue(mutated, "no row with two or more lexical candidates found")
        path.write_text("\n".join(lines), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("消费点缺项", result.stdout)

    def test_three_level_reference_fails(self):
        self.edit(
            "wf-framework-design.md",
            "## 1. 定位与基础契约",
            "见 §5.4.1 的三级引用。\n\n## 1. 定位与基础契约",
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("三级以下引用", result.stdout)

    def test_three_level_reference_in_index_fails(self):
        # Insert a §N.N.M reference into the index; the checker must reject it
        # instead of truncating it to §N.N. The row is picked from the file.
        path = self.tmp / "docs" / "workflows" / "wf-framework-design.index.md"
        lines = path.read_text(encoding="utf-8").split("\n")
        mutated = False
        for i, ln in enumerate(lines):
            if not ln.startswith("| ") or "---" in ln or "定义（名称" in ln:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) < 6:
                continue
            m = re.search(r"§(\d+\.\d+)", cells[2])
            if m:
                cells[2] = cells[2].replace(m.group(0), m.group(0) + ".9", 1)
                lines[i] = "| " + " | ".join(cells) + " |"
                mutated = True
                break
        self.assertTrue(mutated, "no row with a two-level section reference found")
        path.write_text("\n".join(lines), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("三级以下引用", result.stdout)

    def test_index_missing_column_fails(self):
        # Dropping the review-state column must not bypass the state check.
        path = self.tmp / "docs" / "workflows" / "wf-framework-design.index.md"
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, ln in enumerate(lines):
            if not ln.startswith("| ") or "---" in ln or "定义（名称" in ln:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) == 6:
                lines[i] = "| " + " | ".join(cells[:-1]) + " |"
                break
        else:
            self.fail("no six-column index row found")
        path.write_text("\n".join(lines), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("列数应为 6", result.stdout)

    def test_blank_tier_scenario_fails(self):
        # An empty scenario name used to be skipped as a table separator row.
        path = self.tmp / "docs" / "workflows" / "wf-framework-design.md"
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, ln in enumerate(lines):
            if not ln.startswith("| "):
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if len(cells) == 4 and "需人裁决" in cells[1]:
                cells[0] = ""
                lines[i] = "| " + " | ".join(cells) + " |"
                break
        else:
            self.fail("no three-tier row found")
        path.write_text("\n".join(lines), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("缺场景名", result.stdout)

    def test_invalid_review_state_fails(self):
        self.edit("wf-framework-design.index.md", "| 已核对·有消费 |", "| 已核对 |")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("核对状态", result.stdout)

    def test_missing_mechanism_fails(self):
        (self.tmp / "docs/workflows/wf-framework-mechanism.md").unlink()
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("机制稿缺失", result.stdout)

    def test_mechanism_references_resolve_by_owner(self):
        path = self.tmp / "docs/workflows/wf-framework-mechanism.md"
        original = path.read_text(encoding="utf-8")
        cases = (
            ("本文 §99.1", "引用不存在"),
            # Section 12 exists only in the mechanism: wrong-owner references
            # must not accidentally validate against its own headings.
            ("设计稿 §12.1", "引用不存在"),
            ("设计稿 §1.1、§12.1", "引用不存在"),
            ("本文 §5.3.9", "引用不存在"),
            ("charter T99", "引用不存在"),
            ("见 §1.1", "引用缺所有者"),
            ("本文 §1.1；另见 §1.2", "引用缺所有者"),
        )
        for reference, diagnostic in cases:
            with self.subTest(reference=reference):
                path.write_text(original + "\n" + reference + "\n", encoding="utf-8")
                result = self.run_checker()
                self.assertEqual(result.returncode, 1)
                self.assertIn(diagnostic, result.stdout)

    def test_grouped_references_keep_their_explicit_owner(self):
        path = self.tmp / "docs/workflows/wf-framework-mechanism.md"
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\n本文 §1.1、§1.2；设计稿 §1.1、§4.2\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mechanism_missing_binary_mapping_fails(self):
        self.edit("wf-framework-mechanism.md", "`规划授权`；", "")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("二值场景缺映射", result.stdout)

    def test_mechanism_unknown_binary_mapping_fails(self):
        self.edit("wf-framework-mechanism.md", "`规划授权`", "`不存在的规划场景`")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("二值场景悬空", result.stdout)

    def test_mechanism_missing_decision_mapping_fails(self):
        path = self.tmp / "docs/workflows/wf-framework-mechanism.md"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        lines = [line for line in lines if not line.startswith("| `审查不可用` |")]
        path.write_text("".join(lines), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("三档场景缺映射", result.stdout)

    def test_mechanism_unknown_decision_mapping_fails(self):
        self.edit("wf-framework-mechanism.md", "| `审查不可用` |", "| `未知裁决场景` |")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("三档场景悬空", result.stdout)

    def test_baseline_drift_fails_for_each_input(self):
        for name in FILES[:-1]:
            with self.subTest(name=name):
                path = self.tmp / "docs/workflows" / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                result = self.run_checker()
                path.write_bytes(original)
                self.assertEqual(result.returncode, 1)
                self.assertIn("输入摘要不符", result.stdout)
                self.assertIn(name, result.stdout)

    def test_missing_baseline_row_fails(self):
        path = self.tmp / "docs/workflows/wf-framework-mechanism.md"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        path.write_text("".join(line for line in lines if not line.startswith(
            "| wf-framework-design.sources.md |"
        )), encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("输入摘要缺项", result.stdout)

    def test_malformed_baseline_digest_fails(self):
        self.edit("wf-framework-mechanism.md", "| wf-framework-design.md | ",
                  "| wf-framework-design.md | invalid-")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("输入摘要格式", result.stdout)

    def test_missing_baseline_source_fails_cleanly(self):
        (self.tmp / "docs/workflows/wf-framework-design.sources.md").unlink()
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("输入文件不可读", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_mechanism_metrics_are_reported(self):
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"机制稿：引用 \d+；二值场景 \d+/\d+；三档场景 \d+/\d+；输入摘要 4/4")


if __name__ == "__main__":
    unittest.main()

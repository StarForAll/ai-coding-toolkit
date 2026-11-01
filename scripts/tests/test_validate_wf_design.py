"""Regression tests for scripts/validate-wf-design.py.

The checker is the only mechanical guard on the wf design contract, so it must
prove it still catches the failures it claims to catch. Each test runs the real
script against a mutated copy of the three documents (WF_DESIGN_ROOT override),
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
FILES = ("wf-framework-design.md", "wf-framework-charter.md", "wf-framework-design.index.md")


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


if __name__ == "__main__":
    unittest.main()

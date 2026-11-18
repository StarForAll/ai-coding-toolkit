"""Regression tests for scripts/check-wf-analysis.py 的小节引用检查。

校验器是 wf 方案文档小节引用的唯一机械防线，所以必须证明它抓得住自己声称的失效
形态，而不只是「跑起来退出 0」。每个用例在自动清理的临时目录里按仓库相对位置复制
实际脚本、当前完整方案文档和行号检查所需的 `wflib/*.py`，只改自己的文档副本，再用
子进程执行副本。这样判据表、schema、计数等其余检查仍以真实前提运行，修改前的实现
也能用同一入口证明漏检。
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-wf-analysis.py"
DOC = Path("docs/workflows/wf/analysis/proposal-repairing-state.md")
WFLIB = Path("docs/workflows/wf/payload/lib/wflib")
HISTORY_HEADING = "## 9. 本文的历史（只留与 ⑥ 相关的关键否决）"


class CheckWfAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wf-doc-lint-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        script = self.tmp / "scripts" / SCRIPT.name
        script.parent.mkdir(parents=True)
        shutil.copy2(SCRIPT, script)
        self.doc = self.tmp / DOC
        self.doc.parent.mkdir(parents=True)
        shutil.copy2(REPO / DOC, self.doc)
        lib = self.tmp / WFLIB
        lib.mkdir(parents=True)
        for source in sorted((REPO / WFLIB).glob("*.py")):
            shutil.copy2(source, lib / source.name)

    def run_checker(self):
        return subprocess.run(
            [sys.executable, str(self.tmp / "scripts" / SCRIPT.name)],
            capture_output=True,
            text=True,
        )

    def read_lines(self):
        text = self.doc.read_text(encoding="utf-8")
        body = text[:-1] if text.endswith("\n") else text
        return body.split("\n")

    def write_lines(self, lines):
        self.doc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def line_of(self, needle):
        for number, line in enumerate(self.read_lines(), 1):
            if needle in line:
                return number
        self.fail("文档副本里找不到插入行：%s" % needle)

    def insert_after(self, anchor, *new_lines):
        lines = self.read_lines()
        index = next((i for i, line in enumerate(lines) if line.startswith(anchor)), None)
        self.assertIsNotNone(index, "文档副本里找不到锚点行：%s" % anchor)
        lines[index + 1:index + 1] = list(new_lines)
        self.write_lines(lines)

    def append(self, *new_lines):
        lines = self.read_lines()
        lines.extend(new_lines)
        self.write_lines(lines)

    def remove_section(self, anchor):
        """删除以 anchor 开头的二级小节，直到下一个 `## ` 标题或文末。"""
        lines = self.read_lines()
        start = next((i for i, line in enumerate(lines) if line.startswith(anchor)), None)
        self.assertIsNotNone(start, "文档副本里找不到待删小节：%s" % anchor)
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
                   len(lines))
        del lines[start:end]
        self.write_lines(lines)

    def assert_reports(self, result, *fragments):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for fragment in fragments:
            self.assertIn(fragment, result.stdout)

    def assert_passes(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # -- 基线 ------------------------------------------------------------
    def test_clean_copy_passes(self):
        self.assert_passes(self.run_checker())

    # -- 完整编号：一、二级与字母后缀 -----------------------------------
    def test_reachable_references_pass(self):
        self.append("回归：§4 与 §2.1 与 §6a 均可达；句末句点也要通过 §2.")
        self.assert_passes(self.run_checker())

    def test_dangling_references_report_full_number_and_line(self):
        # 一级、普通二级、字母后缀二级各一行：每一处都要单独报告完整编号与实际行号。
        self.append(
            "回归：一级引用 §98 悬空。",
            "回归：二级引用 §4.9 悬空。",
            "回归：带字母的二级引用 §6a.1 悬空。",
        )
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §98 不存在" % self.line_of("§98 悬空"),
            "[引用] L%d §4.9 不存在（不回退到上级小节）" % self.line_of("§4.9 悬空"),
            "[引用] L%d §6a.1 不存在" % self.line_of("§6a.1 悬空"),
        )

    def test_letter_suffixed_reference_passes_with_its_own_heading(self):
        # `§6a.1` 不能靠上级 `§6a` 通过；但登记了完整标题后就该通过。
        self.insert_after("### 6a. 指引交付", "### 6a.1 回归子节", "回归：§6a.1 已登记。")
        self.assert_passes(self.run_checker())

    def test_three_level_reference_fails_despite_valid_prefix(self):
        # `§4.3` 存在，`§4.3.9` 不存在：不得截断成前缀，也不得抬成「未超过两级」。
        self.append("回归：三级引用 §4.3.9 悬空。")
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §4.3.9 超过两级" % self.line_of("§4.3.9 悬空"),
        )

    # -- 历史豁免区间 ----------------------------------------------------
    def test_reference_inside_history_section_passes(self):
        self.insert_after(HISTORY_HEADING, "回归：§98 只在历史小节内出现。")
        self.assert_passes(self.run_checker())

    def test_same_reference_after_history_section_fails(self):
        # §9 的历史豁免不能截到文末：§10 的正式裁定仍要受检。
        self.insert_after("## 10. 已定项", "回归：§98 出现在正式裁定内。")
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §98 不存在" % self.line_of("§98 出现在正式裁定内"),
        )

    def test_unnumbered_heading_ends_history_exemption(self):
        self.append("## 回归附录", "回归：§98 在附录内。")
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §98 不存在" % self.line_of("§98 在附录内"),
        )

    def test_missing_history_section_checks_whole_document(self):
        self.remove_section(HISTORY_HEADING)
        self.append("回归：§98 在无历史小节的文末。")
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §98 不存在" % self.line_of("§98 在无历史小节的文末"),
        )

    def test_numbered_second_level_heading_does_not_open_exemption(self):
        # `## 9.1` 是带编号的二级标题，不等于 `§9` 的历史小节。
        self.remove_section(HISTORY_HEADING)
        self.append("## 9.1 回归小节", "回归：§98 在 9.1 小节内。")
        result = self.run_checker()
        self.assert_reports(
            result,
            "[引用] L%d §98 不存在" % self.line_of("§98 在 9.1 小节内"),
        )

    # -- 其余消费者仍只用旧边界 ------------------------------------------
    def test_withdrawn_word_and_deprecated_tag_ignored_after_history_start(self):
        self.insert_after("## 10. 已定项", "回归：certain 与 A 档 只受旧边界约束。")
        self.assert_passes(self.run_checker())

    def test_withdrawn_word_and_deprecated_tag_reported_before_history_start(self):
        self.insert_after("## 8. 范围边界", "回归：certain 与 A 档 出现在历史小节之前。")
        result = self.run_checker()
        self.assert_reports(result, "[撤回词]", "[标签]")


if __name__ == "__main__":
    unittest.main()
"""指引契约的可核对面（2026-11-23 五轮，三轮审查后的收口）。

本文件只锁两件事——它们都是"指引/契约"而非新机制：

1. **报告状态行的位置约定必须与判定窗口同源**。判定只读报告开头 `STATUS_HEAD_CHARS`
   字符（自动发现与 lint 共用同一实现），而错误出口曾统一说"放在报告第一行"：两句话
   不是同一个契约，reviewer 照出口做会被另一个窗口放过/拒绝，来回一次就是整轮成本。
   这里断言窗口边界行为 + 出口文案里出现同一个数字，任何一边改动都会变红。
2. **"作决定"与"转录"是两件事**（设计稿 §1.2）。决定内容必须由人明确给出，模型可按
   该选择填写决定文件，但不得推测/补造/替人选择；`--draft` 骨架只是省掉猜字段。
   这里断言这条口径在判据位（设计稿）与 skill/草稿出口上都在，防止只改一处又漂回去。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PAYLOAD = REPO / "docs" / "workflows" / "wf" / "payload"
sys.path.insert(0, str(PAYLOAD / "lib"))

from wflib import review, tasks  # noqa: E402

DESIGN = (REPO / "docs" / "workflows" / "wf-framework-design.md").read_text(encoding="utf-8")
SKILL_REVIEW = (REPO / "docs" / "workflows" / "wf" / "skills" / "wf-review" / "SKILL.md").read_text(
    encoding="utf-8")
SKILL_CONTINUE = (REPO / "docs" / "workflows" / "wf" / "skills" / "wf-continue" / "SKILL.md").read_text(
    encoding="utf-8")


class StatusWindowTest(unittest.TestCase):
    def _report(self, prefix):
        return f"{prefix}<!-- wf-review-agent:v1 status=done -->\n正文\n"

    def test_marker_inside_window_is_read(self):
        prefix = "x" * (review.STATUS_HEAD_CHARS - len("<!-- wf-review-agent:v1 status=done -->"))
        self.assertEqual(review.report_status(self._report(prefix)), "done")

    def test_marker_past_window_is_not_read(self):
        prefix = "x" * (review.STATUS_HEAD_CHARS + 1)
        self.assertIsNone(review.report_status(self._report(prefix)))

    def test_exit_texts_quote_the_same_window(self):
        """出口文案必须说"开头前 N 字符"，不能再说"第一行"——否则契约有两份。

        断言落在**渲染后的出口字符串**上（源码里是 `{STATUS_HEAD_CHARS}` 占位，
        拿源码文本比数字会得到假绿/假红）。
        """
        window = str(review.STATUS_HEAD_CHARS)
        report = review.report_input_problems({"protocol": review.PROTOCOL},
                                              task={"id": "t1"},
                                              text="no status marker here",
                                              require_done=True)
        exits = [exit_ for entry in report["checks"].get("status-head") or []
                 for exit_ in entry.get("exits") or []]
        self.assertTrue(exits, "缺少状态行的报告必须给出出口")
        self.assertTrue(any(f"前 {window} 字符" in exit_ for exit_ in exits), exits)
        self.assertFalse(any("报告第一行" in exit_ for exit_ in exits), exits)
        self.assertIn(window, SKILL_REVIEW)


class DecisionTranscriptionTest(unittest.TestCase):
    def test_design_states_decision_vs_transcription(self):
        self.assertIn("作决定与转录是两个动作", DESIGN)
        self.assertIn("不得推测、补全或替人选择", DESIGN)

    def test_skill_keeps_the_boundary_at_the_writing_rule(self):
        self.assertIn("决定内容必须是人已明确给出的选择", SKILL_CONTINUE)
        self.assertIn("作决定与转录是两件事", SKILL_CONTINUE)

    def test_draft_exit_tells_the_model_not_to_guess(self):
        """草稿出口的实际文案（用户/模型看到的那一句）必须写明"按人的明确答复填写"。"""
        payload = tasks._decision_draft_result(
            None, "t-1", [{"choice": "TODO（批准|机械修订）"}], command="task-approve")
        next_text = str(payload.get("next") or "")
        self.assertIn("按人的明确答复填写", next_text)
        self.assertIn("不得推测或替人选择", next_text)


if __name__ == "__main__":
    unittest.main()
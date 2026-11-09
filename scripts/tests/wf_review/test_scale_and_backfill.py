"""P3/4.6 + §0.2 补写：规模事实托底与漏报补写状态。

防的失败：
- 4.6 的"这次改了多少"以前只靠 AI 自觉（v10 删掉了 200/800 这类拍出来的阈值）；
- 抽到"无对应判断"时没有恢复路径（要么死路，要么悄悄放过）——§0.2 要求记失败 + 补写两条。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "新项目开发工作流" / "payload" / "lib"))

from wflib import sampling, scale  # noqa: E402


class ScaleTest(unittest.TestCase):
    def test_relative_line_not_absolute_threshold(self):
        line = scale.describe({"available": True, "net": 480, "files": 6, "new_files": 3}, 620)
        self.assertFalse(line["exceeds_history"])
        self.assertIn("历史最大 620", line["line"])

    def test_exceeding_history_is_highlighted_not_blocked(self):
        described = scale.describe({"available": True, "net": 700, "files": 6, "new_files": 3}, 620)
        self.assertTrue(described["exceeds_history"])
        self.assertIn("超出历史最大值", described["line"])

    def test_unavailable_is_stated_not_guessed_as_zero(self):
        described = scale.describe({"available": False, "reason": "未开工"}, None)
        self.assertIsNone(described["exceeds_history"])
        self.assertIn("不可得", described["line"])

    def test_history_max_comes_from_records(self):
        self.assertEqual(scale.history_max([
            {"cumulative": {"confirmed_net": 620}},
            {"cumulative": {"confirmed_net": 100}},
            {"cumulative": {}}]), 620)
        self.assertIsNone(scale.history_max([]))

    def test_record_writes_the_confirmed_amount(self):
        task = {}
        payload = scale.record(task, {"net": 480, "files": 6, "added": 500, "deleted": 20, "base": "abc"})
        self.assertEqual(payload["confirmed_net"], 480)
        self.assertEqual(task["cumulative"]["base"], "abc")
        self.assertEqual(task["cumulative"]["by"], "human")


class BackfillTest(unittest.TestCase):
    PICKS = [{"class": "关闭", "event": "f1"}]

    def test_sampled_event_without_judgment_is_a_miss(self):
        status = sampling.backfill_status(self.PICKS, [])
        self.assertEqual(status["count"], 1)
        self.assertEqual(status["missing"][0]["event"], "f1")

    def test_judgment_referencing_the_event_is_not_a_miss(self):
        status = sampling.backfill_status(self.PICKS, [
            {"kind": "关闭", "decision": "已修", "basis": "v1", "evidence_refs": ["f:f1"]}])
        self.assertEqual(status["missing"], [])

    def test_two_backfill_entries_close_the_miss(self):
        status = sampling.backfill_status(self.PICKS, [
            {"kind": "漏报说明", "backfill": True, "basis": "抽样漏报：" + "x"},
            {"kind": "关闭", "backfill": True, "basis": "补：按 K4b 复核"}])
        self.assertEqual(len(status["backfilled"]), 1)

    def test_over_two_is_second_failure_not_auto_escalation(self):
        picks = [{"class": c, "event": f"e{i}"} for i, c in enumerate(["关闭", "归属", "扩面"])]
        status = sampling.backfill_status(picks, [])
        self.assertTrue(status["over_limit"])
        self.assertIn("由人裁", status["note"])

    def test_human_review_declaration_ends_strengthened_phase(self):
        history = sampling.history_from_tasks([
            {"sampling": {"results": [{"class": "关闭", "event": "f1", "failed": True}]}},
            {"sampling": {"reviewed_by_human": {"by": "human", "at": "t"}}}])
        self.assertFalse(history["关闭"]["strengthened"])
        self.assertTrue(history["关闭"]["strengthened_ended"])
        self.assertIn("强化抽样期已结束", sampling.report(history))


if __name__ == "__main__":
    unittest.main()

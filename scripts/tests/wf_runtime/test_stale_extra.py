"""A13：结论未绑定"判定时的导入集"——交付的是**事实侧**（`conclusion.stale_extra`）。

历史缺陷：判定之后再导入的报告不使旧 pass 失效，即使它会令重判变 fail——出现"重判会 fail、
直接归档却 pass"的分叉。⑥ 的裁定是只交付事实：`repair_scope.conclusion.stale_extra` 列出
**判定那一轮**里"判定之后新导入、未被结论引用"的报告 slot，供 AI 先读再决定是否重判；
强门禁（判定时导入集摘要 + C4 追加"导入集未变"）仅作未来选项，不在本仓实现。

本用例锁住事实侧的语义：同轮、未被引用、未判定时为空、他轮不算。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402


def reviews(imported, cited_slots=("s1",), round_no=1, verdict="pass"):
    return {"imported": list(imported),
            "result": {"verdict": verdict, "round": round_no,
                       "imported": [{"slot": slot, "report_digest": "sha256:x"}
                                    for slot in cited_slots]}}


ENTRIES = [
    {"round": 1, "slot": "s1", "report_path": "review/round-1/review-s1.md"},
    {"round": 1, "slot": "s2", "report_path": "review/round-1/review-s2.md"},
    {"round": 2, "slot": "s3", "report_path": "review/round-2/review-s3.md"},
]


class StaleExtraTest(unittest.TestCase):
    def test_reports_imported_after_the_conclusion_are_listed(self):
        facts = review._stale_extra(reviews(ENTRIES), reviews(ENTRIES)["result"])
        self.assertEqual(facts, [{"round": 1, "slot": "s2",
                                  "report_path": "review/round-1/review-s2.md"}])

    def test_cited_reports_are_not_listed(self):
        data = reviews(ENTRIES, cited_slots=("s1", "s2"))
        self.assertEqual(review._stale_extra(data, data["result"]), [])

    def test_without_a_conclusion_there_is_nothing_to_compare(self):
        data = reviews(ENTRIES, verdict=None)
        self.assertEqual(review._stale_extra(data, data["result"]), [])

    def test_other_rounds_are_not_counted(self):
        facts = review._stale_extra(reviews(ENTRIES), reviews(ENTRIES)["result"])
        self.assertEqual({item["round"] for item in facts}, {1})
        self.assertNotIn("s3", {item["slot"] for item in facts})

    def test_it_is_a_reported_fact_not_a_gate(self):
        """replay：即使存在 stale_extra，结论本身仍是原样（失效与否由 review_binding 现算）。"""
        data = reviews(ENTRIES)
        facts = review._stale_extra(data, data["result"])
        self.assertTrue(facts)
        self.assertEqual(data["result"]["verdict"], "pass")     # 事实不修改结论
        self.assertNotIn("binding", data["result"])             # 绑定是另一处的派生


if __name__ == "__main__":
    unittest.main()

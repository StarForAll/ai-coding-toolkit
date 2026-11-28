"""`WF_REVIEW_INVALID` 的出口分档（review_input_exits）必须按 anchor_stale token 分档。

2026-11-27 第三/四轮独立复审：此前该判定按 `problems[].reason` 的措辞反推，文案一改
就会静默回落到"补齐报告后重导"，把"报告已失去被审对象"当成可补的输入问题。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402


class ReviewInputExitsTest(unittest.TestCase):
    def test_anchor_stale_points_at_a_new_round(self):
        exits = review.review_input_exits(["anchor_stale"])
        self.assertIn("失去被审对象", exits[0])
        self.assertIn("review-launch", exits[0])
        self.assertNotIn("补齐报告", exits[0])

    def test_other_input_problems_still_name_a_new_round_first(self):
        """已导入槽位的摘要不可替换：非 anchor 分支首条也必须可执行（第八轮复审 F3）。"""
        exits = review.review_input_exits([])
        self.assertIn("review-launch", exits[0])
        self.assertTrue(any("补齐报告" in item for item in exits))



if __name__ == "__main__":
    unittest.main()

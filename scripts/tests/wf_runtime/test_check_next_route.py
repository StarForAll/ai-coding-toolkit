"""R4：Check pass 的下一跳按复杂度分流（复杂任务先审查，不再固定指向 finish）。"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402


class CheckNextHintTest(unittest.TestCase):
    def test_complex_task_routes_to_review_launch(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "pass"})
        self.assertIn("review-launch", hint)

    def test_light_task_routes_to_finish(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "light"}}, {"result": "pass"})
        self.assertIn("finish", hint)
        self.assertNotIn("review-launch", hint)

    def test_failed_check_routes_to_repair_loop(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "fail"})
        self.assertIn("wf-repair-loop", hint)

    def test_in_flight_round_survives_old_fail_verdict(self):
        """十四轮 b-1：旧锚点上的 fail 只是历史，不得把在途未判定轮挤成"重新发起"。"""
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [
                    {"round": 1, "anchor": {"check_anchor": "A"}},
                    {"round": 2, "anchor": {"check_anchor": "A"}},
                ],
                "rounds": [{"round": 1, "verdict": "fail"}],
                "result": {"verdict": "fail", "anchor": {"check_anchor": "A"}},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("第 2 轮审查仍在进行", hint)
        self.assertIn("继续这一轮", hint)
        self.assertNotIn("先 review-launch", hint)

    def test_in_flight_round_hinted_without_any_verdict(self):
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [],
                "result": {},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("第 1 轮审查仍在进行", hint)
        self.assertNotIn("先 review-launch", hint)

    def test_old_fail_without_open_round_still_suggests_launch(self):
        """全部轮次已判定（fail 留史）且无在途轮：仍指向发起新轮。"""
        task = {
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "B"}},
            "reviews": {
                "launches": [{"round": 1, "anchor": {"check_anchor": "A"}}],
                "rounds": [{"round": 1, "verdict": "fail"}],
                "result": {"verdict": "fail", "anchor": {"check_anchor": "A"}},
            },
        }
        hint = tasks.check_next_hint(task, {"result": "pass"})
        self.assertIn("review-launch", hint)

    def test_in_flight_round_with_bound_pass_mentions_finish(self):
        """第四组合（pass 绑定当前锚点 + 在途轮）：继续在途轮，并附 finish 提示。

        _binding 走 gates.review_binding(ctx, task)，用最小 ctx 桩 + 补丁固定其结论。
        """
        import types
        from unittest import mock

        stub = types.SimpleNamespace(root="/nonexistent", debug_threshold=lambda: 3)
        task = {
            "id": "t-bind",
            "plan": {"complexity": "complex"},
            "check": {"result": "pass", "anchor": {"check_anchor": "A"}},
            "reviews": {
                "launches": [
                    {"round": 1, "anchor": {"check_anchor": "A"}},
                    {"round": 2, "anchor": {"check_anchor": "A"}},
                ],
                "rounds": [{"round": 1, "verdict": "pass"}],
                "result": {"verdict": "pass", "anchor": {"check_anchor": "A"}},
            },
        }
        with mock.patch("wflib.gates.review_binding", return_value={"binding": True}):
            hint = tasks.check_next_hint(task, {"result": "pass"}, ctx=stub)
        self.assertIn("第 2 轮审查仍在进行", hint)
        self.assertIn("判定后即可请人 finish", hint)


if __name__ == "__main__":
    unittest.main()

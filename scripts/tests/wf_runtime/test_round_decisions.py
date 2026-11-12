"""A10：逐轮决策事实——`rounds[]` 承接「某轮是否已判 / 判成什么 / 回退不丢历史」。

历史缺陷（基线 8da2f23）：`reviews.result` 只留最新一轮，`attempts.outcome` 是尝试级汇总，
既没有逐轮记录、也没有"这一轮判过什么"的地方；显式重判旧轮会让 `result.round` 回退，
此前的判定事实就只剩一份汇总。⑥ 用 append-only 的 `rounds[]` 承接了这份事实
（v67 记为「A10 已由 rounds[] 承接」），本用例把四问锁住，防止退回单一 `result`。

「是否失效」按 v66 的裁定是**派生事实**（`check_validity` + `review_binding` + `exits_for`
的 C4），不写入 `rounds[]`——本文件只断言派生入口可用，不断言落盘字段。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402

BASE = {"id": "t1", "reviews": {
    "last_round": 2,
    "launches": [{"round": 1, "implementation_cli": "dsh", "slots": [{"slot": "s1"}]},
                 {"round": 2, "implementation_cli": "dsh", "slots": [{"slot": "s1"}]}],
    "attempts": [{"number": 1, "rework_ref": None, "round_ids": [1, 2], "outcome": "fail"}],
    "imported": [],
}}


def record(rounds=None, result=None):
    task = {"id": BASE["id"], "reviews": dict(BASE["reviews"])}
    if rounds is not None:
        task["reviews"]["rounds"] = rounds
    if result is not None:
        task["reviews"]["result"] = result
    return task


class RoundDecisionFactsTest(unittest.TestCase):
    def test_same_round_decided_twice_keeps_both_and_latest_wins(self):
        task = record(rounds=[
            {"round": 1, "verdict": "fail", "check_id": "c1", "decided_at": "2026-11-11T10:00:00Z"},
            {"round": 1, "verdict": "pass", "check_id": "c1", "decided_at": "2026-11-11T12:00:00Z"},
        ])
        self.assertEqual(len(review.decision_rounds(task)), 2)          # 两条都在
        self.assertEqual(review.latest_decision(task, 1)["verdict"], "pass")   # 同轮取最新

    def test_redeciding_an_older_round_does_not_erase_history(self):
        task = record(rounds=[
            {"round": 1, "verdict": "fail", "check_id": "c1", "decided_at": "2026-11-11T10:00:00Z"},
            {"round": 2, "verdict": "pass", "check_id": "c1", "decided_at": "2026-11-11T11:00:00Z"},
            {"round": 1, "verdict": "pass", "check_id": "c1", "decided_at": "2026-11-11T12:00:00Z"},
        ], result={"verdict": "pass", "round": 1, "check_id": "c1"})
        self.assertEqual(task["reviews"]["result"]["round"], 1)        # result 回退了……
        rounds = {(item["round"], item["decided_at"][-9:-1]): item["verdict"]
                  for item in review.decision_rounds(task)}
        self.assertEqual(rounds, {(1, "10:00:00"): "fail",
                                  (2, "11:00:00"): "pass",
                                  (1, "12:00:00"): "pass"})           # ……但历史一条不少
        self.assertEqual(review.latest_decision(task, 1)["verdict"], "pass")
        self.assertEqual(review.latest_decision(task, 2)["verdict"], "pass")

    def test_legacy_record_without_rounds_is_inferred_and_marked(self):
        task = record(result={"verdict": "pass", "round": 3, "check_id": "c1"})
        rounds = review.decision_rounds(task)
        self.assertEqual(len(rounds), 1)
        self.assertEqual((rounds[0]["round"], rounds[0]["verdict"]), (3, "pass"))
        self.assertTrue(rounds[0]["inferred"])            # 推断出来的，不冒充历史
        self.assertIsNone(rounds[0]["decided_at"])

    def test_no_decision_at_all_has_no_rounds(self):
        self.assertEqual(review.decision_rounds(record()), [])


if __name__ == "__main__":
    unittest.main()

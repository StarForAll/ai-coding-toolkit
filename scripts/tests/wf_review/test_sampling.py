"""P3/§0.2：试点期判断抽样——候选来自骨架、选样可复算、预算固定 2 条、首任务 1 条。

防的失败（v42 §0.2）：① AI 通过增减 judgments 影响抽中哪条（可操纵）；② 某个类出过错后
"一路点对"再没人看（强化期形同虚设）；③ 几条局部失误堆成一轮大量人工复核（预算叠加）。
这里锁的是这三条机制性质，不是判断质量本身。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "新项目开发工作流" / "payload" / "lib"))

from wflib import sampling  # noqa: E402


def pool(**extra):
    base = {name: [] for name in sampling.EVENT_SOURCES}
    base.update({"归属": ["p:a", "p:b", "p:c"], "关闭": ["f1", "f2"]})
    base.update(extra)
    return base


class SelectionTest(unittest.TestCase):
    def test_same_seed_and_pool_gives_same_picks(self):
        first = sampling.select("seed-x", pool())
        second = sampling.select("seed-x", pool())
        self.assertEqual(first["picks"], second["picks"])

    def test_budget_is_two_and_does_not_stack(self):
        history = {"关闭": {"strengthened": True, "failures": 1},
                   "归属": {"strengthened": True, "failures": 1}}
        result = sampling.select("seed-x", pool(), history, open_blocking=True)
        self.assertEqual(result["budget"], 2)
        self.assertEqual(len(result["picks"]), 2)

    def test_first_task_takes_one_pick_close_first(self):
        result = sampling.select("seed-x", pool(), first_task=True)
        self.assertEqual(result["budget"], 1)
        self.assertEqual(len(result["picks"]), 1)
        self.assertEqual(result["picks"][0]["class"], "关闭")

    def test_first_task_without_close_falls_back_to_ownership(self):
        result = sampling.select("seed-x", pool(关闭=[]), first_task=True)
        self.assertEqual(result["picks"][0]["class"], "归属")

    def test_open_blocking_puts_close_first(self):
        result = sampling.select("seed-x", pool(标准变更=["s1"]), open_blocking=True)
        self.assertEqual(result["picks"][0]["class"], "关闭")

    def test_strengthened_obligation_takes_the_second_pick(self):
        history = {"关闭": {"strengthened": True, "failures": 1}}
        result = sampling.select("seed-x", pool(标准变更=["s1"]), history)
        classes = [item["class"] for item in result["picks"]]
        self.assertEqual(classes[0], "关闭")          # 强化期优先级最高
        self.assertIn("关闭", classes)

    def test_obligation_with_single_event_is_deferred_not_duplicated(self):
        history = {"关闭": {"strengthened": True, "failures": 1}}
        result = sampling.select("seed-x", pool(关闭=["f1"], 归属=[]), history, open_blocking=True)
        second = result["picks"][1]
        self.assertEqual(second["class"], "关闭")
        self.assertIsNone(second["event"])
        self.assertIn("顺延", second["rule"])

    def test_uncovered_classes_are_named(self):
        result = sampling.select("seed-x", pool())
        self.assertIn("未核实", result["uncovered"])
        self.assertNotIn("关闭", result["uncovered"])


class PoolFromSkeletonTest(unittest.TestCase):
    def test_events_come_from_skeleton_not_from_judgments(self):
        skeleton = {"changed_paths": ["p:a"], "closures": [{"finding_id": "f1"}],
                    "drift_diffs": [], "fix_scope": [], "standard_changes": [],
                    "requirement_gap_findings": [], "unverified": [], "cumulative": None}
        before = sampling.events_of(skeleton)
        skeleton["judgments"] = [{"kind": "关闭", "decision": "看起来很稳"}]   # AI 的说法不进池
        self.assertEqual(before, sampling.events_of(skeleton))
        self.assertEqual(before["归属"], ["p:a"])
        self.assertEqual(before["关闭"], ["f1"])

    def test_freeze_then_select_is_reproducible(self):
        task = {"id": "t1"}
        skeleton = {"changed_paths": ["p:a"], "closures": ["f1"], "drift_diffs": [], "fix_scope": [],
                    "standard_changes": [], "requirement_gap_findings": [], "unverified": [],
                    "cumulative": None}
        frozen = sampling.freeze(task, skeleton, seed="fixed-seed")
        first = sampling.select_for(task)
        task["judgments"] = [{"kind": "归属", "decision": "事后补的"}]   # 冻结后再改判断
        second = sampling.select_for(task)
        self.assertEqual(frozen["seed"], "fixed-seed")
        self.assertEqual(first["picks"], second["picks"])


class HistoryTest(unittest.TestCase):
    def test_first_failure_enters_strengthened_phase(self):
        history = sampling.history_from_tasks([
            {"sampling": {"results": [{"class": "关闭", "event": "f1", "failed": True}]}}])
        self.assertTrue(history["关闭"]["strengthened"])
        self.assertEqual(history["关闭"]["failures"], 1)

    def test_report_flags_insufficient_samples(self):
        text_value = sampling.report(sampling.history_from_tasks([]))
        self.assertIn("门槛未激活", text_value)
        self.assertIn("未命中不等于没问题", text_value)


if __name__ == "__main__":
    unittest.main()

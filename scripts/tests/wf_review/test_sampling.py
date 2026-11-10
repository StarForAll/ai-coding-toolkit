"""P3/§0.2：试点期判断抽样——候选来自骨架、选样可复算、预算固定 2 条、首任务 1 条。

防的失败（v42 §0.2）：① AI 通过增减 judgments 影响抽中哪条（可操纵）；② 某个类出过错后
"一路点对"再没人看（强化期形同虚设）；③ 几条局部失误堆成一轮大量人工复核（预算叠加）。
这里锁的是这三条机制性质，不是判断质量本身。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

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

    def test_strengthened_obligation_takes_a_slot_without_outranking_tier(self):
        """强化期是**同级加权**，不凌驾 tier（v42 §0.2：强化类强制占 1 条，不是占满）。

        旧断言要求"关闭"必须在第 1 条，实际把 strengthened 放在了 tier 之上——
        与同文件 `test_open_blocking_puts_close_first` 的伤口优先例外互相矛盾。
        """
        history = {"关闭": {"strengthened": True, "failures": 1}}
        result = sampling.select("seed-x", pool(关闭=["f1"], 标准变更=["s1"]), history)
        classes = [item["class"] for item in result["picks"]]
        self.assertIn("关闭", classes, "强化义务必须占一条")
        self.assertEqual(classes[0], "标准变更", "tier 优于同级加权")

    def test_obligation_with_single_event_defers_without_burning_the_slot(self):
        """只有一个事件时顺延，但**第 2 条仍要抽别的类**，不能空烧预算。"""
        history = {"关闭": {"strengthened": True, "failures": 1}}
        result = sampling.select("seed-x", pool(关闭=["f1"], 标准变更=["s1"]), history,
                                 open_blocking=True)
        first, second = result["picks"][0], result["picks"][1]
        self.assertEqual(first["class"], "关闭")          # 伤口优先
        self.assertIsNotNone(second["event"], "顺延不等于空烧预算")
        self.assertNotEqual(second["class"], "关闭")      # 该类只有那一个事件，已抽走

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
        # 事件 id 现在统一带前缀（`f:f1`）：旧的裸串无法被 judgment 引用，是假漏报的来源
        self.assertEqual(before["关闭"], ["f:f1"])

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


class EventIdSpaceTest(unittest.TestCase):
    """审查 A1：事件池与 judgment 引用必须共用同一个 id 空间。

    历史缺陷：扩面/标准变更是 dict，`str(item)` 后成为整段文本；缺口类映射到一个
    **没有任何生产者**的骨架键；未核实给的是裸验收 id。这些事件被抽中后必然报"漏报失败"，
    而 AI 补写又会被 `validate` 拒绝——框架自己制造假失败。
    """

    SKELETON = {
        "changed_paths": ["p:src/a.py"],
        "closures": [{"finding_id": "f1", "cited_verification": ["v:1"]}],
        "drift_diffs": [{"id": "d:1", "where": "acceptance"}],
        "fix_scope": [{"judgment_id": "j1", "paths": ["new.py"], "decision": "扩面", "basis": "b"}],
        "standard_changes": [{"judgment_id": "j2", "decision": "改标准", "basis": "b"}],
        "requirement_gap_findings": [{"gap_id": "regression", "axis": "regression"}],
        "unverified": [{"acceptance_id": "a1"}],
        "cumulative": {"line": "净增 3 行", "net": 3},
    }

    def test_every_class_yields_a_referenceable_id(self):
        from wflib import judgments, sampling

        events = sampling.events_of(self.SKELETON)
        known = judgments.ref_ids(self.SKELETON)
        for cls, items in events.items():
            for item in items:
                self.assertNotIn("{", item, f"{cls} 的事件不能是 dict 的字符串形式：{item}")
                self.assertIn(item, known, f"{cls} 的事件 {item} 必须可被 judgment 引用")

    def test_picked_event_can_be_backfilled_legally(self):
        """被抽中的事件，AI 能用合法 judgment 引用它（不再必然判漏报失败）。"""
        from wflib import judgments, sampling

        events = sampling.events_of(self.SKELETON)
        picks = [{"class": cls, "event": events[cls][0]}
                 for cls in ("扩面", "标准变更", "缺口", "未核实", "规模") if events.get(cls)]
        for pick in picks:
            entry = {"kind": pick["class"], "decision": "补写", "basis": "依据",
                     "outcome": "applied", "evidence_refs": [pick["event"]]}
            problems = judgments.validate(entry, self.SKELETON)
            self.assertEqual([p for p in problems if "evidence_ref" in p.get("reason", "")], [],
                             f"{pick['class']} 的合法引用被拒：{problems}")
            self.assertIsNotNone(sampling.judgment_for(pick, [entry]),
                                 f"{pick['class']} 的补写没被认出")

"""顺序边：任务步骤之间的前置由「上一未略过 task 步骤」决定（机制稿 §7.3、§5.8）。

实现里 `advance` 把 `task_map[step].predecessors` 写进新任务的 `prerequisites`；
这里核**前置的推导**（边的值从哪来），端到端的第二次建任务需要完整任务生命周期，
其首任务无前置已由 `repro/run-advance-creates-task.py` 覆盖。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

DOC = {"steps": [
    {"id": "one", "type": "task"},
    {"id": "ask", "type": "human", "required": True},
    {"id": "two", "type": "task"},
]}

DOC_SKIPPED = {"steps": [
    {"id": "one", "type": "task"},
    {"id": "ask", "type": "human", "required": False},
    {"id": "two", "type": "task"},
]}


class OrderEdgeTest(unittest.TestCase):
    def test_previous_task_step_skips_human_steps(self):
        self.assertEqual(runs._previous_task_step(DOC, "two")["id"], "one",
                         "human 步骤不生成任务边（机制稿 §7.3）")

    def test_declared_skipped_step_is_passed_over(self):
        creation = {"steps": {"one": "skipped", "ask": "applicable", "two": "applicable"}}
        applicability = runs._applicability(creation, DOC_SKIPPED)
        self.assertIsNone(runs._previous_task_step(DOC_SKIPPED, "two", applicability),
                          "声明略过的任务步骤不构成前置")

    def test_recorded_skipped_step_is_passed_over(self):
        creation = {"steps": {"one": "applicable", "ask": "applicable", "two": "applicable"}}
        applicability = runs._applicability(creation, DOC_SKIPPED)
        step_results = {"one": {"kind": "skipped"}}
        self.assertIsNone(runs._previous_task_step(DOC_SKIPPED, "two", applicability, step_results),
                          "实例里已记 skipped 的任务步骤不构成前置")

    def test_third_task_links_to_nearest_unskipped(self):
        doc = {"steps": [{"id": "one", "type": "task"}, {"id": "two", "type": "task"},
                         {"id": "three", "type": "task"}]}
        creation = {"steps": {"one": "applicable", "two": "skipped", "three": "applicable"}}
        applicability = runs._applicability(creation, doc)
        self.assertEqual(runs._previous_task_step(doc, "three", applicability)["id"], "one",
                         "跨过被略过的 two，直接引用 one")

    def test_first_task_step_has_no_predecessor(self):
        self.assertIsNone(runs._previous_task_step(DOC, "one"))


if __name__ == "__main__":
    unittest.main()

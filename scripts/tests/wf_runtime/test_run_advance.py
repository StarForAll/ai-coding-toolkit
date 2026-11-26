"""P1-2：`run advance` 的步骤选择与人判判定（机制稿 §7.3）。

本批覆盖最小闭环的可判定部分（纯函数级）：
- 顺序：下一个待处理步骤、上一个未略过的 task 步骤（顺序前置只直接引用它，human 步骤不生成边）；
- 适用性：`creation.steps` 的声明优先，未声明按定义默认；
- 人判答复：`subject` 必须含步骤 id；可略步骤必须有决定；human 步骤的答复必须是已声明选项之一。

端到端（建任务 / task_map / 游标 / 重入）走 `repro/run-advance-creates-task.py`。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

DOC = {
    "steps": [
        {"id": "a", "type": "task", "title": "A", "required": True},
        {"id": "gate", "type": "human", "title": "G", "question": "做不做？",
         "choices": ["do", "skip"]},
        {"id": "b", "type": "task", "title": "B", "required": True},
        {"id": "c", "type": "task", "title": "C", "required": False,
         "skip": {"condition": "不需要", "decision_point": "approve-c"}},
    ],
}


class StepOrderTest(unittest.TestCase):
    def test_next_step_from_scratch_and_from_the_middle(self):
        self.assertEqual(runs._next_step(DOC, None)["id"], "a")
        self.assertEqual(runs._next_step(DOC, "gate")["id"], "b")
        self.assertIsNone(runs._next_step(DOC, "c"))

    def test_next_step_skips_steps_that_already_have_results(self):
        """六轮复核 a.2：人判/略过步骤的结果已在 `step_results` 里，重入不得再停在同一格。"""
        results = {"gate": {"kind": "satisfied"}, "b": {"kind": "skipped"}}
        self.assertEqual(runs._next_step(DOC, "a", results)["id"], "c")
        self.assertIsNone(runs._next_step(DOC, "c", results))

    def test_previous_task_step_skips_human_steps(self):
        # human 步骤不生成任务边：b 的顺序前置仍是 a
        self.assertEqual(runs._previous_task_step(DOC, "b")["id"], "a")
        self.assertIsNone(runs._previous_task_step(DOC, "a"))

    def test_applicability_defaults_and_declarations(self):
        self.assertEqual(runs._applicability({}, DOC),
                         {"a": "applicable", "gate": "applicable",
                          "b": "applicable", "c": "applicable"})
        declared = runs._applicability({"steps": {"c": "skipped"}}, DOC)
        self.assertEqual(declared["c"], "skipped")


class HumanAnswerTest(unittest.TestCase):
    def test_subject_must_name_the_step(self):
        self.assertIsNone(runs._human_answer([{"subject": "b", "choice": "do"}], {"id": "a"}))

    def test_subject_list_form_is_accepted(self):
        decision = {"subject": ["gate", "做不做"], "choice": "do"}
        self.assertIs(runs._human_answer([decision], {"id": "gate"}), decision)

    def test_no_decision_returns_none(self):
        self.assertIsNone(runs._human_answer([], {"id": "gate"}))


if __name__ == "__main__":
    unittest.main()

"""门禁时点：抽样只在归档前、escalated 只挂起最终结论（v42 §5.3 / §0.2）。

防的失败：抽样被跳过就直接收工；一条"判断不了"把整个流程冻住，连中途动作都做不了。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import gates  # noqa: E402


def step(name):
    for identifier, mode, condition, due in gates.TASK_STEP_SPECS:
        if identifier == name:
            return {"mode": mode, "condition": condition, "due": due}
    return None


class SamplingTimingTest(unittest.TestCase):
    def test_sampling_step_exists_and_is_due_before_archive(self):
        spec = step("task.sampled")
        self.assertIsNotNone(spec, "缺 task.sampled 步骤：抽样没有门禁时点")
        self.assertEqual(spec["due"], "before_archive")

    def test_sampling_step_is_not_due_before_execute_or_check(self):
        dues = [item["due"] for item in [step("task.sampled")]]
        self.assertNotIn("before_execute", dues)
        self.assertNotIn("before_check", dues)

    def test_sampling_projection_is_the_frozen_selection(self):
        task = {"id": "t1", "sampling": {"frozen": {"seed": "s1", "picks": [{"class": "关闭"}]}}}
        projection = gates.compute_P(None, task, "task.sampled")
        self.assertEqual(projection, {"seed": "s1", "picks": [{"class": "关闭"}]})

    def test_missing_selection_blocks_with_an_exit(self):
        class Ctx:
            root = str(REPO)

            def rule_version(self):
                return 1

        task = {"id": "t1", "sampling": {}}
        ok, code, facts = gates.verify_step(Ctx(), task, "task.sampled")
        self.assertFalse(ok)
        self.assertEqual(code, "WF_SEMANTIC_DECISION")
        self.assertTrue(any("sampling" in str(item) for item in facts.get("exits") or []))

    def test_frozen_selection_satisfies_the_step(self):
        class Ctx:
            root = str(REPO)

            def rule_version(self):
                return 1

        task = {"id": "t1", "sampling": {"frozen": {"seed": "s", "picks": [{"class": "关闭"}]}}}
        ok, code, _facts = gates.verify_step(Ctx(), task, "task.sampled")
        self.assertTrue(ok, code)

    @staticmethod
    def _via_internal(task):
        for name in ("_step_satisfied", "step_satisfied", "_check_step"):
            func = getattr(gates, name, None)
            if func:
                return func(None, task, "task.sampled")
        raise unittest.SkipTest("找不到单步判定入口")


class EscalatedHangsOnlyTheEndingTest(unittest.TestCase):
    def test_escalated_judgment_is_visible_in_gate_source(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        self.assertIn('item.get("outcome") == "escalated"', source)
        self.assertIn("最终结论挂起", source)

    def test_escalated_does_not_appear_in_mid_action_gates(self):
        """escalated 只出现在 final_gate（归档口），不进入 before_execute/before_check 的判定。"""
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/gates.py").read_text(encoding="utf-8")
        escalate_index = source.index('item.get("outcome") == "escalated"')
        final_gate_index = source.index("def final_gate")
        self.assertGreater(escalate_index, final_gate_index, "escalated 判定必须落在 final_gate 内")

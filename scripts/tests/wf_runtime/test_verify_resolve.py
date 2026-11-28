"""`verify resolve` 的落档边界与 Finish 出口（2026-11-28 外审 A1-2）。

区分力：
- 不存在的验收 id / 已 passed / failed 不能收窄；
- 成功处置只写 `unverified_resolutions`，不改变当前 Check；
- Check 不是 pass 时，Finish 门禁仍给出 pending required 的可执行出口。
"""

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import gates, projection  # noqa: E402


def _task(conclusion="pending"):
    return {
        "id": "t1",
        "plan": {"acceptance": [{"id": "a1", "required": True}]},
        "check": {"id": "c1", "result": "fail",
                  "acceptance_results": [{"acceptance_id": "a1", "conclusion": conclusion}]},
    }


class VerifyResolveTest(unittest.TestCase):
    def _resolve(self, task, acceptance_id="a1", kind="narrow"):
        return projection.resolve(
            task, acceptance_id, kind=kind, evidence="证据",
            reason="无法在本机验证", impact="影响面", compensation="补偿")

    def test_unknown_acceptance_id_is_rejected(self):
        task = _task()
        record, problems = self._resolve(task, "a-does-not-exist")
        self.assertIsNone(record)
        self.assertIn("不在当前批准", problems[0]["reason"])

    def test_passed_acceptance_is_not_narrowable(self):
        task = _task("passed")
        record, problems = self._resolve(task)
        self.assertIsNone(record)
        self.assertIn("已 passed", problems[0]["reason"])

    def test_failed_acceptance_is_not_narrowable(self):
        task = _task("failed")
        record, problems = self._resolve(task)
        self.assertIsNone(record)
        self.assertIn("failed 是已核实的缺陷", problems[0]["reason"])
        self.assertTrue(problems[0]["exits"])

    def test_pending_narrow_records_without_changing_check(self):
        task = _task("pending")
        before = copy.deepcopy(task["check"])
        record, problems = self._resolve(task)
        self.assertEqual(problems, [])
        self.assertEqual(record["kind"], "narrow")
        self.assertEqual(task["unverified_resolutions"]["a1"]["reason"], "无法在本机验证")
        self.assertEqual(task["check"], before)

    def test_plan_item_without_check_result_is_not_narrowable(self):
        task = _task("pending")
        task["check"]["acceptance_results"] = [
            {"acceptance_id": "a2", "conclusion": "pending"}]
        record, problems = self._resolve(task)
        self.assertIsNone(record)
        self.assertIn("没有该验收项结果", problems[0]["reason"])
        self.assertNotIn("unverified_resolutions", task)

    def test_inspection_records_evidence_without_changing_check(self):
        task = _task("failed")
        before = copy.deepcopy(task["check"])
        record, problems = projection.resolve(
            task, "a1", kind="inspection", evidence="人工运行确认")
        self.assertEqual(problems, [])
        self.assertEqual(record["kind"], "inspection")
        self.assertEqual(task["check"], before)


class FinishGateExitTest(unittest.TestCase):
    def test_check_failure_with_pending_required_has_executable_exits(self):
        task = {"id": "t1", "check": {"id": "c1", "result": "fail"}}
        ctx = SimpleNamespace(rule_version=lambda: "sha256:" + "0" * 64)
        with mock.patch("wflib.projection.required_unverified",
                        return_value=[{"acceptance_id": "a1", "conclusion": "pending"}]):
            ok, code, facts = gates.final_gate_nonstep(ctx, task)
        self.assertFalse(ok)
        self.assertEqual(code, "WF_CHECK_FAILED")
        exits = facts.get("exits") or []
        self.assertTrue(any("task-replan" in item for item in exits))
        self.assertTrue(any("异常归档" in item for item in exits))


if __name__ == "__main__":
    unittest.main()
"""步骤契约（十轮收敛项）：定义声明 → 任务记录 → Check 消费，以及动作结果的决定回写。"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, runs  # noqa: E402

STEP = {
    "id": "build", "type": "task", "title": "实现",
    "actions": [{"id": "write", "text": "写实现", "required": True, "skip": None, "human_points": []},
                {"id": "polish", "text": "可选打磨", "required": False, "skip": None, "human_points": []}],
    "human_points": [{"id": "confirm", "question": "接受吗？", "choices": ["yes", "no"]}],
    "verifications": [{"id": "v1", "source": "current_plan", "consume_at": "check"}],
}


class _Ctx:
    def __init__(self, root="."):
        self.root = root


def _task_with_contract():
    contract = runs.step_contract({"steps": [STEP]}, STEP, run_id="r1",
                                  run={"definition": {"digest": "sha256:" + "a" * 64}},
                                  workflow_id="wf-demo")
    return {"id": "t1", "plan": {"verifications": [{"id": "v1"}]}, "execution": contract}


class StepContractProducerTest(unittest.TestCase):
    def test_contract_shape(self):
        task = _task_with_contract()
        execution = task["execution"]
        self.assertEqual(execution["step"]["workflow_id"], "wf-demo")
        self.assertEqual(execution["step"]["step_id"], "build")
        self.assertEqual([item["result"] for item in execution["actions"]], ["pending", "pending"])
        self.assertEqual(execution["human_points"][0]["id"], "confirm")
        self.assertEqual(execution["verifications"][0]["id"], "v1")
        self.assertEqual(execution["verification_runs"], [])


class StepContractCheckTest(unittest.TestCase):
    def test_pending_required_action_blocks(self):
        task = _task_with_contract()
        contract = check.check_step_contract(_Ctx(), task, task["plan"],
                                             [{"subject": "confirm", "choice": "yes"}])
        kinds = [item["kind"] for item in contract["problems"]]
        self.assertIn("pending_actions", kinds)
        self.assertTrue(contract["exits"])

    def test_done_decision_clears_the_action(self):
        task = _task_with_contract()
        contract = check.check_step_contract(_Ctx(), task, task["plan"], [
            {"subject": "write", "choice": "done", "reason": "已实现"},
            {"subject": "confirm", "choice": "yes"},
        ])
        self.assertEqual(contract["problems"], [])
        check.apply_action_results(task, contract)
        results = {item["id"]: item["result"] for item in task["execution"]["actions"]}
        self.assertEqual(results, {"write": "done", "polish": "pending"})
        self.assertEqual(task["execution"]["actions"][0]["result_decision"]["why"], "已实现")

    def test_missing_human_point_blocks(self):
        task = _task_with_contract()
        contract = check.check_step_contract(_Ctx(), task, task["plan"], [
            {"subject": "write", "choice": "done"},
        ])
        self.assertIn("missing_human_points", [item["kind"] for item in contract["problems"]])

    def test_declared_verification_must_be_in_plan(self):
        task = _task_with_contract()
        task["plan"]["verifications"] = []
        contract = check.check_step_contract(_Ctx(), task, task["plan"], [
            {"subject": "write", "choice": "done"}, {"subject": "confirm", "choice": "yes"},
        ])
        self.assertIn("declared_verification_not_in_plan",
                      [item["kind"] for item in contract["problems"]])

    def test_waived_action_needs_registered_choice(self):
        task = _task_with_contract()
        contract = check.check_step_contract(_Ctx(), task, task["plan"], [
            {"subject": "write", "choice": "maybe"}, {"subject": "confirm", "choice": "yes"},
        ])
        self.assertIn("pending_actions", [item["kind"] for item in contract["problems"]])

    def test_plain_task_has_no_gate(self):
        contract = check.check_step_contract(_Ctx(), {"id": "t"}, {}, [])
        self.assertEqual(contract["problems"], [])


if __name__ == "__main__":
    unittest.main()

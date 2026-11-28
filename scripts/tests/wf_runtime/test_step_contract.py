"""步骤契约（十轮收敛项）：定义声明 → 任务记录 → Check 消费，以及动作结果的决定回写。

区分力（2026-11-28 外审 A1-1）：
- required 且无 skip 声明的动作不得用 waived 结案；
- 步骤级/动作级人判点必须按声明选项答复；
- 验证声明的 consume_at / stored_in.verification_id 必须对齐已批准 plan；
- 旧契约无 stored_in 时按 legacy 消费，不阻断。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, runs  # noqa: E402

STEP = {
    "id": "build", "type": "task", "title": "实现",
    "actions": [
        {"id": "write", "text": "写实现", "required": True, "skip": None,
         "human_points": [{"id": "approve-write", "question": "可以写吗？",
                           "choices": ["yes", "no"]}]},
        {"id": "polish", "text": "可选打磨", "required": False, "skip": None,
         "human_points": []},
    ],
    "human_points": [{"id": "confirm", "question": "接受吗？", "choices": ["yes", "no"]}],
    "verifications": [{"id": "v1", "source": "current_plan", "consume_at": "check",
                       "established_by": {"kind": "current_task"},
                       "stored_in": {"kind": "task_plan", "verification_id": "v1"}}],
}

PLAN = {"verifications": [{"id": "v1", "consume_at": "check"}]}

DONE = [
    {"subject": "write", "choice": "done", "reason": "已实现"},
    {"subject": "approve-write", "choice": "yes"},
    {"subject": "confirm", "choice": "yes"},
]


class _Ctx:
    def __init__(self, root="."):
        self.root = root


def _task_with_contract():
    contract = runs.step_contract({"steps": [STEP]}, STEP, run_id="r1",
                                  run={"definition": {"digest": "sha256:" + "a" * 64}},
                                  workflow_id="wf-demo")
    return {"id": "t1", "plan": dict(PLAN), "execution": contract}


def _kinds(contract):
    return [item["kind"] for item in contract["problems"]]


class StepContractProducerTest(unittest.TestCase):
    def test_contract_shape(self):
        task = _task_with_contract()
        execution = task["execution"]
        self.assertEqual(execution["step"]["workflow_id"], "wf-demo")
        self.assertEqual(execution["step"]["step_id"], "build")
        self.assertEqual([item["result"] for item in execution["actions"]], ["pending", "pending"])
        self.assertEqual(execution["human_points"][0]["id"], "confirm")
        verification = execution["verifications"][0]
        self.assertEqual(verification["id"], "v1")
        self.assertEqual(verification["consume_at"], "check")
        self.assertEqual(verification["stored_in"]["verification_id"], "v1")
        self.assertEqual(verification["established_by"]["kind"], "current_task")
        self.assertEqual(execution["verification_runs"], [])


class StepContractCheckTest(unittest.TestCase):
    def _check(self, decisions, plan=None):
        task = _task_with_contract()
        return task, check.check_step_contract(_Ctx(), task, plan or task["plan"], decisions)

    def test_pending_required_action_blocks(self):
        task, contract = self._check([])
        self.assertIn("pending_actions", _kinds(contract))
        self.assertTrue(contract["exits"])

    def test_done_decision_clears_the_action(self):
        task, contract = self._check(DONE)
        self.assertEqual(contract["problems"], [])
        check.apply_action_results(task, contract)
        results = {item["id"]: item["result"] for item in task["execution"]["actions"]}
        self.assertEqual(results, {"write": "done", "polish": "pending"})
        self.assertEqual(task["execution"]["actions"][0]["result_decision"]["why"], "已实现")

    def test_missing_human_point_blocks(self):
        task, contract = self._check([{"subject": "write", "choice": "done"}])
        self.assertIn("missing_human_points", _kinds(contract))

    def test_declared_verification_must_be_in_plan(self):
        task, contract = self._check(DONE, plan={"verifications": []})
        self.assertIn("declared_verification_not_in_plan", _kinds(contract))

    def test_waived_action_needs_registered_choice(self):
        task, contract = self._check([
            {"subject": "write", "choice": "maybe"},
            {"subject": "approve-write", "choice": "yes"},
            {"subject": "confirm", "choice": "yes"},
        ])
        self.assertIn("pending_actions", _kinds(contract))

    def test_waived_required_action_without_skip_blocks(self):
        task, contract = self._check([
            {"subject": "write", "choice": "waived", "reason": "不想做"},
            {"subject": "approve-write", "choice": "yes"},
            {"subject": "confirm", "choice": "yes"},
        ])
        actions = contract["problems"][0]["actions"]
        self.assertEqual(actions[0]["reason"], "waived_requires_skip_declaration")

    def test_waived_optional_action_without_skip_is_allowed(self):
        task, contract = self._check(DONE + [{"subject": "polish", "choice": "waived"}])
        self.assertEqual(contract["problems"], [])
        results = {item["id"]: item["result"] for item in contract["applied"]}
        self.assertEqual(results["polish"], "waived")

    def test_human_point_choice_must_be_declared(self):
        task, contract = self._check([
            {"subject": "write", "choice": "done"},
            {"subject": "approve-write", "choice": "yes"},
            {"subject": "confirm", "choice": "maybe"},
        ])
        points = contract["problems"][0]["points"]
        self.assertIn("choice not in declared choices", [item["reason"] for item in points])

    def test_action_human_point_must_be_answered(self):
        task, contract = self._check([
            {"subject": "write", "choice": "done"},
            {"subject": "confirm", "choice": "yes"},
        ])
        points = contract["problems"][0]["points"]
        self.assertIn("approve-write", [item["id"] for item in points])
        self.assertIn("no decision", [item["reason"] for item in points])

    def test_verification_consume_at_must_match_plan(self):
        task, contract = self._check(DONE, plan={"verifications": [{"id": "v1", "consume_at": "finish"}]})
        self.assertEqual(contract["problems"][0]["kind"], "declared_verification_not_in_plan")
        self.assertIn("consume_at differs", contract["problems"][0]["verifications"][0]["reason"])

    def test_stored_in_verification_id_must_hit_plan(self):
        task = _task_with_contract()
        task["execution"]["verifications"][0]["stored_in"]["verification_id"] = "other"
        contract = check.check_step_contract(_Ctx(), task, task["plan"], DONE)
        self.assertIn("stored_in.verification_id is not in the approved plan",
                      contract["problems"][0]["verifications"][0]["reason"])

    def test_declaration_id_may_differ_from_plan_id(self):
        task = _task_with_contract()
        task["execution"]["verifications"][0]["id"] = "local-v1"
        task["execution"]["verifications"][0]["stored_in"]["verification_id"] = "v1"
        contract = check.check_step_contract(_Ctx(), task, task["plan"], DONE)
        self.assertEqual(contract["problems"], [])
        self.assertEqual(contract["legacy_verifications"], [])

    def test_waived_optional_action_skips_its_human_points(self):
        task = _task_with_contract()
        task["execution"]["actions"][1]["human_points"] = [
            {"id": "polish-ok", "question": "打磨确认？", "choices": ["yes", "no"]}]
        contract = check.check_step_contract(
            _Ctx(), task, task["plan"], DONE + [{"subject": "polish", "choice": "waived"}])
        self.assertEqual(contract["problems"], [])
        self.assertNotIn("polish-ok", contract["human_points"])

    def test_project_file_must_exist(self):
        task = _task_with_contract()
        task["execution"]["verifications"][0] = {
            "id": "v1", "source": "existing_project", "consume_at": "check",
            "established_by": {"kind": "project"},
            "stored_in": {"kind": "project_file", "path": "missing.md", "verification_id": "v1"}}
        contract = check.check_step_contract(_Ctx(), task, task["plan"], DONE)
        self.assertIn("stored_in.project_file.path not found",
                      contract["problems"][0]["verifications"][0]["reason"])

    def test_legacy_contract_without_stored_in_is_consumed_by_id(self):
        task = _task_with_contract()
        task["execution"]["verifications"][0].pop("stored_in")
        task["execution"]["verifications"][0].pop("established_by")
        contract = check.check_step_contract(_Ctx(), task, task["plan"], DONE)
        self.assertEqual(contract["problems"], [])
        self.assertEqual(contract["legacy_verifications"], ["v1"])

    def test_plain_task_has_no_gate(self):
        contract = check.check_step_contract(_Ctx(), {"id": "t"}, {}, [])
        self.assertEqual(contract["problems"], [])


if __name__ == "__main__":
    unittest.main()

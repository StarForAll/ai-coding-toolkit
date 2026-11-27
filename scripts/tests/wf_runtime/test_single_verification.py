"""单次验证运行（十轮收敛项）：只跑一条、只记一次运行；失败运行可作为 TDD 红证据。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, fingerprint, records  # noqa: E402


class _Ctx:
    def __init__(self, root):
        self.root = str(root)


def _verification(exit_code):
    return {"id": "v1", "invocation": {"kind": "argv",
                                       "argv": [sys.executable, "-c", f"raise SystemExit({exit_code})"]},
            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}


class SingleRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-single-run-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        records.write_json(str(self.task_dir / "task.json"),
                           {"id": "t1", "title": "t", "status": "in_progress", "execution": {},
                            "plan": {"verifications": [_verification(0)]}})

    def test_single_run_records_identity_without_check(self):
        task = records.load_json(str(self.task_dir / "task.json"))
        task_after, entry = check.run_single_verification(_Ctx(self.root), task, "v1")
        self.assertEqual(entry["verification_id"], "v1")
        self.assertEqual(entry["status"], "passed")
        self.assertTrue(entry.get("verification_digest"))
        self.assertEqual(len(task_after["execution"]["verification_runs"]), 1)
        self.assertIsNone(task_after.get("check"), "单次运行不能产生 Check 结论")

    def test_unknown_verification_is_refused(self):
        task = records.load_json(str(self.task_dir / "task.json"))
        with self.assertRaises(check.CheckError) as caught:
            check.run_single_verification(_Ctx(self.root), task, "nope")
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")

    def test_manual_verification_has_no_command(self):
        task = records.load_json(str(self.task_dir / "task.json"))
        task["plan"]["verifications"] = [{"id": "m1", "invocation": {"kind": "manual"}}]
        with self.assertRaises(check.CheckError) as caught:
            check.run_single_verification(_Ctx(self.root), task, "m1")
        self.assertIn("manual", str(caught.exception.facts))

    def test_failed_run_can_back_tdd_red(self):
        task = records.load_json(str(self.task_dir / "task.json"))
        task["plan"]["verifications"] = [_verification(1)]
        _after, red_entry = check.run_single_verification(_Ctx(self.root), task, "v1")
        self.assertEqual(red_entry["status"], "failed")
        # 绿来自本次 Check（command 形状），红来自单次运行
        plan_verification = _verification(0)
        green = {"verification_id": "v1",
                 "verification_digest": fingerprint.verification_digest(plan_verification),
                 "status": "passed", "evidence_ref": "v1"}
        evidence = {"assertion": "a", "red_reason": "r", "red_command_ref": "v1",
                    "green_command_ref": "v1", "properties": "p"}
        runs = check.verification_run_commands({"execution": {"verification_runs": [red_entry]}})
        problem = check.tdd_evidence_problem(evidence, [green], runs)
        # 定义摘要不同（一个失败版本一个通过版本）→ 必须拒绝，证明"身份"真的被核
        self.assertIsNotNone(problem)
        self.assertIn("different verification definitions", problem.get("reason", ""))


if __name__ == "__main__":
    unittest.main()

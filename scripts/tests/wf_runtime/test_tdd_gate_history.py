"""TDD 门禁必须消费 `--run-verification` 记录的红运行。

Check 定稿段把 `execution.verification_runs` 并入历史红证据；归档门禁
`task.tdd-verified` 若只读 `check_history`，正常 TDD 路径会"Check pass 但归档被拒"，
形成稳定复现的死循环。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, fingerprint, gates  # noqa: E402


class TddGateHistoryTest(unittest.TestCase):
    def _task(self):
        verification = {"id": "v1", "invocation": {"kind": "argv", "argv": ["true"]},
                        "cwd": ".", "required": True, "consume_at": "check"}
        digest = fingerprint.verification_digest(verification)
        red = {"verification_id": "v1", "verification_digest": digest, "status": "failed",
               "evidence_ref": "run-1"}
        green = {"verification_id": "v1", "verification_digest": digest, "status": "passed",
                 "evidence_ref": "check-log"}
        return {
            "id": "t-1",
            "plan": {"tdd": True, "tdd_applicability": "code", "verifications": [verification]},
            "check": {"commands": [green], "check_history": [],
                      "tdd_evidence": {"assertion": "先红后绿",
                                       "red_command_ref": "v1", "green_command_ref": "v1",
                                       "red_reason": "行为缺失",
                                       "properties": {"可红": "是", "快速": "是",
                                                      "确定性": "是", "可无人执行": "是"}}},
            "execution": {"verification_runs": [red]},
        }

    def test_run_verification_counts_as_red_history(self):
        satisfied, code, facts = gates.verify_step(None, self._task(), "task.tdd-verified")
        self.assertTrue(satisfied, (code, facts))

    def test_without_verification_runs_still_rejected(self):
        task = self._task()
        task["execution"] = {}
        satisfied, code, facts = gates.verify_step(None, task, "task.tdd-verified")
        self.assertFalse(satisfied)
        self.assertEqual(code, "WF_CHECK_FAILED")
        self.assertIn("red run not found", (facts or {}).get("reason", ""))


if __name__ == "__main__":
    unittest.main()

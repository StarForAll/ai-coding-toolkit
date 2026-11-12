"""P2-10：start 期验证证据必须固定在动作内（实现稿 §2.3.11 ⑥）。

历史状态：`_run_start_verifications` 的结果只进命令 facts——打印一次就没了，
归档/复盘时无从核对「开工时那条 `consume_at=start` 验证真的跑过」。
机制稿 §5.1 要求把跨记录写入固定在动作意图与后置里，因此证据并入
`action.inputs["start_verifications"]`，并在**结案前按真实后置重核**。

本文件钉住三件事：证据进动作、缺证据即 `WF_ACTION_INCOMPLETE`、
「把步骤标 done」不能代替证据。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402


def _task(verifications):
    return {"id": "t1", "plan": {"verifications": verifications}}


START_VER = {"id": "v-start", "consume_at": "start"}
CHECK_VER = {"id": "v-check", "consume_at": "check"}


class StartVerificationActionTest(unittest.TestCase):
    def test_only_start_point_verifications_are_required(self):
        task = _task([START_VER, CHECK_VER])
        self.assertEqual(tasks_mod._start_verification_ids(task), ["v-start"])

    def test_evidence_in_action_satisfies_the_postcondition(self):
        task = _task([START_VER])
        action = {"inputs": {"start_verifications": [{"verification_id": "v-start", "exit_code": 0}]}}
        self.assertEqual(tasks_mod._missing_start_verification_evidence(task, action), [])

    def test_missing_evidence_is_reported(self):
        task = _task([START_VER])
        for action in ({"inputs": {}}, {"inputs": {"start_verifications": []}},
                       {"inputs": {"start_verifications": [{"verification_id": "other"}]}}):
            with self.subTest(action=action):
                self.assertEqual(tasks_mod._missing_start_verification_evidence(task, action),
                                 ["v-start"])

    def test_marking_steps_done_does_not_substitute_evidence(self):
        """动作已 done 但没有证据 → 仍判未完成（防止「标 done 即算做」）。"""
        task = _task([START_VER])
        action = {"state": "done", "next_step": None, "steps": ["verify_approval"],
                  "inputs": {"task": "t1"}}
        self.assertEqual(tasks_mod._missing_start_verification_evidence(task, action), ["v-start"])

    def test_no_start_verifications_means_nothing_required(self):
        task = _task([CHECK_VER])
        self.assertEqual(tasks_mod._missing_start_verification_evidence(task, {"inputs": {}}), [])


if __name__ == "__main__":
    unittest.main()

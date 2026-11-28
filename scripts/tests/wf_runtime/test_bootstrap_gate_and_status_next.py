"""开工前置与状态页下一步的一致性。

缺陷形态：
1. 新项目可建普通任务并走完批准，直到 `task-start` 才被"缺基线/配置"拦下；此时会话
   已绑定不可开工对象，"先建 initialize 任务"的出口在本会话不可执行；
2. 批准后 `status` 仍按位置表报 `task-approve`，把 AI 送进必然被拒的重复批准；
3. 接收方在 recovering 读 `status --short` 时看不到 `handover_for_me`，next 被位置表
   指到 `bind`——与 `wf-start` 的接收四步相反。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, protocol, tasks  # noqa: E402

BASELINE = "# 项目基线\n"


class BootstrapPrerequisiteTest(unittest.TestCase):
    def test_missing_config_reported(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
            problem = tasks.bootstrap_prerequisite(root)
        self.assertIsNotNone(problem)
        self.assertEqual(problem["missing"], ".wf/project-config.json")
        self.assertTrue(any("initialize" in item for item in problem["exits"]))

    def test_missing_baseline_reported(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
            with open(os.path.join(root, ".wf", "project-config.json"), "w", encoding="utf-8") as handle:
                handle.write('{"schema_version": 1}\n')
            problem = tasks.bootstrap_prerequisite(root)
        self.assertIsNotNone(problem)
        self.assertEqual(problem["missing"], ".wf/baseline.md")

    def test_ready_project_passes(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
            with open(os.path.join(root, ".wf", "project-config.json"), "w", encoding="utf-8") as handle:
                handle.write('{"schema_version": 1}\n')
            with open(os.path.join(root, ".wf", "baseline.md"), "w", encoding="utf-8") as handle:
                handle.write(BASELINE)
            self.assertIsNone(tasks.bootstrap_prerequisite(root))


class StatusNextTest(unittest.TestCase):
    def setUp(self):
        self.states = protocol.states()

    def test_unapproved_plan_points_to_approve(self):
        for status in ("not_started", "in_progress"):
            text = self.states.next_for(status, "plan", approved=False)
            self.assertIn("task-approve", text)

    def test_approved_plan_points_to_start(self):
        for status in ("not_started", "in_progress"):
            text = self.states.next_for(status, "plan", approved=True)
            self.assertIn("task-start", text)

    def test_default_keeps_position_table(self):
        for status in self.states.status_enum:
            for phase in self.states.phase_enum:
                expected = self.states.next_by_position.get(f"{status}/{phase}")
                if expected is None:
                    continue
                self.assertEqual(self.states.next_for(status, phase), expected)

    def test_paused_wins_over_approval(self):
        text = self.states.next_for("not_started", "plan", paused=True, approved=True)
        self.assertIn("task-resume", text)


class FinishStaleCheckTest(unittest.TestCase):
    def test_finish_with_invalid_check_points_to_check(self):
        task = {"phase": "finish", "status": "in_progress"}
        scope = {"conditions": {"C1_check_valid": False}}
        self.assertIn("task-check", cli.finish_check_stale_next(task, scope))
        self.assertNotIn("archive", cli.finish_check_stale_next(task, scope))

    def test_valid_check_keeps_position_next(self):
        task = {"phase": "finish", "status": "in_progress"}
        scope = {"conditions": {"C1_check_valid": True}}
        self.assertIsNone(cli.finish_check_stale_next(task, scope))

    def test_paused_wins(self):
        task = {"phase": "finish", "status": "in_progress", "paused": True}
        scope = {"conditions": {"C1_check_valid": False}}
        self.assertIsNone(cli.finish_check_stale_next(task, scope))


class HandoverNextTextTest(unittest.TestCase):
    def _record(self, receiver="receiver-key"):
        return {
            "state": "recovering",
            "holder": None,
            "checkpoint": None,
            "handover": {
                "from": "initiator-key",
                "receiver_session_key": receiver,
                "object_or_preparation": {"kind": "task", "id": "t-1"},
                "invalidated_generation": 3,
            },
        }

    def test_receiver_gets_accept(self):
        handover, for_me, text = cli.handover_next_text(self._record(), "receiver-key")
        self.assertTrue(for_me)
        self.assertIn("writer-handover accept", text)
        self.assertIn("task:t-1", text)
        self.assertIn("from", handover)

    def test_initiator_and_third_party_wait(self):
        for key in ("initiator-key", "someone-else"):
            _, for_me, text = cli.handover_next_text(self._record(), key)
            self.assertFalse(for_me)
            self.assertNotIn("writer-handover accept", text)
            self.assertIn("repair", text)

    def test_non_recovering_has_no_next(self):
        _, for_me, text = cli.handover_next_text({"state": "held", "holder": {}}, "k")
        self.assertFalse(for_me)
        self.assertIsNone(text)

    def test_label_is_not_a_dict_repr(self):
        label = cli.handover_object_label({"object": {"kind": "task", "id": "t-1"}})
        self.assertEqual(label, "task:t-1")


if __name__ == "__main__":
    unittest.main()

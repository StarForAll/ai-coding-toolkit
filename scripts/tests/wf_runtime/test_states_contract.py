"""协议迁移登记与真实入口/出口一致（2026-11-28 外审 A2-6）。

区分力：`check.from` 缺 finish、`finish-invalidate.action` 只登记 baseline-apply、
finish 位置的 next 仍只写 archive —— 都会让本用例红。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import protocol  # noqa: E402


class StatesContractTest(unittest.TestCase):
    def setUp(self):
        self.states = protocol.states(REPO / "docs" / "workflows" / "wf" / "payload" / "protocol")
        self.by_id = {entry["id"]: entry for entry in self.states.transitions}

    def test_task_check_accepts_finish_phase(self):
        positions = {(item["status"], item.get("phase"))
                     for item in self.by_id["check"]["from"]}
        self.assertIn(("in_progress", "finish"), positions)

    def test_finish_invalidate_lists_both_actions(self):
        actions = self.by_id["finish-invalidate"]["action"]
        self.assertEqual(sorted(actions), ["baseline-apply", "spec-update"])

    def test_finish_next_mentions_recheck_when_c1_invalid(self):
        self.assertIn("task-check", self.states.next_by_position["in_progress/finish"])


if __name__ == "__main__":
    unittest.main()

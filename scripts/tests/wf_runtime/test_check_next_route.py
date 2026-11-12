"""R4：Check pass 的下一跳按复杂度分流（复杂任务先审查，不再固定指向 finish）。"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402


class CheckNextHintTest(unittest.TestCase):
    def test_complex_task_routes_to_review_launch(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "pass"})
        self.assertIn("review-launch", hint)

    def test_light_task_routes_to_finish(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "light"}}, {"result": "pass"})
        self.assertIn("finish", hint)
        self.assertNotIn("review-launch", hint)

    def test_failed_check_routes_to_repair_loop(self):
        hint = tasks.check_next_hint({"plan": {"complexity": "complex"}}, {"result": "fail"})
        self.assertIn("wf-repair-loop", hint)


if __name__ == "__main__":
    unittest.main()

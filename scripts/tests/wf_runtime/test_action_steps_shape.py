"""动作步骤的唯一形状：`{"id","state"}` 列表（自审查：同一字段两种形状会让按名比较失效）。"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import actions  # noqa: E402


class ActionStepsShapeTest(unittest.TestCase):
    def _action(self):
        return actions.new_action("run.advance", {"kind": "session", "id": "s"},
                                  0, {"run": "r"}, steps=["resolve_step", "create_or_reuse_task"])

    def test_new_action_emits_id_state_pairs(self):
        action = self._action()
        self.assertEqual(action["steps"],
                         [{"id": "resolve_step", "state": "pending"},
                          {"id": "create_or_reuse_task", "state": "pending"}])
        self.assertEqual(action["next_step"], "resolve_step")

    def test_step_done_advances_by_id(self):
        action = actions.step_done(self._action(), "resolve_step")
        self.assertEqual([item["state"] for item in action["steps"]], ["done", "pending"])
        self.assertEqual(action["next_step"], "create_or_reuse_task")
        self.assertEqual(action["state"], "applying")

    def test_step_done_rejects_unknown_step(self):
        with self.assertRaises(ValueError):
            actions.step_done(self._action(), "nope")

    def test_complete_marks_every_step_done(self):
        action = actions.complete(self._action(), summary="x")
        self.assertEqual([item["state"] for item in action["steps"]], ["done", "done"])
        self.assertIsNone(action["next_step"])
        self.assertEqual(action["state"], "done")

    def test_legacy_actions_with_plain_names_still_step(self):
        legacy = {"kind": "run.advance", "steps": ["a", "b"], "state": "prepared", "next_step": "a"}
        stepped = actions.step_done(legacy, "a")
        self.assertEqual(stepped["steps"], [{"id": "a", "state": "done"},
                                            {"id": "b", "state": "pending"}])
        self.assertEqual(stepped["next_step"], "b")


if __name__ == "__main__":
    unittest.main()

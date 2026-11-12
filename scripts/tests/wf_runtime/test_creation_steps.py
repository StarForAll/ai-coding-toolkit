"""创建输入必须逐步骤声明适用性（机制稿 §7.2）。

理由：未出现的步骤不能被推断为 `applicable`——「人确认它适用」与「人没看它」
在事后追责上不是一回事，脚本也不替人做这个确认。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

DOC = {"inputs": {}, "steps": [{"id": "one", "type": "human"}, {"id": "two", "type": "task"}]}


def _creation(steps):
    return {"definition_id": "demo", "definition_digest": "sha256:" + "a" * 64,
            "inputs": {}, "steps": steps}


class CreationStepsTest(unittest.TestCase):
    def test_full_declaration_passes(self):
        problems = runs.creation_problems(_creation({"one": "applicable", "two": "skipped"}), DOC)
        self.assertEqual(problems, [])

    def test_missing_step_is_rejected(self):
        problems = runs.creation_problems(_creation({"one": "applicable"}), DOC)
        self.assertTrue(any("declare every step" in item["reason"] for item in problems),
                        f"未声明 two 应被拒：{problems}")
        self.assertEqual([item.get("missing") for item in problems if item.get("missing")], [["two"]])

    def test_undeclared_and_bad_value_still_rejected(self):
        problems = runs.creation_problems(_creation({"one": "applicable", "two": "maybe", "x": "applicable"}), DOC)
        reasons = " ".join(item["reason"] for item in problems)
        self.assertIn("undeclared step", reasons)
        self.assertIn("value must be one of", reasons)


if __name__ == "__main__":
    unittest.main()

"""B2：`--short` 的 `task.check` 必须是派生值，不能是记录的 `result`。

历史缺陷：`--short` 直接回 `check.result`。锚点漂移（对象/标准变了）之后记录的 `result`
仍是 `pass`，于是 short 输出说"check: pass"，而门禁 `check_validity` 判 `anchor_drift`
→ 展示与事实矛盾，AI 会据此以为检查还有效。

现在 `check` 报"能不能用"：`usable` 或第一个 blocker token；原始记录值另列 `check_result`。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, gates, tasks as tasks_mod  # noqa: E402

SAVED = "sha256:" + "a" * 64
CURRENT = "sha256:" + "b" * 64


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)

    def rule_version(self):
        return "rules-v1"


def task_record(result="pass", anchor=SAVED):
    return {"id": "t1", "phase": "check", "status": "in_progress", "plan": {"complexity": "light"},
            "entry_snapshot": {"touch_paths": []},
            "check": {"id": "c1", "result": result, "anchor": {"check_anchor": anchor},
                      "commands": []}}


class ShortCheckTest(unittest.TestCase):
    def test_anchor_drift_is_not_reported_as_pass(self):
        with mock.patch.object(tasks_mod, "current_check_anchor",
                               return_value={"anchor": CURRENT, "parts": {}}), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            facts = cli._short_check(FakeCtx("/tmp"), task_record())
        self.assertEqual(facts["check"], "anchor_drift")
        self.assertEqual(facts["check_result"], "pass")     # 原始值仍可追溯，但不冒充"能用"

    def test_usable_check_says_usable(self):
        with mock.patch.object(tasks_mod, "current_check_anchor",
                               return_value={"anchor": SAVED, "parts": {}}), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            facts = cli._short_check(FakeCtx("/tmp"), task_record())
        self.assertEqual(facts["check"], "usable")
        self.assertEqual(facts["check_result"], "pass")

    def test_failed_check_reports_its_blocker(self):
        with mock.patch.object(tasks_mod, "current_check_anchor",
                               return_value={"anchor": SAVED, "parts": {}}):
            facts = cli._short_check(FakeCtx("/tmp"), task_record(result="fail"))
        self.assertEqual(facts["check"], "result_not_pass")


if __name__ == "__main__":
    unittest.main()

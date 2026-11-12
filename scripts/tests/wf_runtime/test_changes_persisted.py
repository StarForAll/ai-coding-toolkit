"""D1：`changes-persisted` 缺项要说清楚"这一步由归档动作完成"。

历史缺陷：只要存在待提交路径就返回 `WF_WIP_UNRESOLVED`——即使本任务已经拿到覆盖这些
路径的提交授权。于是归档前看门禁的 AI 被推向"先手工提交再归档"，而归档自己就会提交
同一批路径（`archive` 内的业务提交），等于多一条重复路径、还制造"归档探路"。

现在分三种事实：
- 有待提交路径、**没有**提交授权 → `WF_COMMIT_NOT_AUTHORIZED`（先拿授权）；
- 有授权但**没覆盖全** → `WF_WIP_UNRESOLVED`（列出未覆盖路径）；
- 有授权且**全覆盖** → `WF_ACTION_INCOMPLETE` + `fulfilled_by: "archive_commit"` +
  `resumable: true`（直接归档，不要先手工提交）。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402


class ChangesPersistedFactTest(unittest.TestCase):
    def facts(self, pending, grants):
        task = {"id": "t1", "commit_grants": [{"subject": grant} for grant in grants]}
        with mock.patch.object(tasks_mod, "pending_delivery_paths", return_value=list(pending)):
            return tasks_mod.changes_persisted_fact(None, task)

    def test_nothing_pending_is_satisfied(self):
        satisfied, code, facts = self.facts([], [])
        self.assertTrue(satisfied)
        self.assertIsNone(code)
        self.assertEqual(facts, {"paths": []})

    def test_pending_without_grant_asks_for_authorization(self):
        satisfied, code, facts = self.facts(["pkg/a.py"], [])
        self.assertFalse(satisfied)
        self.assertEqual(code, "WF_COMMIT_NOT_AUTHORIZED")
        self.assertEqual(facts["pending_paths"], ["pkg/a.py"])

    def test_grant_that_does_not_cover_stays_unresolved(self):
        satisfied, code, facts = self.facts(["pkg/a.py", "docs/b.md"], ["pkg/**"])
        self.assertFalse(satisfied)
        self.assertEqual(code, "WF_WIP_UNRESOLVED")
        self.assertEqual(facts["uncovered_paths"], ["docs/b.md"])

    def test_full_coverage_points_at_the_archive_commit(self):
        satisfied, code, facts = self.facts(["pkg/a.py", "docs/b.md"],
                                            ["pkg/**", "docs/b.md"])
        self.assertFalse(satisfied)              # 步骤本身仍未完成……
        self.assertEqual(code, "WF_ACTION_INCOMPLETE")
        self.assertEqual(facts["fulfilled_by"], "archive_commit")   # ……但由归档提交完成
        self.assertTrue(facts["resumable"])
        self.assertTrue(any("wf archive" in item for item in facts["exits"]))

    def test_coverage_matching_is_shared_and_exact(self):
        self.assertEqual(tasks_mod.uncovered_commit_paths(["pkg/a.py"], ["pkg/**"]), [])
        self.assertEqual(tasks_mod.uncovered_commit_paths(["pkg/a.py"], ["pkg/a.py"]), [])
        self.assertEqual(tasks_mod.uncovered_commit_paths(["pkg/a.py"], ["other/**"]), ["pkg/a.py"])


if __name__ == "__main__":
    unittest.main()

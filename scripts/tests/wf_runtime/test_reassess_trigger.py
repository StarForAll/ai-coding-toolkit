"""挂起复评触发面：合法 `suspended` 只报告事实，不阻断归档/启动（第十六轮复审 F1）。

历史实现把任何挂起记录当"未知残留"抛 `WF_HISTORY_UNRESOLVED`；挂起是 task-rework 写入的
合法状态（设计稿 §5.4"T 挂起、R 执行是合法组合"），返工闭环收尾与挂起期间的 status 都会踩到。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402


class ReassessTriggerTest(unittest.TestCase):
    def test_suspended_task_is_reported_not_raised(self):
        blocked = {"id": "2026-" + "a" * 32, "status": "in_progress", "phase": "execute",
                   "suspended": True, "prerequisites": ["2026-" + "b" * 32]}
        with mock.patch.object(tasks, "iter_tasks", return_value=[(None, blocked)]), \
                mock.patch.object(tasks, "reassess_problems", return_value=[{"condition": "rework_set_non_empty", "ok": True}]):
            report = tasks._reassess_empty_set(mock.Mock(root="/nonexistent"))
        self.assertTrue(report["waiting"])
        self.assertEqual([item["id"] for item in report["suspended_tasks"]], [blocked["id"]])
        self.assertEqual([item["id"] for item in report["waiting_tasks"]], [blocked["id"]])
        self.assertEqual(report["reassessed"], [])

    def test_no_suspended_tasks_means_clean_report(self):
        with mock.patch.object(tasks, "iter_tasks", return_value=[]):
            report = tasks._reassess_empty_set(mock.Mock(root="/nonexistent"))
        self.assertFalse(report["waiting"])
        self.assertEqual(report["suspended_tasks"], [])

    def test_condition_error_degrades_to_unverified(self):
        blocked = {"id": "2026-" + "d" * 32, "status": "in_progress", "phase": "execute", "suspended": True}
        with mock.patch.object(tasks, "iter_tasks", return_value=[(None, blocked)]), \
                mock.patch.object(tasks, "reassess_problems", side_effect=RuntimeError("boom")):
            report = tasks._reassess_empty_set(mock.Mock(root="/nonexistent"))
        self.assertFalse(report["waiting"])
        self.assertEqual([item["id"] for item in report["unknown"]], [blocked["id"]])
        self.assertIsNone(report["conditions"][blocked["id"]])


    def test_suspended_without_rework_set_is_unknown_not_waiting(self):
        """非法组合（挂起但返工集合为空）：不可指向 task-reassess，出口是 abandon/repair。"""
        blocked = {"id": "2026-" + "e" * 32, "status": "in_progress", "phase": "execute", "suspended": True}
        with mock.patch.object(tasks, "iter_tasks", return_value=[(None, blocked)]), \
                mock.patch.object(tasks, "reassess_problems",
                                  return_value=[{"condition": "rework_set_non_empty", "ok": False}]):
            report = tasks._reassess_empty_set(mock.Mock(root="/nonexistent"))
        self.assertFalse(report["waiting"])
        self.assertEqual([item["id"] for item in report["unknown"]], [blocked["id"]])
        self.assertIn("task-abandon", report["unknown"][0]["exits"])


if __name__ == "__main__":
    unittest.main()

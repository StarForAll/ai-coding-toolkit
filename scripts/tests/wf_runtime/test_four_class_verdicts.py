"""巡检四类三态（机制稿 §8.5）：报告四类各自 passed/failed/unknown 及未覆盖对象。

要点：`unknown` **不等于通过**——只要有一类 unknown，整体就不能称"巡检通过"；
未覆盖对象必须显式列出，不能只给知识统计就说巡检过了。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402


def verdicts(**kwargs):
    base = dict(archive_terminals=[], archive_references={"dangling": [], "unknown": []},
                spec_usage={"unknown": [], "problem": None, "statistic_complete": True},
                incomplete=[], every_problem=None, manual_compare=[], author_order=[],
                out_of_scope_duplicates=[])
    base.update(kwargs)
    return tasks_mod._four_class_verdicts([], **base)


class FourClassVerdictTest(unittest.TestCase):
    def test_clean_scan_passes_all_four(self):
        report = verdicts()
        self.assertEqual(report["overall"], "passed")
        self.assertEqual([item["class"] for item in report["verdicts"]],
                         ["archive_references", "archive_terminals", "archive_ids", "knowledge"])
        self.assertEqual(report["uncovered"], [])

    def test_unknown_is_not_pass(self):
        report = verdicts(archive_references={"dangling": [], "unknown": [{"path": "x.md"}]})
        reference = next(item for item in report["verdicts"] if item["class"] == "archive_references")
        self.assertEqual(reference["status"], "unknown")
        self.assertEqual(report["overall"], "unknown", "unknown 不能被当成通过")
        self.assertTrue(report["uncovered"], "未覆盖对象必须列出")

    def test_failed_outranks_unknown_overall(self):
        report = verdicts(archive_terminals=[{"task": "t1", "reason": "bad terminal"}],
                          spec_usage={"unknown": [{"reason": "sample"}], "problem": None,
                                      "statistic_complete": False})
        self.assertEqual(report["overall"], "failed")

    def test_incomplete_archive_lands_in_unknown(self):
        report = verdicts(incomplete=[{"task": "t2", "reason": "archived_at missing or unparsable"}])
        terminal = next(item for item in report["verdicts"] if item["class"] == "archive_terminals")
        self.assertEqual(terminal["status"], "unknown")

    def test_non_archived_status_lands_in_id_class(self):
        report = verdicts(incomplete=[{"task": "t3", "reason": "archived record is not status=archived"}])
        ids = next(item for item in report["verdicts"] if item["class"] == "archive_ids")
        self.assertEqual(ids["status"], "failed")

    def test_knowledge_failed_from_governance_lists(self):
        report = verdicts(manual_compare=[{"pair": "a/b", "class": "witnessed"}])
        knowledge = next(item for item in report["verdicts"] if item["class"] == "knowledge")
        self.assertEqual(knowledge["status"], "failed")


if __name__ == "__main__":
    unittest.main()

"""P3/S9：`review-status` 的到位判定，以及 S3 判定句的三态推导。

防的失败（dogfood D3「人当传声筒」）：8 轮里有 8 次人工转述"已在其他 agent 完成"，
因为框架没有一处能回答"这一轮到齐了吗、缺哪份、那份文件现在算什么状态"。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)


def write_report(root, relative, payload_text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload_text, encoding="utf-8")
    return path


class ReviewStatusTest(unittest.TestCase):
    def _task(self, imported=()):
        return {"id": "2026-x", "title": "t", "status": "in_progress", "phase": "check",
                "reviews": {"launches": [{"round": 1, "slots": [{"slot": "zcode"}, {"slot": "dsh"}]}],
                            "imported": list(imported)}}

    def test_missing_slot_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            facts = review.status_of_round(FakeCtx(tmp), self._task())
        self.assertEqual(facts["round"], 1)
        self.assertEqual(facts["required"], 2)
        self.assertEqual(facts["arrived"], 0)
        self.assertEqual(sorted(facts["missing"]), ["dsh", "zcode"])
        self.assertFalse(facts["material_ready"])

    def test_imported_and_missing_are_distinguished(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel = "review/round-1/review-zcode.md"
            path = write_report(tmp, rel, "报告正文")
            digest = records.file_digest(path)
            task = self._task(imported=[{"round": 1, "slot": "zcode", "agent": "zcode",
                                         "report_path": rel, "report_digest": digest,
                                         "anchor": {"check_anchor": "sha256:whatever"}}])
            facts = review.status_of_round(FakeCtx(tmp), task)
            slots = {item["slot"]: item for item in facts["slots"]}
            self.assertEqual(slots["zcode"]["state"], "imported")
            # 假任务的记录不完整 ⇒ 锚点核不了：如实标 anchor_checked=False，不假装新鲜
            self.assertFalse(slots["zcode"]["anchor_checked"])
            self.assertEqual(slots["dsh"]["state"], "missing")
            self.assertEqual(facts["arrived"], 1)
            self.assertFalse(facts["material_ready"])

    def test_report_changed_after_import_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel = "review/round-1/review-zcode.md"
            write_report(tmp, rel, "改过的正文")
            task = self._task(imported=[{"round": 1, "slot": "zcode", "agent": "zcode",
                                         "report_path": rel, "report_digest": "sha256:deadbeef",
                                         "anchor": {}}])
            facts = review.status_of_round(FakeCtx(tmp), task)
            slots = {item["slot"]: item for item in facts["slots"]}
            self.assertEqual(slots["zcode"]["state"], "stale")
            self.assertIn("改写", slots["zcode"]["reason"])


class DeriveVerdictTest(unittest.TestCase):
    AXES = {"range": "pass", "acceptance": "pass", "contract": "pass",
            "regression": "pass", "testability": "pass"}

    def test_all_pass(self):
        conclusion, problems, gaps, blocking = review.derive_verdict(self.AXES, [])
        self.assertEqual((conclusion, problems, gaps, blocking), ("pass", [], [], []))

    def test_uncovered_is_a_gap_not_a_failure(self):
        axes = dict(self.AXES, acceptance="uncovered")
        conclusion, problems, gaps, _blocking = review.derive_verdict(axes, [])
        self.assertEqual(conclusion, "pass")
        self.assertEqual(problems, [])
        self.assertEqual([item["axis"] for item in gaps], ["acceptance"])

    def test_fail_axis_without_blocking_finding_is_input_invalid(self):
        axes = dict(self.AXES, contract="fail")
        _conclusion, problems, _gaps, _blocking = review.derive_verdict(axes, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("一义三用", problems[0]["reason"])

    def test_blocking_finding_makes_it_fail(self):
        axes = dict(self.AXES, contract="fail")
        conclusion, problems, _gaps, blocking = review.derive_verdict(
            axes, [{"id": "f1", "severity": "blocking"}])
        self.assertEqual(conclusion, "fail")
        self.assertEqual(problems, [])
        self.assertEqual(len(blocking), 1)

    def test_missing_axis_is_input_invalid(self):
        axes = dict(self.AXES)
        axes.pop("testability")
        _conclusion, problems, _gaps, _blocking = review.derive_verdict(axes, [])
        self.assertTrue(any(item["reason"].startswith("report does not cover") for item in problems))


if __name__ == "__main__":
    unittest.main()

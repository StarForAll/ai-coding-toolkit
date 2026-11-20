"""P3/S9：`review-status` 的到位判定，以及 S3 判定句的三态推导。

防的失败（dogfood D3「人当传声筒」）：8 轮里有 8 次人工转述"已在其他 agent 完成"，
因为框架没有一处能回答"这一轮到齐了吗、缺哪份、那份文件现在算什么状态"。
"""

import os
import sys
import tempfile
import unittest
import uuid
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
    def setUp(self):
        self._task_id = f"2026-status-{uuid.uuid4().hex[:8]}"

    def _task(self, imported=()):
        return {"id": self._task_id, "title": "t", "status": "in_progress", "phase": "check",
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

    def test_in_progress_placeholders_are_writing_not_arrived(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_id = "2026-status-writing"
            for agent in ("zcode", "dsh"):
                staged = Path(review.agent_report_path(FakeCtx(tmp), task_id, 1, agent))
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text("<!-- wf-review-agent:v1 status=in-progress -->\n",
                                  encoding="utf-8")
            task = self._task()
            task["id"] = task_id
            facts = review.status_of_round(FakeCtx(tmp), task)
        self.assertEqual(facts["arrived"], 0)
        self.assertEqual(sorted(facts["writing"]), ["dsh", "zcode"])
        self.assertFalse(facts["material_ready"])

    def test_done_staged_reports_are_ready_to_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_id = "2026-status-ready"
            for agent in ("zcode", "dsh"):
                staged = Path(review.agent_report_path(FakeCtx(tmp), task_id, 1, agent))
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text("<!-- wf-review-agent:v1 status=done -->\n",
                                  encoding="utf-8")
            task = self._task()
            task["id"] = task_id
            facts = review.status_of_round(FakeCtx(tmp), task)
        self.assertEqual(sorted(facts["ready_to_import"]), ["dsh", "zcode"])
        self.assertTrue(facts["material_ready"])

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


class ReportShapeTest(unittest.TestCase):
    def test_lint_reports_malformed_findings_and_round_without_crashing(self):
        import json
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": "x",
                   "read-scope": ["pkg/**"], "excluded-scope": [],
                   "findings": 3, "axes": {axis: "pass" for axis in review.REVIEW_AXES}}
        text = ("<!-- wf-review-agent:v1 status=done -->\n"
                + review.REPORT_MARKER + "\n\n```json\n"
                + json.dumps(payload) + "\n```\n")
        linted = review.lint_report(None, None, text)
        self.assertFalse(linted["ok"])
        reasons = "\n".join(item.get("reason", "") for item in linted["problems"])
        self.assertIn("findings must be an array", reasons)
        self.assertIn("positive integer", reasons)

    def test_invalid_severity_is_rejected_not_treated_as_suggestion(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": ["pkg/**"], "excluded-scope": [],
                   "findings": [{"id": "f1", "severity": "blockng"}],
                   "axes": {axis: "pass" for axis in review.REVIEW_AXES}}
        shared = review.report_input_problems(payload)
        self.assertTrue(shared["checks"]["findings-shape"])
        self.assertIsNone(shared["verdict"])

    def test_duplicate_finding_ids_are_rejected(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": ["pkg/**"], "excluded-scope": [],
                   "findings": [{"id": "f1", "severity": "blocking"},
                                {"id": "f1", "severity": "blocking"}],
                   "axes": {axis: "fail" for axis in review.REVIEW_AXES}}
        shared = review.report_input_problems(payload)
        self.assertTrue(shared["checks"]["findings-shape"])

    def test_subdirectory_sensitive_file_is_mandatory_excluded(self):
        self.assertTrue(any(review.pattern_overlap("pkg/.env", pattern)
                            for pattern in review.DEFAULT_EXCLUSIONS))

    def test_finding_without_id_is_rejected(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": ["pkg/**"],
                   "excluded-scope": [],
                   "findings": [{"severity": "blocking", "statement": "缺 id"}],
                   "axes": {axis: "fail" for axis in review.REVIEW_AXES}}
        shared = review.report_input_problems(payload)
        self.assertIn("findings-shape", shared["checks"])
        self.assertTrue(shared["checks"]["findings-shape"])

    def test_dot_prefixed_outside_read_is_rejected(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": ["./.wf/tasks/other/prd.md"], "excluded-scope": [],
                   "findings": [], "axes": {axis: "pass" for axis in review.REVIEW_AXES}}
        launch = {"readable_scope": {"business_code": ["pkg/**"], "spec": [],
                                     "prd": ".wf/tasks/t1/prd.md"},
                  "exclusions": []}
        shared = review.report_input_problems(payload, launch=launch)
        self.assertTrue(shared["checks"]["read-scope-readable"])

    def test_absolute_read_scope_is_rejected(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": ["/etc/passwd"], "excluded-scope": [],
                   "findings": [], "axes": {axis: "pass" for axis in review.REVIEW_AXES}}
        shared = review.report_input_problems(payload)
        self.assertIn("read-scope-path", shared["checks"])
        self.assertTrue(shared["checks"]["read-scope-path"])

    def test_malformed_collections_return_problems_not_typeerror(self):
        payload = {"protocol": review.PROTOCOL, "task-id": "t", "round": 1,
                   "read-scope": 3, "excluded-scope": {}, "findings": {},
                   "axes": []}
        shared = review.report_input_problems(payload)
        text = "\n".join(item.get("reason", "") for item in review.flatten_checks(shared["checks"]))
        self.assertIn("must be an array", text)
        self.assertIn("axes must be an object", text)


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

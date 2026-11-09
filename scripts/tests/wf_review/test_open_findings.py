"""P3/S6：blocking 无处置必须阻断归档（`WF_UNRESOLVED_BLOCKING`）。

防的失败（dogfood）：唯一那条 blocking 的处置只有自由文本 evidence，没有任何可核的关闭动作；
框架当时既没有"未处置"这个概念，也没有对应的阻断码——于是"报了 blocking 也能归档"。
这里锁三件事：投影能算出未处置、已关闭的不再算未处置、报告被改写时如实标不可用。
"""

import json
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


def write_report(root, relative, findings):
    payload = {"protocol": review.PROTOCOL, "task-id": "t1", "round": 1,
               "review-time": "2026-11-09T00:00:00Z", "review-focus": "f",
               "check-anchor": {"check_id": "c1", "check_anchor": "sha256:x"},
               "read-scope": [], "excluded-scope": [], "scope-exceptions": [],
               "axes": {axis: "pass" for axis in review.REVIEW_AXES},
               "findings": findings, "verdict": "pass"}
    body = (f"{review.REPORT_MARKER}\n\n```json\n"
            f"{json.dumps(payload, ensure_ascii=False)}\n```\n")
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def task_with(root, findings, dispositions=None):
    path = write_report(root, "review/round-1/review-zcode.md", findings)
    return {"id": "t1", "reviews": {
        "imported": [{"round": 1, "slot": "zcode", "report_path": "review/round-1/review-zcode.md",
                      "report_digest": records.file_digest(path),
                      "anchor": {"check_anchor": "sha256:x"}}],
        "dispositions": list(dispositions or [])}}


class OpenFindingsTest(unittest.TestCase):
    def test_blocking_without_disposition_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(tmp, [{"id": "f1", "severity": "blocking"}])
            result = review.open_findings(FakeCtx(tmp), task)
        self.assertEqual([item["finding_id"] for item in result["blocking"]], ["f1"])
        self.assertEqual(result["unavailable"], [])

    def test_accepted_disposition_closes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(tmp, [{"id": "f1", "severity": "blocking"}],
                             dispositions=[{"finding_id": "f1", "decision": "accepted",
                                            "reason": "已修", "recheck_by": "dsh"}])
            result = review.open_findings(FakeCtx(tmp), task)
        self.assertEqual(result["blocking"], [])
        self.assertEqual(result["closed"], ["f1"])

    def test_rejected_disposition_does_not_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(tmp, [{"id": "f1", "severity": "blocking"}],
                             dispositions=[{"finding_id": "f1", "decision": "rejected",
                                            "reason": "不认可", "recheck_by": "dsh"}])
            result = review.open_findings(FakeCtx(tmp), task)
        self.assertEqual(len(result["blocking"]), 1)

    def test_report_changed_after_import_is_unavailable_not_silently_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(tmp, [{"id": "f1", "severity": "blocking"}])
            Path(tmp, "review/round-1/review-zcode.md").write_text("改过", encoding="utf-8")
            result = review.open_findings(FakeCtx(tmp), task)
        self.assertEqual(len(result["unavailable"]), 1)
        self.assertEqual(result["blocking"], [])

    def test_blocking_code_is_registered(self):
        from wflib import codes

        self.assertIn("WF_UNRESOLVED_BLOCKING", codes.CODES)
        self.assertEqual(codes.tier_of("WF_UNRESOLVED_BLOCKING"), "blocked")
        self.assertTrue(codes.exit_of("WF_UNRESOLVED_BLOCKING").strip())


if __name__ == "__main__":
    unittest.main()

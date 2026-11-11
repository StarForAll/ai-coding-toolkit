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


class AllFindingsTest(unittest.TestCase):
    """骨架的 `findings` 必须是**全部**（含已处置），`unaddressed` 只是子集。"""

    def test_closed_findings_stay_in_the_full_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(tmp, [{"id": "f1", "severity": "blocking"},
                                   {"id": "f2", "severity": "suggestion"}],
                             dispositions=[{"finding_id": "f1", "decision": "accepted",
                                            "reason": "已修", "recheck_by": "dsh"}])
            full, _unreadable = review.all_findings(FakeCtx(tmp), task)
            open_items = review.open_findings(FakeCtx(tmp), task)
        self.assertEqual(sorted(item["id"] for item in full), ["f1", "f2"])
        self.assertTrue(next(item for item in full if item["id"] == "f1")["closed"])
        self.assertEqual([item["finding_id"] for item in open_items["unaddressed"]], ["f2"])


class BlockingUnknownTest(unittest.TestCase):
    """Q2=甲：blocking 与 blocking_unknown 分列，出口不同、互不混淆。
    Q1=乙：放行按 (round, slot, report_digest) 逐项匹配；批量写入、逐项撤销。"""

    def _ctx(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace

        root = tempfile.mkdtemp(prefix="wf-unknown-")
        Path(root, "review").mkdir()
        Path(root, "review", "s1.md").write_text("changed", encoding="utf-8")
        return SimpleNamespace(root=root, key=lambda required=True: "k")

    def _task(self, extra=None):
        task = {"id": "t", "reviews": {"imported": [
            {"round": 1, "slot": "s1", "report_path": "review/s1.md",
             "report_digest": "sha256:ORIGINAL"}]}}
        if extra:
            task["reviews"].update(extra)
        return task

    def test_unknown_is_separate_from_blocking(self):
        from wflib import review

        out = review.open_findings(self._ctx(), self._task())
        self.assertEqual(out["blocking"], [])
        self.assertEqual(len(out["blocking_unknown"]), 1)
        self.assertEqual(len(out["pending_unknown"]), 1)
        self.assertEqual(out["blocking_unknown"][0]["cause"], "changed")
        self.assertEqual(out["blocking_unknown"][0]["report_digest"], "sha256:ORIGINAL")

    def test_acceptance_must_match_digest(self):
        from wflib import review

        accepted = {"unknown_acceptances": [{"round": 1, "slot": "s1", "report_digest": "sha256:OTHER",
                                            "by": "human:x", "quote": "q"}]}
        out = review.open_findings(self._ctx(), self._task(accepted))
        self.assertEqual(len(out["pending_unknown"]), 1, "摘要不同不得匹配")

    def test_matching_acceptance_clears_only_that_entry(self):
        from wflib import review

        accepted = {"unknown_acceptances": [{"round": 1, "slot": "s1",
                                            "report_digest": "sha256:ORIGINAL",
                                            "by": "human:x", "quote": "q"}]}
        out = review.open_findings(self._ctx(), self._task(accepted))
        self.assertEqual(out["pending_unknown"], [])
        self.assertTrue(out["blocking_unknown"][0]["accepted"])

    def test_revoked_acceptance_blocks_again(self):
        from wflib import review

        accepted = {"unknown_acceptances": [{"round": 1, "slot": "s1",
                                            "report_digest": "sha256:ORIGINAL", "revoked": True}]}
        out = review.open_findings(self._ctx(), self._task(accepted))
        self.assertEqual(len(out["pending_unknown"]), 1)

    def test_unknown_and_blocking_never_overlap(self):
        """不变量：同一个 (round, slot, id) 不会同时在两类里。"""
        from wflib import review

        out = review.open_findings(self._ctx(), self._task())
        self.assertEqual({item["finding_id"] for item in out["blocking"]} &
                         {item.get("finding_id") for item in out["blocking_unknown"]}, set())

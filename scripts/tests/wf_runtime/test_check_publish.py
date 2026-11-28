"""Check 发布与消费同条件（2026-11-28 外审 A1-3）。

区分力：
- 双轴 pass 缺 basis 在准备段即被拒（不需要先跑长验证）；
- 定稿段发布 pass 前复用 `check.validate_check_result`，不写一个 Finish 会拒的记录；
- 锁外执行期间 notes 变化 → `WF_CHECK_STALE`。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check as check_mod  # noqa: E402


def _write_notes(data):
    handle, path = tempfile.mkstemp(suffix="-review-notes.json")
    os.close(handle)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    return path


def _state(notes_path=None, internal_review=None, digest=None):
    return {
        "anchor": "sha256:" + "a" * 64,
        "plan": {"verifications": []},
        "decisions": [],
        "started": "2026-11-28T00:00:00.000000Z",
        "scan_before": [],
        "scope_facts": {"buckets": {key: [] for key in "abcdef"},
                        "external_changes": [], "governance": []},
        "coverage": {},
        "governance_violations": [],
        "parts": {"paths_digest": "sha256:" + "b" * 64,
                  "content_digest": "sha256:" + "c" * 64},
        "review_notes_path": notes_path,
        "internal_review": internal_review,
        "review_notes_problem": None,
        "review_notes_digest": digest,
        "exclusion_records": [],
        "step_contract": {"problems": []},
    }


class ReviewNotesTest(unittest.TestCase):
    def test_pass_without_basis_is_rejected(self):
        path = _write_notes({"standard": {"conclusion": "pass"},
                             "requirement": {"conclusion": "pass"}})
        review, problem = check_mod._parse_review_notes(path)
        self.assertIsNone(review)
        self.assertIn("lacks basis", problem["reason"])
        os.unlink(path)

    def test_pass_with_basis_is_accepted(self):
        path = _write_notes({"standard": {"conclusion": "pass", "basis": "spec 条款"},
                             "requirement": {"conclusion": "pass", "basis": "PRD"}})
        review, problem = check_mod._parse_review_notes(path)
        self.assertIsNone(problem)
        self.assertEqual(review["standard"]["basis"], "spec 条款")
        os.unlink(path)


class ScopeParseTest(unittest.TestCase):
    """准备段解析 notes：缺 basis 不进入锁外执行。"""

    def _scope(self, notes_path):
        ctx = mock.Mock(root="/tmp/x")
        task = {"id": "t1", "plan": {"verifications": [], "acceptance": []},
                "execution": {}, "check": {}}
        with mock.patch.object(check_mod, "_receipts", return_value=[]), \
                mock.patch.object(check_mod.scope, "classify_candidates",
                                  return_value={"buckets": {key: [] for key in "abcdef"},
                                                "candidates": [], "touch_paths": []}), \
                mock.patch.object(check_mod.scope, "external_changes", return_value=({}, [])), \
                mock.patch.object(check_mod.scope, "delivery_set",
                                  return_value={"buckets": {"covered_f": [], "uncovered_f": []},
                                                "paths": []}), \
                mock.patch.object(check_mod.scope, "declaration_violations",
                                  return_value=([], {})), \
                mock.patch.object(check_mod, "_spec_coverage",
                                  return_value={"missing_curation": [], "unresolved": [],
                                                "period_problems": []}), \
                mock.patch.object(check_mod.fingerprint, "items", return_value=[]), \
                mock.patch.object(check_mod, "object_paths", return_value=[]), \
                mock.patch.object(check_mod, "current_anchor", return_value=("sha256:" + "a" * 64, {})), \
                mock.patch.object(check_mod, "check_step_contract", return_value={"problems": []}), \
                mock.patch.object(check_mod, "resolve_verifications", return_value=[]):
            return check_mod.run_check_scope(ctx, task, [], notes_path)

    def test_scope_rejects_pass_without_basis_before_execution(self):
        path = _write_notes({"standard": {"conclusion": "pass", "basis": "ok"},
                             "requirement": {"conclusion": "pass"}})
        with self.assertRaises(check_mod.CheckError) as caught:
            self._scope(path)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("lacks basis", caught.exception.facts["reason"])
        os.unlink(path)

    def test_scope_rejects_missing_notes_file_with_hint(self):
        with self.assertRaises(check_mod.CheckError) as caught:
            self._scope("/tmp/definitely-missing-review-notes.json")
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("unreadable", caught.exception.facts["reason"])


class FinishValidationTest(unittest.TestCase):
    def test_finish_refuses_pass_that_fails_validate(self):
        review = {"standard": {"conclusion": "pass", "basis": "spec"},
                  "requirement": {"conclusion": "pass", "basis": "prd"}}
        state = _state(internal_review=review)
        task = {"id": "t1", "plan": {"verifications": []}, "check_history": []}
        ctx = mock.Mock(root="/tmp/x")
        ctx.rule_version.return_value = "sha256:" + "d" * 64
        with mock.patch.object(check_mod.scope, "classify_candidates",
                               return_value={"buckets": {key: [] for key in "abcdef"},
                                             "candidates": [], "touch_paths": []}), \
                mock.patch.object(check_mod.scope, "external_changes", return_value=({}, [])), \
                mock.patch.object(check_mod.scope, "declaration_violations",
                                  return_value=([], {})), \
                mock.patch.object(check_mod, "_receipts", return_value=[]), \
                mock.patch.object(check_mod.fingerprint, "items", return_value=[]), \
                mock.patch.object(check_mod, "object_paths", return_value=[]), \
                mock.patch.object(check_mod, "_acceptance_results", return_value=[]), \
                mock.patch.object(check_mod, "tdd_scope", return_value=(False, None)), \
                mock.patch.object(check_mod, "validate_check_result",
                                  return_value=[{"field": "internal_review.requirement"}]):
            with self.assertRaises(check_mod.CheckError) as caught:
                check_mod.run_check_finish(ctx, task, state, [])
        self.assertEqual(caught.exception.code, "WF_CHECK_FAILED")
        self.assertTrue(caught.exception.facts["problems"])


if __name__ == "__main__":
    unittest.main()
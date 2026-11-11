"""A3：暂存报告按 reviewer 名产出，状态查询也必须按同一个名找。

历史缺陷：`review-context --as codex` 写的是 `round-N/review-codex.md`，而 `status_of_round`
按**声明槽位名**去找 `review-s1.md` → "已产出未导入"被报成 `missing`，人又得去当传声筒
（dogfood D3 的原始场景）。A1 之后查找按 `agent` 走，槽位只是位置；本用例锁住这条口径。

基线实测（8da2f23，同一夹具）：arrived=0、missing=['s1','s2']、两个槽位都 missing。
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

from wflib import records, review  # noqa: E402

ANCHOR = "sha256:" + "a" * 64


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)


class StagingLookupTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)
        self.staging = Path(self.root) / "staging" / "round-1"

    def tearDown(self):
        self._tmp.cleanup()

    def task(self):
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "slots": [{"slot": "s1"}, {"slot": "s2"}]}],
            "imported": [], "dispositions": []}}

    def status(self):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: os.path.join(self.root, "staging")):
            return review.status_of_round(self.ctx, self.task(), 1)

    def stage(self, agent, status="done"):
        self.staging.mkdir(parents=True, exist_ok=True)
        (self.staging / f"review-{agent}.md").write_text(
            f"<!-- wf-review-agent:v1 status={status} -->\n", encoding="utf-8")

    def test_fully_written_report_is_staged_not_missing(self):
        self.stage("codex", "done")
        facts = self.status()
        by_slot = {item["slot"]: item for item in facts["slots"]}
        self.assertEqual(by_slot["s1"]["state"], "staged")
        self.assertEqual(by_slot["s1"]["agent"], "codex")
        self.assertEqual(by_slot["s1"]["agent_status"], "done")
        self.assertTrue(by_slot["s1"]["staged_path"].endswith("review-codex.md"))
        self.assertEqual(by_slot["s2"]["state"], "missing")
        self.assertEqual(facts["arrived"], 1)
        self.assertEqual(facts["missing"], ["s2"])

    def test_in_progress_report_is_staged_with_its_own_status(self):
        self.stage("codex", "in-progress")
        facts = self.status()
        by_slot = {item["slot"]: item for item in facts["slots"]}
        self.assertEqual(by_slot["s1"]["state"], "staged")
        self.assertEqual(by_slot["s1"]["agent_status"], "in-progress")

    def test_empty_staging_is_missing(self):
        facts = self.status()
        self.assertEqual(facts["arrived"], 0)
        self.assertEqual(sorted(facts["missing"]), ["s1", "s2"])


if __name__ == "__main__":
    unittest.main()

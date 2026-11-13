"""A2：同一份报告只能被认领一次（`arrived` 不得虚增）。

历史缺陷（v15 实现里实测复现过、随后整批回退）：暂存发现逻辑只排除了声明槽位名，没排除
**已导入**的报告名 → 一份 `codex` 报告同时算 `imported(s1)` 与 `staged(s2)`，`arrived=2`、
`ready_to_decide=True`，AI 会重复导入同一份，而判定其实会因人数不足被拒。

当前实现由 `slot_assignment` 的身份去重从结构上消除：一个身份只占一个槽位、槽位数恒等于
声明数。本用例锁住这条不变量，防止"再增加一条发现路径"时重新引入。
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


def write_report(root, relative):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": [], "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


class ClaimOnceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def status(self, task):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: os.path.join(self.root, "staging")):
            return review.status_of_round(self.ctx, task, 1)

    def task(self, imported, declared=("s1", "s2")):
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "slots": [{"slot": name} for name in declared]}],
            "imported": list(imported), "dispositions": []}}

    def test_imported_report_is_not_claimed_again_as_staged(self):
        relative, digest = write_report(self.root, "review/round-1/review-codex.md")
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        (staging / "review-codex.md").write_text(
            "<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        entry = {"round": 1, "slot": "codex", "agent": "codex", "report_path": relative,
                 "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}
        facts = self.status(self.task([entry]))
        self.assertEqual(facts["required"], 2)
        self.assertEqual(facts["arrived"], 1)
        self.assertEqual(facts["missing"], ["s2"])
        self.assertFalse(facts["material_ready"])
        self.assertEqual([(slot["slot"], slot["state"]) for slot in facts["slots"]],
                         [("s1", "imported"), ("s2", "missing")])

    def test_slots_never_outnumber_declared(self):
        relative, digest = write_report(self.root, "review/round-1/review-codex.md")
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        (staging / "review-codex.md").write_text(
            "<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        entry = {"round": 1, "slot": "codex", "agent": "codex", "report_path": relative,
                 "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}
        facts = self.status(self.task([entry]))
        self.assertEqual(len(facts["slots"]), facts["required"])
        self.assertLessEqual(facts["arrived"], facts["required"])

    def test_two_distinct_reports_both_count(self):
        relative, digest = write_report(self.root, "review/round-1/review-pi.md")
        staging = Path(self.root) / "staging" / "round-1"
        staging.mkdir(parents=True)
        (staging / "review-zcode.md").write_text(
            "<!-- wf-review-agent:v1 status=done -->\n", encoding="utf-8")
        entry = {"round": 1, "slot": "pi", "agent": "pi", "report_path": relative,
                 "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}
        facts = self.status(self.task([entry]))
        self.assertEqual(facts["arrived"], 2)
        self.assertEqual(facts["missing"], [])
        self.assertEqual(sorted(facts["arrived_slots"]), ["s1", "s2"])


if __name__ == "__main__":
    unittest.main()

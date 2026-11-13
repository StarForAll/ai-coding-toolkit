"""A11（裁定：甲·维持现状）：恢复只在**受控写点被观察到**时结束豁免。

机制保证的是：「写点观察到恢复 → 该放行失效（`consumed`）」。
机制**不保证**：「恢复 → 期间没有写命令 → 再次损坏」这段窗口——那不是遗漏，是当前信任
模型的边界（要做强需要签名/外部见证，⑥ 已裁定不引入）。

本文件把这条边界写成可执行断言，防止以后有人把保证说大：
- 观察到恢复 → 放行记录被消费（带 `consumed_at`）；
- 文件被改写/读不到 → 不消费（也不把 IO 故障当成恢复）；
- 恢复后再损坏且期间无写点 → 放行仍然生效（**登记的残余风险**）。
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
DIGEST = "sha256:" + "b" * 64


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
            "findings": [{"id": "f1", "severity": "blocking"}], "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


def acceptance(digest):
    return {"round": 1, "slot": "s1", "report_digest": digest,
            "by": "human:test", "at": "2026-11-11T00:00:00.000000Z",
            "quote": "人确认这条证据不可核实、接受风险", "batch": "b1"}


class RecoveryBoundaryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def task(self):
        relative, digest = write_report(self.root, "review/round-1/review-s1.md")
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "slots": [{"slot": "s1"}]}],
            "imported": [{"round": 1, "slot": "s1", "agent": "pi", "report_path": relative,
                          "report_digest": digest, "anchor": {"check_anchor": ANCHOR}}],
            "unknown_acceptances": [acceptance(digest)],
            "dispositions": []}}

    def test_observed_recovery_consumes_the_release(self):
        task = self.task()
        consumed = review.consume_recovered(self.ctx, task)
        self.assertEqual(consumed, [{"round": 1, "slot": "s1",
                                     "report_digest": task["reviews"]["imported"][0]["report_digest"]}])
        record = task["reviews"]["unknown_acceptances"][0]
        self.assertTrue(record["consumed"])
        self.assertTrue(record["consumed_at"])
        self.assertEqual(review.active_acceptances(task), [])

    def test_rewritten_report_is_not_a_recovery(self):
        task = self.task()
        Path(self.root, "review/round-1/review-s1.md").write_text("改过", encoding="utf-8")
        self.assertEqual(review.consume_recovered(self.ctx, task), [])
        self.assertFalse(task["reviews"]["unknown_acceptances"][0].get("consumed"))

    def test_unreadable_report_is_not_a_recovery(self):
        task = self.task()
        path = Path(self.root, "review/round-1/review-s1.md")
        path.unlink()
        path.mkdir()
        self.assertEqual(review.consume_recovered(self.ctx, task), [])
        self.assertFalse(task["reviews"]["unknown_acceptances"][0].get("consumed"))

    def test_recovery_then_damage_without_a_write_point_is_the_registered_residual(self):
        """恢复 → 没有任何写命令 → 再次损坏：归档时观察到的是"坏"，旧放行仍然生效。"""
        task = self.task()
        imported = task["reviews"]["imported"][0]
        # ① 报告被删（进入不可核实）
        path = Path(self.root, "review/round-1/review-s1.md")
        original = path.read_text(encoding="utf-8")
        path.unlink()
        self.assertEqual(review.consume_recovered(self.ctx, task), [])
        # ② 恢复（但期间没有任何写命令可观察）
        path.write_text(original, encoding="utf-8")
        # ③ 再次损坏
        path.unlink()
        # ④ 归档前预检只能观察到"坏" → 不消费；旧放行仍生效（**这就是登记的残余风险**）
        self.assertEqual(review.consume_recovered(self.ctx, task), [])
        self.assertFalse(task["reviews"]["unknown_acceptances"][0].get("consumed"))
        facts = review.unverifiable_evidence(self.ctx, task)
        entry = next(item for item in facts if item["slot"] == "s1")
        self.assertTrue(entry["released"])
        self.assertEqual(entry["state"], "accepted-risk")
        self.assertEqual(entry["report_digest"], imported["report_digest"])


if __name__ == "__main__":
    unittest.main()

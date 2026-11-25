"""A12：放行记录（`unknown_acceptances`）必须进抽样事件池，并且能被事后核验。

backlog A12：`review-accept-unknown` 的决定文件由持写权会话提交，机制无法区分人与 AI；
阻断越强、伪造激励越强。裁定过的缓解有两条，本用例锁的两半都在：
1. **归档回显**：`acceptance_echo` 强制列出当前生效的放行（撤销/消费后不再列）；
2. **抽样池**：放行记录并入事实骨架的 `unverified`，事件 id 稳定为 `accept:<round>:<slot>`，
   可被抽样抽中、也可被 judgment 引用（`ref_ids` 与 `events_of` 共用同一处，避免"抽中了却
   补写不了"的历史缺陷）。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import attestation, authorize, judgments, review, sampling, scale  # noqa: E402


class QuoteMaskTest(unittest.TestCase):
    """人的原话入库必须是遮罩+截断摘要（授权/抽样/规模确认共用一处）。"""

    def test_mask_quote_redacts_and_truncates(self):
        text = authorize.mask_quote("Authorization: Bearer sk-live-AAAABBBB " + "x" * 600)
        self.assertNotIn("sk-live-AAAABBBB", text)
        self.assertIn("…<truncated>", text)

    def test_sampling_reviewed_masks_quote(self):
        task = {}
        state = sampling.mark_reviewed(task, quote="token = sk-live-AAAABBBB", attestation={})
        self.assertNotIn("sk-live-AAAABBBB", state["quote"])

    def test_scale_record_masks_quote(self):
        task = {}
        payload = scale.record(task, {"net": 1, "files": 1}, quote="password = hunter2")
        self.assertNotIn("hunter2", payload["quote"])

    def test_attestation_stamp_masks_quote(self):
        stamped = attestation.stamp({"by": "human:x", "at": "2026-11-25T00:00:00Z",
                                     "quote": "token = sk-live-AAAABBBB", "source": "user-declared"},
                                    "sha256:" + "a" * 64)
        self.assertNotIn("sk-live-AAAABBBB", stamped["quote"])
        self.assertEqual(stamped["attestation_digest"], "sha256:" + "a" * 64)

    def test_review_acceptance_quotes_are_masked(self):
        decision = {"by": "human:x", "at": "2026-11-25T00:00:00Z",
                    "quote": "token = sk-live-AAAABBBB", "source": "user-declared",
                    "residual_risk": "r", "round": 1, "task": "t1"}
        record, problems = review.single_reviewer_acceptance(decision, 1, "t1")
        self.assertEqual(problems, [])
        self.assertNotIn("sk-live-AAAABBBB", record["quote"])
        gap, problems = review.gap_acceptance({"by": "human:x", "at": "2026-11-25T00:00:00Z",
                                               "quote": "token = sk-live-AAAABBBB",
                                               "source": "user-declared", "round": 1,
                                               "task": "t1", "axes": ["range"]},
                                              ["range"], 1, "t1")
        self.assertEqual(problems, [])
        self.assertNotIn("sk-live-AAAABBBB", gap["quote"])

    def test_evaluate_attestation_is_committed(self):
        task = {}
        state = sampling.record_result(
            task, [{"class": "c", "event": "e"}],
            {"c:e": "ok", "__attestation__": {"by": "human:x",
                                               "attestation_digest": "sha256:" + "b" * 64}})
        self.assertEqual(state["evaluate_attestation"]["attestation_digest"],
                         "sha256:" + "b" * 64)


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)

    def rule_version(self):
        return "rules-v1"


def acceptance(round_no=1, slot="s1", **over):
    record = {"round": round_no, "slot": slot, "report_digest": "sha256:" + "d" * 64,
              "by": "human:xzc", "at": "2026-11-11T00:00:00Z",
              "quote": "人确认该报告不可核实、接受风险", "batch": "b1"}
    record.update(over)
    return record


def task_with(*records):
    return {"id": "t1", "phase": "finish", "reviews": {
        "unknown_acceptances": list(records), "imported": [], "dispositions": []}}


class AcceptanceSamplingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ctx = FakeCtx(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def skeleton(self, task):
        with mock.patch.object(judgments, "_unverified", return_value=[]), \
                mock.patch.object(judgments, "cumulative_facts", return_value={}):
            return judgments.skeleton(self.ctx, task)

    def test_release_record_enters_the_sampling_pool(self):
        facts = self.skeleton(task_with(acceptance()))
        self.assertEqual([item["id"] for item in facts["unverified"]], ["accept:1:s1"])
        pool = sampling.events_of(facts)
        self.assertIn("accept:1:s1", pool["未核实"])

    def test_picked_release_event_is_referenceable(self):
        facts = self.skeleton(task_with(acceptance()))
        self.assertIn("accept:1:s1", judgments.ref_ids(facts))
        picks = sampling.select("seed", {"未核实": ["accept:1:s1"]}, {})
        self.assertEqual(picks["picks"][0]["class"], "未核实")
        self.assertEqual(picks["picks"][0]["event"], "accept:1:s1")

    def test_revoked_and_consumed_releases_stay_auditable_but_not_echoed(self):
        task = task_with(acceptance(), acceptance(slot="s2", revoked=True),
                         acceptance(slot="s3", consumed=True))
        facts = self.skeleton(task)
        self.assertEqual(sorted(item["id"] for item in facts["unverified"]),
                         ["accept:1:s1", "accept:1:s2", "accept:1:s3"])   # 骨架里都留痕
        echo = review.acceptance_echo(task)
        self.assertEqual([item["slot"] for item in echo], ["s1"])          # 回显只列生效中的


if __name__ == "__main__":
    unittest.main()

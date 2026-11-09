"""判「沿用」/ 漂移位置 / 被驳回收口 三条机械规则（D1 采纳的 v42 独有概念）。

防的失败：判「沿用」只写一句"还能用"，不指明标准到底哪一处变了——事后无法复算它是基于哪个差异做的判断。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import judgments  # noqa: E402


def facts(drift=None, rejected=None):
    return {"drift_diffs": drift or [],
            "rejected": rejected or [],
            "findings": [], "verifications": [], "acceptance": [], "closures": [],
            "unaddressed_findings": [], "rejected_unresolved": []}


def entry(**overrides):
    base = {"kind": "沿用", "decision": "继续沿用", "basis": "标准只改了措辞", "outcome": "applied",
            "evidence_refs": []}
    base.update(overrides)
    return base


class ReuseNeedsDriftPositionTest(unittest.TestCase):
    def test_reuse_without_d_position_is_rejected(self):
        problems = judgments.validate(entry(), facts())
        self.assertTrue(any("沿用" in p["reason"] for p in problems), problems)

    def test_reuse_with_existing_position_passes(self):
        drift = [{"id": "d:assertions", "where": "assertions"}]
        problems = judgments.validate(entry(evidence_refs=["d:assertions"]), facts(drift))
        self.assertEqual(problems, [])

    def test_position_not_in_drift_is_rejected(self):
        drift = [{"id": "d:assertions", "where": "assertions"}]
        problems = judgments.validate(entry(evidence_refs=["d:paths"]), facts(drift))
        self.assertTrue(any("不在 drift_diffs" in p["reason"] for p in problems), problems)

    def test_other_kinds_do_not_need_a_d_position(self):
        problems = judgments.validate(entry(kind="关闭", evidence_refs=[]), facts())
        self.assertEqual([p for p in problems if "沿用" in p["reason"]], [])


class RejectedNeedsResolutionTest(unittest.TestCase):
    def test_rejected_finding_without_resolution_is_rejected(self):
        problems = judgments.validate(
            entry(kind="关闭", finding="f1", evidence_refs=[]),
            facts(rejected=[{"finding_id": "f1", "decision": "rejected"}]))
        self.assertTrue(any("resolved" in p["reason"] for p in problems), problems)

    def test_rejected_finding_with_resolution_passes(self):
        problems = judgments.validate(
            entry(kind="关闭", finding="f1", resolved_by="human:xzc", evidence_refs=[]),
            facts(rejected=[{"finding_id": "f1", "decision": "rejected"}]))
        self.assertEqual([p for p in problems if "resolved" in p["reason"]], [])

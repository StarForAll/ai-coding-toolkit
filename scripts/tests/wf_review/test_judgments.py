"""P3/§5：判断骨架、append-only、引用只认骨架 id、预览计数显式。

防的失败（dogfood）：69 个任务文件里 12 条"人决定"全是模型转录的 human:chat；
唯一那条 blocking 的 evidence 只写自由文本"PRD a5 未变"；收工时人看不到
"到底做了哪些判断、哪些是我没把握的"。这里锁四件事：骨架可重建、判断只增不撤、
引用不接受自由文本、预览把计数（含"不确定 0"）显式打出来。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import judgments  # noqa: E402


def task(judgments_list=None, dispositions=None):
    return {"id": "t1", "reviews": {
        "imported": [{"findings": [{"id": "f1", "severity": "blocking", "class": "behaviour"}]}],
        "dispositions": dispositions or []},
        "check": {"commands": [{"verification_id": "v1", "status": "passed"}]},
        "judgments": list(judgments_list or [])}


def base(**overrides):
    entry = {"kind": "关闭", "decision": "f1 已修", "basis": "v1 通过", "outcome": "applied",
             "evidence_refs": ["v:v1", "f:f1"]}
    entry.update(overrides)
    return entry


class SkeletonTest(unittest.TestCase):
    def test_findings_and_verifications_become_refs(self):
        ids = judgments.ref_ids(judgments.skeleton_ids(task()))
        self.assertIn("f:f1", ids)
        self.assertIn("v:v1", ids)

    def test_findings_survive_from_imported_reports(self):
        facts = judgments.skeleton_ids(task())
        self.assertEqual([item["id"] for item in facts["findings"]], ["f1"])
        self.assertEqual(facts["findings"][0]["severity"], "blocking")


class AppendOnlyTest(unittest.TestCase):
    def test_append_never_rewrites_history(self):
        record = task()
        first, problems = judgments.append(record, base())
        self.assertEqual(problems, [])
        second, problems = judgments.append(record, base(basis="改主意了", supersedes=first["id"]))
        self.assertEqual(problems, [])
        self.assertEqual(len(record["judgments"]), 2)          # 旧条目仍在
        self.assertEqual(record["judgments"][0]["basis"], "v1 通过")
        self.assertEqual(second["supersedes"], first["id"])

    def test_supersedes_must_point_to_existing_entry(self):
        _record, problems = judgments.append(task(), base(supersedes="j99"))
        self.assertTrue(any("supersedes" in item["reason"] for item in problems))

    def test_free_text_ref_is_rejected(self):
        _record, problems = judgments.append(task(), base(evidence_refs=["PRD a5 未变"]))
        self.assertTrue(any("骨架派生集合" in item["reason"] for item in problems))

    def test_escalated_needs_a_concrete_question(self):
        _record, problems = judgments.append(task(), base(outcome="escalated"))
        self.assertTrue(any("判断不了" in item["reason"] for item in problems))

    def test_kind_must_be_known(self):
        _record, problems = judgments.append(task(), base(kind="随便"))
        self.assertTrue(any("kind 非法" in item["reason"] for item in problems))


class PreviewTest(unittest.TestCase):
    def test_counts_are_explicit_including_zero_uncertain(self):
        record = task(judgments_list=[base(basis="v1 通过")])
        text = judgments.render_preview(record)
        self.assertIn("不确定 0", text)                        # 0 也要显示
        self.assertIn("判断清单（1 条", text)
        self.assertIn("[关闭]    1 条", text)

    def test_escalated_and_backfill_are_visible(self):
        record = task(judgments_list=[
            base(outcome="escalated", escalated_question="该子句业务上重要吗"),
            base(backfill=True, basis="补：抽样漏报")])
        text = judgments.render_preview(record)
        self.assertIn("需你复核 1 条", text)
        self.assertIn("该子句业务上重要吗", text)
        self.assertIn("[补]", text)


if __name__ == "__main__":
    unittest.main()


class JudgmentEvidenceRefTest(unittest.TestCase):
    """判断里的 `evidence_refs` 只能引用骨架 id（v42 §6 逐条补：不属骨架 id 即拒）。"""

    def test_unknown_ref_is_rejected(self):
        facts = judgments.skeleton_ids(task())
        problems = judgments.validate(base(evidence_refs=["v:not-in-skeleton"]), facts)
        self.assertTrue(problems)
        self.assertIn("骨架派生集合", str(problems))

    def test_known_refs_pass(self):
        facts = judgments.skeleton_ids(task())
        self.assertEqual(judgments.validate(base(), facts), [])


class JudgmentWaiverTest(unittest.TestCase):
    """豁免只能由人给出：`waived` 条目必须带 human 前缀的 waived_by。"""

    def test_waiver_needs_human(self):
        facts = judgments.skeleton_ids(task())
        problems = judgments.validate(
            base(waived_by="codex", decision="不修", evidence_refs=["v:v1"]), facts)
        self.assertTrue(problems, "非人豁免应被拒")
        self.assertIn("human", str(problems))

    def test_human_waiver_passes(self):
        facts = judgments.skeleton_ids(task())
        self.assertEqual(judgments.validate(
            base(waived_by="human:xzc", decision="不修", evidence_refs=["v:v1"]), facts), [])



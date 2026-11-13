"""A9：finding 的精确身份是 `(round, slot, finding_id)`，裸 `finding_id` 不是身份。

防的失败：第 1 轮 `s1` 报的 `f1` 被处置关闭后，第 2 轮新报的同名 `f1`（其实是新问题）
被同一条旧处置"顺带"关掉——关闭匹配按裸 id，于是新问题静默消失；提出者索引同样按裸 id，
不同槽位的同名问题会被合并成一个提出者。

历史歧义（同 id 出现在多轮/多槽位、处置没写 round+slot）**不关闭**，列入待裁。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

AXES = {name: "pass" for name in review.REVIEW_AXES}


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)


def write_report(root, round_no, slot, findings):
    relative = f"review/round-{round_no}/review-{slot}.md"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": round_no,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": "sha256:x"},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
            "scope-exceptions": [], "axes": dict(AXES),
            "findings": findings, "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False, indent=2) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


def task_with(root, rounds):
    """`rounds`: [(round, slot, findings)] → 导入记录都指向真实报告文件。"""
    imported = []
    for round_no, slot, findings in rounds:
        relative, digest = write_report(root, round_no, slot, findings)
        imported.append({"round": round_no, "slot": slot, "agent": slot,
                         "report_path": relative, "report_digest": digest,
                         "anchor": {"check_anchor": "sha256:x"}})
    return {"id": "t1", "reviews": {"imported": imported, "dispositions": []}}


BLOCKING = [{"id": "f1", "severity": "blocking", "assertion_ref": "a1"}]


class FindingIdentityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_old_disposition_does_not_close_a_new_finding_with_same_id(self):
        task = task_with(self.root, [(1, "s1", BLOCKING), (2, "s1", BLOCKING)])
        task["reviews"]["dispositions"] = [
            {"finding_id": "f1", "decision": "accepted", "reason": "第 1 轮已修",
             "recheck_by": "human:xzc", "round": 1, "slot": "s1"}]
        result = review.open_findings(self.ctx, task)
        self.assertEqual([(item["round"], item["slot"], item["finding_id"])
                          for item in result["blocking"]], [(2, "s1", "f1")])

    def test_ambiguous_bare_id_stays_open_and_is_listed(self):
        task = task_with(self.root, [(1, "s1", BLOCKING), (2, "s2", BLOCKING)])
        task["reviews"]["dispositions"] = [
            {"finding_id": "f1", "decision": "accepted", "reason": "已修", "recheck_by": "human:xzc"}]
        result = review.open_findings(self.ctx, task)
        self.assertEqual(len(result["blocking"]), 2)
        self.assertEqual(len(result["ambiguous"]), 1)
        self.assertEqual([(item["round"], item["slot"]) for item in result["ambiguous"][0]["candidates"]],
                         [(1, "s1"), (2, "s2")])

    def test_explicit_slot_targets_exactly_one_identity(self):
        task = task_with(self.root, [(1, "s1", BLOCKING), (2, "s1", BLOCKING)])
        task["reviews"]["dispositions"] = [
            {"finding_id": "f1", "decision": "accepted", "reason": "第 2 轮已修",
             "recheck_by": "human:xzc", "round": 2, "slot": "s1"}]
        result = review.open_findings(self.ctx, task)
        self.assertEqual([item["round"] for item in result["blocking"]], [1])
        self.assertEqual([item["round"] for item in result["closed"]], [2])

    def test_all_findings_closed_is_per_identity(self):
        task = task_with(self.root, [(1, "s1", BLOCKING), (2, "s1", BLOCKING)])
        task["reviews"]["dispositions"] = [
            {"finding_id": "f1", "decision": "accepted", "reason": "已修",
             "recheck_by": "human:xzc", "round": 1, "slot": "s1"}]
        closed = {(item["round"], item["slot"]): item["closed"]
                  for item in review.all_findings(self.ctx, task)}
        self.assertTrue(closed[(1, "s1")])
        self.assertFalse(closed[(2, "s1")])


class ProposerIdentityTest(unittest.TestCase):
    def test_proposers_are_indexed_by_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(Path(tmp), [(1, "s1", [{"id": "f1"}]), (2, "s2", [{"id": "f1"}])])
            proposers = review.proposers_from_history(FakeCtx(tmp), task)
        self.assertEqual(proposers[(1, "s1", "f1")], "s1")
        self.assertEqual(proposers[(2, "s2", "f1")], "s2")

    def test_ambiguous_disposition_needs_round_and_slot(self):
        proposers = {(1, "s1", "f1"): "zcode", (2, "s2", "f1"): "dsh"}
        problems = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "已修", "recheck_by": "human:x"}],
            proposers)
        self.assertEqual(len(problems), 1)
        self.assertIn("round+slot", problems[0]["reason"])
        self.assertEqual(len(problems[0]["candidates"]), 2)

    def test_self_check_uses_the_proposer_of_that_identity(self):
        proposers = {(1, "s1", "f1"): "zcode", (2, "s2", "f1"): "dsh"}
        # 复核人是 (2,s2) 的提出者 dsh：对 (1,s1) 不构成自证，对 (2,s2) 构成
        fine = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "已修",
              "recheck_by": "dsh", "round": 1, "slot": "s1"}], proposers)
        self.assertEqual(fine, [])
        self_check = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "已修",
              "recheck_by": "dsh", "round": 2, "slot": "s2"}], proposers)
        self.assertIn("不得自证", self_check[0]["reason"])


if __name__ == "__main__":
    unittest.main()

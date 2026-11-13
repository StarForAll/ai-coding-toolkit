"""A7：提出者从**重解析的报告**取，不从导入记录里的 `findings` 取。

防的失败：导入记录只存路径/摘要/锚点，从不保存 findings；`proposers_from_history` 却从
`imported[].findings` 读 → 提出者索引永远是空的，于是**跨轮**（第 1 轮提出、第 2 轮复核
关闭）的处置被判定"不属任何已导入报告"，真实修复后无法正常关闭（K4b 关闭链断裂）。
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


def task_with_rounds(root, rounds):
    """rounds: [(round, slot, findings)] → 导入记录（**不写 findings**，与真实记录同形）。"""
    imported = []
    for round_no, slot, findings in rounds:
        relative, digest = write_report(root, round_no, slot, findings)
        imported.append({"round": round_no, "slot": slot, "agent": slot,
                         "report_path": relative, "report_digest": digest,
                         "anchor": {"check_anchor": "sha256:x"}})
    return {"id": "t1", "reviews": {"imported": imported, "dispositions": []}}


class ProposerSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_proposers_come_from_reparsed_reports(self):
        task = task_with_rounds(self.root, [(1, "s1", [{"id": "f1"}])])
        self.assertNotIn("findings", task["reviews"]["imported"][0])   # 记录里本来就没有
        proposers = review.proposers_from_history(self.ctx, task)
        self.assertEqual(proposers[(1, "s1", "f1")], "s1")

    def test_cross_round_finding_keeps_its_proposer(self):
        task = task_with_rounds(self.root, [(1, "zcode", [{"id": "f1"}]),
                                            (2, "dsh", [{"id": "f2"}])])
        proposers = review.proposers_from_history(self.ctx, task)
        self.assertEqual(proposers[(1, "zcode", "f1")], "zcode")
        self.assertEqual(proposers[(2, "dsh", "f2")], "dsh")

    def test_previous_round_close_is_accepted(self):
        task = task_with_rounds(self.root, [(1, "zcode", [{"id": "f1"}]),
                                            (2, "dsh", [{"id": "f2"}])])
        proposers = review.proposers_from_history(self.ctx, task)
        problems = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "第 2 轮复核通过",
              "recheck_by": "human:xzc", "round": 1, "slot": "zcode"}], proposers)
        self.assertEqual(problems, [])

    def test_self_closure_of_previous_round_is_still_rejected(self):
        task = task_with_rounds(self.root, [(1, "zcode", [{"id": "f1"}])])
        proposers = review.proposers_from_history(self.ctx, task)
        problems = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "自己复核",
              "recheck_by": "zcode", "round": 1, "slot": "zcode"}], proposers)
        self.assertIn("不得自证", problems[0]["reason"])

    def test_rewritten_report_contributes_no_proposer(self):
        task = task_with_rounds(self.root, [(1, "zcode", [{"id": "f1"}])])
        Path(self.root, "review/round-1/review-zcode.md").write_text("改过", encoding="utf-8")
        self.assertEqual(review.proposers_from_history(self.ctx, task), {})


if __name__ == "__main__":
    unittest.main()

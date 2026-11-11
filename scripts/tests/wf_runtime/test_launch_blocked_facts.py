"""B3：`blocked` 是组标签，不能遮住它概括的事实行。

历史缺陷：`launch_facts` 算了 `review_report_problems` 与 `review_eligibility`，却只留下
`blocked` 里的 token（report_invalid / anchor_stale / material_missing /
insufficient_reviewers / implementer_overlap）。人看到 `anchor_stale` 不知道是**哪一份**
报告的锚点失效，看到 `insufficient_reviewers` 也不知道差在哪。

现在每个 launch 条目在 `blocked` 旁边并排给出 `problems`（报告/锚点问题）与
`eligibility`（人数/异种/实施者重叠的提示），标签与事实同屏。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import gates, records, review  # noqa: E402

SAVED = "sha256:" + "a" * 64
DRIFT = "sha256:" + "b" * 64


class FakeCtx:
    def __init__(self, root):
        self.root = str(root)

    def rule_version(self):
        return "rules-v1"


def write_report(root, slot):
    relative = f"review/round-1/review-{slot}.md"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": SAVED},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**",
                               ".wf/tasks/**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": [], "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


class BlockedFactsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def task(self, agents, implementation="dsh", declared=2):
        imported = []
        for agent in agents:
            relative, digest = write_report(self.root, agent)
            imported.append({"round": 1, "slot": agent, "agent": agent,
                             "report_path": relative, "report_digest": digest,
                             "anchor": {"check_id": "c1", "check_anchor": SAVED}})
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "implementation_cli": implementation,
                          "slots": [{"slot": f"s{i + 1}"} for i in range(declared)]}],
            "imported": imported, "dispositions": []}}

    def facts(self, task, anchor=SAVED):
        with mock.patch.object(review, "_current_anchor", return_value=(anchor, {})), \
                mock.patch.object(gates, "check_result_problems", return_value=[]):
            return review.launch_facts(self.ctx, task)[0]

    def test_anchor_stale_token_comes_with_the_facts(self):
        entry = self.facts(self.task(["pi", "zcode"]), anchor=DRIFT)
        self.assertIn("anchor_stale", entry["blocked"])
        self.assertTrue(any("anchor does not match" in item["reason"]
                            for item in entry["problems"]), entry["problems"])
        self.assertEqual({item["slot"] for item in entry["problems"]}, {"pi", "zcode"})

    def test_eligibility_tokens_come_with_reasons(self):
        entry = self.facts(self.task(["codex"], implementation="codex", declared=1))
        self.assertIn("insufficient_reviewers", entry["blocked"])
        self.assertIn("implementer_overlap", entry["blocked"])
        reasons = [item["reason"] for item in entry["eligibility"]["problems"]]
        self.assertTrue(any("人数不合格" in reason for reason in reasons), reasons)
        self.assertTrue(any("重叠" in reason for reason in reasons), reasons)

    def test_clean_round_has_empty_fact_rows(self):
        entry = self.facts(self.task(["pi", "zcode"]))
        self.assertEqual(entry["blocked"], [])
        self.assertEqual(entry["problems"], [])
        self.assertEqual(entry["eligibility"]["problems"], [])


if __name__ == "__main__":
    unittest.main()

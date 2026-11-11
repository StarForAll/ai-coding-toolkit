"""B1：材料事实与判定资格分列——`status` 不再承诺"可判"。

历史缺陷：`ready_to_decide = 声明非空 and 无 missing`，只看材料在不在。单 provider
（`slots` 只声明 1 个）或审查 CLI 与实施 CLI 重叠时，它照样返回 True 并让 CLI 说
"review-decide 可判"，而 `review-decide` 用 `review_eligibility` 一定拒绝（实测）。

现在 `status` 只报两件事：
- `material_ready`：每份声明材料都到位且当前可用（无 missing / stale / unreadable）；
- `eligibility`：与 `review-decide` **同一个函数**给出的资格提示（人数/异种/实施者重叠）。
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


def write_report(root, round_no, slot):
    relative = f"review/round-{round_no}/review-{slot}.md"
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": round_no,
            "review-time": "2026-11-11T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"],
            "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**"],
            "scope-exceptions": [], "axes": {name: "pass" for name in review.REVIEW_AXES},
            "findings": [], "verdict": "pass"}
    path.write_text(review.REPORT_MARKER + "\n\n```json\n"
                    + json.dumps(body, ensure_ascii=False) + "\n```\n", encoding="utf-8")
    return relative, records.file_digest(path)


class MaterialVsEligibilityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ctx = FakeCtx(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def make_task(self, slots, agents, implementation="dsh"):
        imported = []
        for agent in agents:
            relative, digest = write_report(self.root, 1, agent)
            imported.append({"round": 1, "slot": agent, "agent": agent,
                             "report_path": relative, "report_digest": digest,
                             "anchor": {"check_anchor": ANCHOR}})
        return {"id": "t1", "reviews": {
            "launches": [{"round": 1, "implementation_cli": implementation,
                          "slots": [{"slot": name} for name in slots]}],
            "imported": imported, "dispositions": []}}

    def status(self, task):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "staging_root",
                                  lambda _ctx, _task: os.path.join(self.root, "staging")):
            return review.status_of_round(self.ctx, task, 1)

    def test_single_provider_is_material_ready_but_ineligible(self):
        facts = self.status(self.make_task(["s1"], ["codex"], implementation="codex"))
        self.assertTrue(facts["material_ready"])
        reasons = [problem["reason"] for problem in facts["eligibility"]["problems"]]
        self.assertTrue(any("人数不合格" in reason for reason in reasons), reasons)
        self.assertTrue(any("重叠" in reason for reason in reasons), reasons)
        self.assertNotIn("ready_to_decide", facts)     # 混同口径已移除

    def test_two_distinct_reviewers_pass_eligibility(self):
        facts = self.status(self.make_task(["s1", "s2"], ["pi", "zcode"], implementation="dsh"))
        self.assertTrue(facts["material_ready"])
        self.assertEqual(facts["eligibility"]["problems"], [])

    def test_stale_material_is_not_ready(self):
        task = self.make_task(["s1", "s2"], ["pi", "zcode"])
        Path(self.root, "review/round-1/review-pi.md").write_text("改过", encoding="utf-8")
        facts = self.status(task)
        self.assertFalse(facts["material_ready"])
        self.assertEqual(facts["stale"], ["s1"])

    def test_cli_never_says_can_decide(self):
        source = (REPO / "docs" / "workflows" / "wf" / "payload" / "lib" / "wflib"
                  / "cli.py").read_text(encoding="utf-8")
        start = source.index("def cmd_review_status")
        body = source[start:source.index("\ndef ", start + 10)]
        self.assertNotIn("可判", body)
        self.assertNotIn("ready_to_decide", body)


if __name__ == "__main__":
    unittest.main()

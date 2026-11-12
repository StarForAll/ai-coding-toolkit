"""`broken-reference` 豁免按精确身份匹配（A9 的相邻面）。

缺陷：`broken_reference_problems` 把"声明"与"人复核"按**裸 finding_id** 配对。同一轮两个
槽位都报了 `f1`（两个不同问题）时，只要为人复核其中一条，另一条也被顺带豁免——豁免面
被悄悄放大。关闭链（A9）已经按 `(round, slot, finding_id)` 精确匹配，豁免却还是裸 id。

现在两边同一口径：`decide` 把条目上的 round/slot 补进 lifted，匹配走 `disposition_keys`
（显式 round+slot 精确命中；只写 finding_id 且唯命中则兼容；命中多条按歧义处理，不豁免）。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402


def lifted(round_no, slot, finding="f1"):
    return {"finding": finding, "assertion_ref": ".wf/spec/x.md#c1", "rule": ".wf/spec/x.md",
            "round": round_no, "slot": slot}


def human(round_no=None, slot=None, finding="f1"):
    item = {"finding_id": finding, "decision": "accepted", "reason": "人看过旧规则",
            "recheck_by": "human:xzc"}
    if round_no is not None:
        item["round"] = round_no
    if slot is not None:
        item["slot"] = slot
    return item


class BrokenReferenceIdentityTest(unittest.TestCase):
    def test_one_human_recheck_does_not_excuse_another_slots_finding(self):
        problems = review.broken_reference_problems(
            [lifted(1, "s1"), lifted(1, "s2")], [human(1, "s1")])
        self.assertEqual([(item["round"], item["slot"]) for item in problems], [(1, "s2")])
        self.assertIn("round", problems[0]["exits"][1])

    def test_explicit_identity_matches_exactly(self):
        problems = review.broken_reference_problems(
            [lifted(1, "s1"), lifted(1, "s2")], [human(1, "s2")])
        self.assertEqual([(item["round"], item["slot"]) for item in problems], [(1, "s1")])

    def test_bare_id_with_one_candidate_still_matches(self):
        # 兼容：只有一条同 id 的 finding 时，旧写法（不写 round+slot）仍然有效
        self.assertEqual(review.broken_reference_problems([lifted(1, "s1")], [human()]), [])

    def test_bare_id_with_two_candidates_is_ambiguous_and_excuses_nothing(self):
        problems = review.broken_reference_problems(
            [lifted(1, "s1"), lifted(1, "s2")], [human()])
        self.assertEqual(len(problems), 2)          # 两条都不算被豁免
        self.assertTrue(all("human:" in item["reason"] for item in problems))

    def test_non_human_recheck_never_counts(self):
        item = human(1, "s1")
        item["recheck_by"] = "codex"
        problems = review.broken_reference_problems([lifted(1, "s1")], [item])
        self.assertEqual(len(problems), 1)

    def test_no_declaration_means_no_problem(self):
        self.assertEqual(review.broken_reference_problems([], [human()]), [])


if __name__ == "__main__":
    unittest.main()

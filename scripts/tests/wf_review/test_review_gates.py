"""P2/K3b·K4b·K4c：引用属当前集合、规则不得自证、关闭不得自证、锚点差异可列出。

防的失败（都实际发生过或可具体推演）：
- 唯一那条 blocking 的 evidence 只写了自由文本「PRD a5 未变」（4.2 反例）→ 引用必须是集合内的 id；
- 第 5 轮 pass 后改代码、第 6 轮靠临时发明 `review-reauthorize` 续跑（4.7 反例）→ 标准变了要能被指出差异；
- 提出者自己复核自己的 finding（K4b）→ 复核人必须不是提出者。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "新项目开发工作流" / "payload" / "lib"))

from wflib import review  # noqa: E402


class AssertionRefTest(unittest.TestCase):
    INDEX = {"a1": "acceptance", "v1": "verification", ".wf/spec/x.md": "spec-rule",
             ".wf/spec/x.md#c1": "spec-clause"}

    def test_known_refs_pass(self):
        for ref in ("a1", "v1", ".wf/spec/x.md", ".wf/spec/x.md#c1"):
            self.assertIsNone(review.assertion_ref_problem(ref, self.INDEX, {}), ref)

    def test_unknown_ref_is_rejected_with_known_set(self):
        problem = review.assertion_ref_problem("a9", self.INDEX, {})
        self.assertEqual(problem["reason"], "assertion_ref 不属于当前批准集合")
        self.assertIn("a1", problem["known"])

    def test_rule_changed_in_this_task_cannot_be_a_basis(self):
        changed = {".wf/spec/x.md": {"curation_digest": "sha256:old", "current_digest": "sha256:new"}}
        problem = review.assertion_ref_problem(".wf/spec/x.md#c1", self.INDEX, changed)
        self.assertIn("规则不得自证", problem["reason"])
        self.assertIn("changed_rule", problem)

    def test_broken_reference_declaration_lifts_the_ban(self):
        changed = {".wf/spec/x.md": {"curation_digest": "sha256:old", "current_digest": "sha256:new"}}
        self.assertIsNone(
            review.assertion_ref_problem(".wf/spec/x.md", self.INDEX, changed, "broken-reference"))


class DispositionTest(unittest.TestCase):
    PROPOSERS = {"f1": "zcode", "f2": "dsh"}

    def test_close_by_proposer_is_rejected(self):
        problems = review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "已修", "recheck_by": "zcode"}],
            self.PROPOSERS)
        self.assertEqual(len(problems), 1)
        self.assertIn("不得自证", problems[0]["reason"])

    def test_close_by_another_reviewer_passes(self):
        self.assertEqual(review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "已修", "recheck_by": "dsh"}],
            self.PROPOSERS), [])

    def test_missing_rechecker_and_bad_decision_are_reported(self):
        problems = review.dispositions_problems(
            [{"finding_id": "f2", "decision": "closed", "reason": ""}], self.PROPOSERS)
        reasons = " ".join(item["reason"] for item in problems)
        self.assertIn("accepted|rejected|amended", reasons)
        self.assertIn("non-empty reason", reasons)
        self.assertIn("recheck_by", reasons)

    def test_human_recheck_is_allowed(self):
        self.assertEqual(review.dispositions_problems(
            [{"finding_id": "f1", "decision": "accepted", "reason": "人确认", "recheck_by": "human:xzc"}],
            self.PROPOSERS), [])


class AnchorDriftTest(unittest.TestCase):
    def test_parts_diff_lists_only_changed_keys(self):
        saved = {"content_digest": "sha256:a", "assertions_digest": "sha256:b", "plan_version": "p1"}
        current = {"content_digest": "sha256:a", "assertions_digest": "sha256:c", "plan_version": "p1"}
        diffs = review.anchor_drift(saved, current)
        self.assertEqual([item["where"] for item in diffs], ["assertions_digest"])
        self.assertEqual(diffs[0]["id"], "d:assertions_digest")

    def test_missing_parts_means_diff_unavailable(self):
        self.assertIsNone(review.anchor_drift(None, {"content_digest": "sha256:a"}))


class BrokenReferenceExemptionTest(unittest.TestCase):
    """`check_fix_kind=broken-reference` 的豁免 = 声明 + 人复核（2026-11-09 人裁 B）。

    防的失败：把"语义变化"声明成"机械纠错"绕过 K4c（v42 风险表已列出该滥用面）。
    框架无法验证旧 check 原文，所以用"必须有人复核过"把声明变成可审计事实。
    """

    LIFTED = [{"finding": "f1", "assertion_ref": ".wf/spec/x.md#c1", "rule": ".wf/spec/x.md"}]

    def test_without_human_recheck_is_rejected(self):
        problems = review.broken_reference_problems(
            self.LIFTED, [{"finding_id": "f1", "decision": "accepted", "reason": "已修", "recheck_by": "zcode"}])
        self.assertEqual(len(problems), 1)
        self.assertIn("需人复核", problems[0]["reason"])

    def test_human_recheck_lifts_it(self):
        self.assertEqual(review.broken_reference_problems(
            self.LIFTED, [{"finding_id": "f1", "decision": "accepted", "reason": "人确认纠错",
                           "recheck_by": "human:xzc"}]), [])

    def test_no_declaration_needs_no_human(self):
        self.assertEqual(review.broken_reference_problems([], []), [])


if __name__ == "__main__":
    unittest.main()

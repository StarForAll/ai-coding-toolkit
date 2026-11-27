"""决定取值域的归一语义（十轮自审查）：`canonical` 只归一**同义写法**，不把语义不同的取值折叠。

历史缺陷：实现一律返回登记表首项，于是 `failed → passed`、`keep → commit`——
人工验收的失败结论被当成通过（check 的 manual 证据核对），spec 核实的失败结论也不进 unresolved。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import decisions  # noqa: E402


class CanonicalTest(unittest.TestCase):
    def test_distinct_values_are_not_collapsed(self):
        self.assertEqual(decisions.canonical("acceptance_conclusion", "failed"), "failed")
        self.assertEqual(decisions.canonical("acceptance_conclusion", "passed"), "passed")
        self.assertEqual(decisions.canonical("acceptance_conclusion", "pending"), "pending")
        self.assertEqual(decisions.canonical("stop_choice", "keep"), "keep")
        self.assertEqual(decisions.canonical("stop_choice", "commit"), "commit")
        self.assertEqual(decisions.canonical("debug_ruling", "不同问题"), "不同问题")

    def test_aliases_normalise_to_one_value(self):
        self.assertEqual(decisions.canonical("plan_approval", "批准"), "approve")
        self.assertEqual(decisions.canonical("archive_finish", "pass"), "finish")
        self.assertEqual(decisions.canonical("action_result", "完成"), "done")
        self.assertEqual(decisions.canonical("action_result", "不适用"), "waived")

    def test_unregistered_values_are_none(self):
        for operation in decisions.registered():
            self.assertIsNone(decisions.canonical(operation, "bogus-value"))

    def test_every_alias_group_is_registered(self):
        for operation, aliases in decisions.ALIAS_GROUPS.items():
            values = decisions.registered()[operation]
            for alias, target in aliases.items():
                self.assertIn(alias, values)
                self.assertIn(target, values)
                self.assertEqual(decisions.canonical(operation, alias), target)


class SubjectTokensTest(unittest.TestCase):
    """`subject` 覆盖判定的唯一实现：四个入口都委托它（此前有四份实现）。"""

    def test_tokens_accept_list_and_string(self):
        self.assertEqual(decisions.subject_tokens(["a1", "b 2"]), ["a1", "b", "2"])
        self.assertEqual(decisions.subject_tokens("确认 a1 通过"), ["确认", "a1", "通过"])
        self.assertEqual(decisions.subject_tokens(None), [])

    def test_whole_word_only(self):
        self.assertTrue(decisions.subject_mentions(["api-docs"], "api-docs"))
        self.assertFalse(decisions.subject_mentions(["api-docs"], "api"))
        self.assertTrue(decisions.subject_mentions("write 实现", "write"))

    def test_punctuation_and_cjk_separators(self):
        self.assertTrue(decisions.subject_mentions("a1，b2；c3、d4|e5", "c3"))
        self.assertTrue(decisions.subject_mentions("a1，b2", "b2"))


if __name__ == "__main__":
    unittest.main()

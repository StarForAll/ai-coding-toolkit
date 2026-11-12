"""P2-7：`Decision.choice` 的取值域统一登记（实现稿 §2.3.11 ①）。

历史状态：取值以字面量散在七处（`tasks.APPROVE_CHOICES`、`cmd_archive` 的 finish 集合、
`check.EXTERNAL_CHECKED_CHOICES`、`debug-ruling` 的两个中文值、`commit_grants`、
`stop` 的四值、验收结论的三值），既没有单一来源，也无法回答「加个近义词算不算改语义」。
机制稿 §1.1 只定 `Decision` 的结构，取值域按操作登记在实现稿 §2.3。

现在只有一处登记表（`wflib/decisions.py`），调用点一律 `accepts`/`canonical`，
**未登记的同义词被拒**（`WF_SEMANTIC_DECISION`），不许就地放宽。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check as check_mod  # noqa: E402
from wflib import decisions, tasks as tasks_mod  # noqa: E402

EXPECTED = {
    "plan_approval", "mechanical_revision", "replan", "archive_finish", "stop_choice",
    "commit_grant", "external_checked", "debug_ruling", "acceptance_conclusion",
}


class DecisionDomainTest(unittest.TestCase):
    def test_all_operations_are_registered(self):
        self.assertTrue(EXPECTED <= set(decisions.registered()))

    def test_every_domain_has_a_canonical_value(self):
        for name, values in decisions.DOMAINS.items():
            with self.subTest(domain=name):
                self.assertTrue(values, f"{name} 不能为空")
                self.assertTrue(decisions.accepts(name, values[0]))
                self.assertEqual(decisions.canonical(name, values[0]), values[0])

    def test_unregistered_synonym_is_rejected(self):
        """新增同义词必须回实现稿登记；未登记的一律不认。"""
        for name, bogus in (("plan_approval", "approved"),
                            ("archive_finish", "done"),
                            ("external_checked", "looks-fine"),
                            ("debug_ruling", "同一问题重复"),
                            ("acceptance_conclusion", "ok"),
                            ("stop_choice", "stash")):
            with self.subTest(domain=name):
                self.assertFalse(decisions.accepts(name, bogus))
                self.assertIsNone(decisions.canonical(name, bogus))

    def test_unknown_domain_raises_instead_of_allowing_everything(self):
        with self.assertRaises(decisions.UnknownDomain):
            decisions.accepts("no-such-domain", "anything")

    def test_call_sites_share_the_registry(self):
        """三处历史字面量必须与登记表同源（不是各留一份）。"""
        self.assertEqual(tuple(tasks_mod.APPROVE_CHOICES),
                         tuple(decisions.domain("plan_approval")))
        self.assertEqual(tuple(check_mod.EXTERNAL_CHECKED_CHOICES),
                         tuple(decisions.domain("external_checked")))
        self.assertEqual(tasks_mod.MECHANICAL_REVISION,
                         decisions.domain("mechanical_revision")[0])


if __name__ == "__main__":
    unittest.main()

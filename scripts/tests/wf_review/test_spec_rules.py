"""spec 规则元数据的机械校验（v42 §6 逐条补：clauses 只增不改、deprecated_summary 长度）。

防的失败：`clauses` 被原地改字当"没改过"，或停用条目只写一句"停用"导致后人不知道被什么取代。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import spec  # noqa: E402


def errors(md):
    """`validate_metadata` 返回 (errors, warnings, infos) 三元组，测试只看 errors。"""
    return spec.validate_metadata(md)[0]


def metadata(**overrides):
    base = {"schema_version": 1, "status": "active", "author": "human",
            "verified_at": "2026-11-09", "counterexample": "反例"}
    base.update(overrides)
    return base


class DeprecatedSummaryTest(unittest.TestCase):
    def test_missing_summary_is_rejected(self):
        problems = errors(metadata(clauses=[
            {"id": "c1", "status": "deprecated", "statement": "旧条件"}]))
        self.assertTrue(any("deprecated_summary" in p for p in problems), problems)

    def test_over_eighty_chars_is_rejected(self):
        problems = errors(metadata(clauses=[
            {"id": "c1", "status": "deprecated", "statement": "旧条件",
             "deprecated_summary": "长" * 81}]))
        self.assertTrue(any("80" in p for p in problems), problems)

    def test_eighty_chars_is_accepted(self):
        problems = errors(metadata(clauses=[
            {"id": "c1", "status": "deprecated", "statement": "旧条件",
             "deprecated_summary": "长" * 80}]))
        self.assertEqual([p for p in problems if "deprecated_summary" in p], [])


class ClauseStatusTest(unittest.TestCase):
    def test_unknown_status_is_rejected(self):
        problems = errors(metadata(clauses=[
            {"id": "c1", "status": "改为停用", "statement": "条件"}]))
        self.assertTrue(problems)

    def test_duplicate_clause_id_is_rejected(self):
        problems = errors(metadata(clauses=[
            {"id": "c1", "status": "active", "statement": "一"},
            {"id": "c1", "status": "active", "statement": "二"}]))
        self.assertTrue(any("c1" in p for p in problems), problems)


class RuleDigestTest(unittest.TestCase):
    def test_digest_ignores_formatting_and_deprecated(self):
        active = metadata(clauses=[{"id": "c1", "status": "active", "statement": "条件一"}])
        with_deprecated = metadata(clauses=[
            {"id": "c1", "status": "active", "statement": "条件一"},
            {"id": "c0", "status": "deprecated", "statement": "旧", "deprecated_summary": "被 c1 取代"}])
        self.assertEqual(spec.rule_digest(active), spec.rule_digest(with_deprecated))

    def test_changing_active_statement_changes_digest(self):
        before = metadata(clauses=[{"id": "c1", "status": "active", "statement": "条件一"}])
        after = metadata(clauses=[{"id": "c1", "status": "active", "statement": "条件一（原地改字）"}])
        self.assertNotEqual(spec.rule_digest(before), spec.rule_digest(after))

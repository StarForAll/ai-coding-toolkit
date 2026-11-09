"""P2/K3b：断言面摘要只算实质字段，且能区分"改排版"与"改标准"。

防的失败：dogfood 里"锚点漏控制面"（B3）与"标准变了报告还能 pass"（5.4 反例）——
整文件摘要会把排版也算成标准变化（真假阳性并存），而漏掉"验收项/验证命令变了但文件没变"。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "新项目开发工作流" / "payload" / "lib"))

from wflib import spec  # noqa: E402


class RuleDigestTest(unittest.TestCase):
    def _metadata(self, **extra):
        data = {"schema_version": 1, "status": "active", "author": "ai",
                "verified_at": "2026-11-01", "counterexample": "反例",
                "paths": ["src/**"], "check": "pytest -q tests/test_a.py",
                "clauses": [{"id": "c1", "status": "active", "statement": "条件一"}]}
        data.update(extra)
        return data

    def test_digest_ignores_formatting_and_deprecated_clauses(self):
        base = self._metadata()
        formatted = self._metadata(clauses=[
            {"id": "c1", "status": "active", "statement": "条件一"},
            {"id": "c0", "status": "deprecated", "deprecated_summary": "旧条件一句；停用一句"},
        ])
        self.assertEqual(spec.rule_digest(base), spec.rule_digest(formatted))

    def test_digest_changes_when_check_or_active_clause_changes(self):
        base = spec.rule_digest(self._metadata())
        self.assertNotEqual(base, spec.rule_digest(self._metadata(check="pytest -q tests/test_b.py")))
        self.assertNotEqual(base, spec.rule_digest(self._metadata(clauses=[
            {"id": "c2", "status": "active", "statement": "条件一（改）"}])))

    def test_rule_without_substantive_fields_has_no_digest(self):
        metadata = self._metadata()
        metadata.pop("check")
        metadata["clauses"] = []
        self.assertIsNone(spec.rule_digest(metadata))

    def test_clause_schema_rejects_in_place_edit_and_bad_summary(self):
        problems, _paths, _path_problems = spec.validate_metadata(self._metadata(clauses=[
            {"id": "c1", "status": "active", "statement": "一"},
            {"id": "c1", "status": "active", "statement": "二"}]))
        self.assertTrue(any("重复" in item for item in problems))
        problems, _p, _pp = spec.validate_metadata(self._metadata(clauses=[
            {"id": "c2", "status": "deprecated"}]))
        self.assertTrue(any("deprecated_summary" in item for item in problems))
        problems, _p, _pp = spec.validate_metadata(self._metadata(clauses=[
            {"id": "c3", "status": "deprecated", "deprecated_summary": "x" * 81}]))
        self.assertTrue(any("80" in item for item in problems))


if __name__ == "__main__":
    unittest.main()

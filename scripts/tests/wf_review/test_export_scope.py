"""D4：外发授权绑定本次范围；仓库规则提交按实际路径核对覆盖。

防的失败（dogfood）：
- `review-launch` 只核 `authorization-export.json` **存在**，旧授权可被复用到另一个任务或新增材料类；
- 归档提交守卫对仓库级规则文件只核"有过 repo_rules 类确认"，不核本次提交的实际路径。

断言：
1. 外发确认必须写明任务与材料类集合，否则记录被拒；
2. 入库副本带 `scope_digest`（任务 + 材料类），不同任务/不同材料类都不匹配；
3. 同任务同材料类可复用（设计稿 §4.1：同范围授权持续有效）；
4. `repo_rules` 的 `covers` 只认覆盖本次路径的确认。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import authorize, records  # noqa: E402

MATERIALS = ["diff", "requirement", "test_results"]


class ExportScopeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.task_dir = Path(self._tmp.name) / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def decision(self, **overrides):
        payload = {"choice": "export", "task": "t1", "materials": list(MATERIALS),
                   "by": "human:xzc", "at": "2026-11-12T00:00:00Z",
                   "quote": "同意把本任务的 diff/PRD/测试结果发给两个 reviewer",
                   "source": "user-declared"}
        payload.update(overrides)
        return payload

    def test_decision_must_name_task_and_materials(self):
        problems = authorize.export_decision_problems({"choice": "export"})
        self.assertEqual({item["field"] for item in problems}, {"task", "materials"})
        problems = authorize.export_decision_problems(self.decision(materials=["everything"]))
        self.assertTrue(any(item.get("unknown") for item in problems))
        self.assertEqual(authorize.export_decision_problems(self.decision()), [])

    def test_recorded_authorization_binds_task_and_materials(self):
        authorize.record_authorization(self.task_dir, "export", self.decision())
        stored = records.load_json(authorize.authorization_path(self.task_dir, "export"))
        self.assertTrue(stored["scope_digest"].startswith("sha256:"))
        # 范围元数据本身不入库（只保留摘要），但 digest 足以复算
        self.assertNotIn("materials", stored)
        self.assertEqual(authorize.export_scope_problems(self.task_dir, "t1", MATERIALS), [])

    def test_reuse_across_tasks_or_material_sets_is_refused(self):
        authorize.record_authorization(self.task_dir, "export", self.decision())
        problems = authorize.export_scope_problems(self.task_dir, "t2", MATERIALS)
        self.assertTrue(problems)
        problems = authorize.export_scope_problems(self.task_dir, "t1", ["diff", "requirement"])
        self.assertTrue(problems)
        problems = authorize.export_scope_problems(self.task_dir, "t1", MATERIALS + ["logs"])
        self.assertTrue(problems)

    def test_record_authorization_rejects_incomplete_export(self):
        with self.assertRaises(ValueError):
            authorize.record_authorization(self.task_dir, "export",
                                           {"choice": "export", "quote": "x",
                                            "by": "human:xzc", "at": "2026-11-12T00:00:00Z",
                                            "source": "user-declared"})

    def test_legacy_authorization_without_scope_is_refused(self):
        records.write_json(authorize.authorization_path(self.task_dir, "export"),
                           {"action": "export", "original_digest": "sha256:x"})
        problems = authorize.export_scope_problems(self.task_dir, "t1", MATERIALS)
        self.assertTrue(any("scope_digest" in item["reason"] for item in problems))


class RepoRuleCoverageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "a.py").write_text("x\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("rules\n", encoding="utf-8")
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def record(self, paths):
        authorize.record_authorization(self.task_dir, "repo_rules",
                                       {"choice": "repo_rules", "paths": paths,
                                        "by": "human:xzc", "at": "2026-11-12T00:00:00Z",
                                        "quote": "同意改 AGENTS.md 的这一段",
                                        "source": "user-declared"})

    def test_covers_uses_the_actual_paths(self):
        self.record(["AGENTS.md"])
        covered, uncovered = authorize.covers(self.task_dir, "repo_rules",
                                              ["AGENTS.md"], root=self.root)
        self.assertTrue(covered)
        self.assertEqual(uncovered, [])
        covered, uncovered = authorize.covers(self.task_dir, "repo_rules",
                                              ["AGENTS.md", ".codex/config.toml"], root=self.root)
        self.assertFalse(covered)
        self.assertEqual(uncovered, [".codex/config.toml"])

    def test_missing_authorization_covers_nothing(self):
        covered, uncovered = authorize.covers(self.task_dir, "repo_rules",
                                              ["AGENTS.md"], root=self.root)
        self.assertFalse(covered)
        self.assertEqual(uncovered, ["AGENTS.md"])


if __name__ == "__main__":
    unittest.main()

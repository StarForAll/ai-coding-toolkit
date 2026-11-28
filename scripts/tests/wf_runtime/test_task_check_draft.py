"""task-check --review-notes-draft：双轴审查结论的只读骨架入口。

dogfood 痛点：复杂任务的 task-check 要求 AI 手写
`{standard: {conclusion, basis}, requirement: {conclusion, basis}}`，
字段形状靠报错试错。本用例锁住：骨架只打印不落盘、给出真实任务目录路径、
TODO 不会被当成合法 conclusion。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, cli, tasks  # noqa: E402


class ReviewNotesDraftTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        task_dir = self.root / ".wf/tasks/t-20261123-1-alpha"
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(json.dumps(
            {"id": "t-20261123-1", "title": "草稿测试", "status": "in_progress",
             "phase": "Check"}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_plan(self, plan):
        task_dir = self.root / ".wf/tasks/t-20261123-1-alpha"
        record = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
        record["plan"] = plan
        (task_dir / "task.json").write_text(json.dumps(record), encoding="utf-8")

    def test_draft_includes_tdd_evidence_when_tdd_code(self):
        """TDD 开启（applicability=code）时，骨架必须列出 Check 真正读取的 `tdd_evidence`。

        2026-11-28 独立复审 F1.1/F3.4：字段只存在于消费方（`_parse_review_notes`），
        help inputs 与骨架都没有它 —— "按骨架填"永远过不了 Check。
        """
        self._write_plan({"tdd": True})
        ctx = type("Ctx", (), {"root": str(self.root)})()
        payload = tasks.cmd_task_check(ctx, cli.Args(
            ["--task", "t-20261123-1", "--review-notes-draft"]))
        draft = payload["facts"]["draft"]
        self.assertTrue(payload["facts"]["tdd_required"])
        evidence = draft.get("tdd_evidence") or {}
        # 形状由机制常量派生：骨架与消费方不再各写一份字面清单
        self.assertEqual(set(evidence), set(check.TDD_EVIDENCE_FIELDS))
        self.assertIn("tdd_evidence", payload["next"])

    def test_draft_omits_tdd_evidence_for_docs_applicability(self):
        self._write_plan({"tdd": True, "tdd_applicability": "docs"})
        ctx = type("Ctx", (), {"root": str(self.root)})()
        payload = tasks.cmd_task_check(ctx, cli.Args(
            ["--task", "t-20261123-1", "--review-notes-draft"]))
        self.assertFalse(payload["facts"]["tdd_required"])
        self.assertNotIn("tdd_evidence", payload["facts"]["draft"])

    def test_draft_prints_path_and_skeleton_without_writing(self):
        ctx = type("Ctx", (), {"root": str(self.root)})()
        args = cli.Args(["--task", "t-20261123-1", "--review-notes-draft"])
        payload = tasks.cmd_task_check(ctx, args)
        facts = payload["facts"]
        self.assertEqual(facts["draft"]["standard"]["conclusion"], "TODO（pass|fail|undecided）")
        self.assertEqual(facts["draft"]["requirement"]["conclusion"], "TODO（pass|fail|undecided）")
        self.assertIn(".wf/tasks/t-20261123-1-alpha", facts["path"])
        self.assertTrue(facts["path"].endswith("review-notes.json"))
        self.assertFalse(os.path.exists(facts["path"]))          # 只打印，不落盘
        self.assertIn("--review-notes-draft", payload["next"])

    def test_draft_requires_existing_task(self):
        ctx = type("Ctx", (), {"root": str(self.root)})()
        args = cli.Args(["--task", "missing", "--review-notes-draft"])
        with self.assertRaises(tasks.TaskError) as caught:
            tasks.cmd_task_check(ctx, args)
        self.assertEqual(caught.exception.code, "WF_RECORD_INVALID")

    def test_task_knowledge_changes_draft(self):
        ctx = type("Ctx", (), {"root": str(self.root)})()
        args = cli.Args(["--task", "t-20261123-1", "--changes-draft"])
        payload = tasks.cmd_task_knowledge(ctx, args)
        self.assertIn("TODO", payload["facts"]["draft"][0]["action"])
        self.assertTrue(payload["facts"]["path"].endswith("knowledge-changes.json"))
        self.assertFalse(os.path.exists(payload["facts"]["path"]))

    def test_spec_update_changes_draft(self):
        ctx = type("Ctx", (), {"root": str(self.root)})()
        args = cli.Args(["--task", "t-20261123-1", "--changes-draft"])
        payload = tasks.cmd_spec_update(ctx, args)
        self.assertIn("TODO", payload["facts"]["draft"][0]["operation"])
        self.assertTrue(payload["facts"]["path"].endswith("spec-changes.json"))
        self.assertFalse(os.path.exists(payload["facts"]["path"]))


if __name__ == "__main__":
    unittest.main()
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

from wflib import cli, tasks  # noqa: E402


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
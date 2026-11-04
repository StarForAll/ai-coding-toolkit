"""归档持久化只认任务记录（第三轮 R14）。"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "docs", "workflows", "新项目开发工作流", "payload", "lib"))

from wflib import tasks  # noqa: E402

TASK_ID = "2026-" + "d" * 32
RECORD_REL = f".wf/tasks/archive/2026-11/{TASK_ID}-demo"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()


class ArchivePersistedTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="wf-archive-")
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        os.makedirs(os.path.join(self.root, RECORD_REL, "review"))
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as stream:
            stream.write("# demo\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")
        self.lower = git(self.root, "rev-parse", "HEAD")
        self.task = {"id": TASK_ID, "action": {"kind": "task.archive", "head_before": self.lower}}

    def test_other_files_in_record_dir_do_not_count(self):
        with open(os.path.join(self.root, RECORD_REL, "review/notes.md"), "w", encoding="utf-8") as stream:
            stream.write("# notes\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "notes only")
        self.assertFalse(tasks.archive_persisted(self.root, self.task)["persisted"])

    def test_record_commit_counts(self):
        with open(os.path.join(self.root, RECORD_REL, "task.json"), "w", encoding="utf-8") as stream:
            json.dump({"id": TASK_ID, "terminal": "normal"}, stream)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "record")
        self.assertTrue(tasks.archive_persisted(self.root, self.task)["persisted"])

    def test_non_normal_terminal_does_not_count(self):
        with open(os.path.join(self.root, RECORD_REL, "task.json"), "w", encoding="utf-8") as stream:
            json.dump({"id": TASK_ID, "terminal": "abnormal"}, stream)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "record")
        self.assertFalse(tasks.archive_persisted(self.root, self.task)["persisted"])


if __name__ == "__main__":
    unittest.main()

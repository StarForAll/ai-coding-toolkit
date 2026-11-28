"""K6 提交前置必须覆盖所有提交入口，而不是只在 archive 里核。

stop 的 commit 去向、task-abandon 的提交授权、run terminate 的任务放弃都会落到
`_commit_paths`；同一批删除/仓库级规则文件必须同样要人签确认。
"""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402


class CommitGateTest(unittest.TestCase):
    def _ctx(self, root):
        return types.SimpleNamespace(root=root)

    def test_repo_rule_without_authorization_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            task = {"id": "t1", "title": "x"}
            with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as handle:
                handle.write("*.pyc\n")
            task_path = os.path.join(root, ".wf", "tasks", "t1-x")
            os.makedirs(task_path, exist_ok=True)
            import json
            with open(os.path.join(task_path, "task.json"), "w", encoding="utf-8") as handle:
                json.dump({"id": "t1", "title": "x"}, handle)
            problem = tasks._commit_gate_problems(self._ctx(root), task, [".gitignore"])
            self.assertIsNotNone(problem)
            self.assertEqual(problem[0], "WF_REPO_RULES_NOT_AUTHORIZED")
            self.assertIn(".gitignore", problem[1]["uncovered"])

    def test_rule_authorization_covers_path(self):
        with tempfile.TemporaryDirectory() as root:
            task = {"id": "t1", "title": "x"}
            with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as handle:
                handle.write("*.pyc\n")
            task_path = os.path.join(root, ".wf", "tasks", "t1-x")
            os.makedirs(task_path, exist_ok=True)
            import json
            with open(os.path.join(task_path, "task.json"), "w", encoding="utf-8") as handle:
                json.dump({"id": "t1", "title": "x"}, handle)
            # authorize.require 读的是 authorization-<action>.json（脱敏入库后的形态）
            with open(os.path.join(task_path, "authorization-repo_rules.json"), "w", encoding="utf-8") as handle:
                json.dump({"action": "repo_rules", "choice": "repo_rules", "paths": [".gitignore"], "source": "human:user",
                           "by": "human:user", "at": "2026-11-28T00:00:00+08:00",
                           "quote": "确认", "object_digest": "sha256:" + "0" * 64}, handle)
            self.assertIsNone(tasks._commit_gate_problems(self._ctx(root), task, [".gitignore"]))


if __name__ == "__main__":
    unittest.main()

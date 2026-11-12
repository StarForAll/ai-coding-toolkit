"""D3：归档失败后重入的幂等判据——同一批路径第二次提交是**空操作**。

判据（`tasks._commit_paths`）：
- 待提交路径已经全部在 HEAD 上（暂存为空）→ 返回 `already_clean: True`、HEAD 不变；
- 提交永远按**精确路径**执行（授权里的 glob 先展开），不会顺手带走别人的改动；
- 因此"归档失败后重入"不会重复提交，也不会把同一批改动提交两次。

本文件把这条判据锁成可执行的审计断言。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import scope, tasks as tasks_mod  # noqa: E402


def git(root, *args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=str(root),
                          capture_output=True, text=True, check=False)


class CommitIdempotencyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "tests@example.com")
        git(self.root, "config", "user.name", "tests")
        (self.root / "a.txt").write_text("v1\n", encoding="utf-8")
        (self.root / "b.txt").write_text("keep\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "init")

    def tearDown(self):
        self._tmp.cleanup()

    def commits(self):
        return int(git(self.root, "rev-list", "--count", "HEAD").stdout.strip())

    def test_second_commit_of_the_same_path_is_a_noop(self):
        (self.root / "a.txt").write_text("v2\n", encoding="utf-8")
        first = tasks_mod._commit_paths(self.root, ["a.txt"], "wf: complete t1")
        head_after_first = scope.head(self.root)
        second = tasks_mod._commit_paths(self.root, ["a.txt"], "wf: complete t1")
        self.assertTrue(first["committed"])
        self.assertFalse(first.get("already_clean"))
        # 重入：同一批路径已在 HEAD 上 → 空操作，HEAD 不动、不产生第二个提交
        self.assertTrue(second["committed"])
        self.assertTrue(second["already_clean"])
        self.assertEqual(scope.head(self.root), head_after_first)
        self.assertEqual(self.commits(), 2)          # init + 一次业务提交

    def test_commit_takes_only_the_authorized_paths(self):
        (self.root / "a.txt").write_text("v2\n", encoding="utf-8")
        (self.root / "b.txt").write_text("someone else\n", encoding="utf-8")
        tasks_mod._commit_paths(self.root, ["a.txt"], "wf: complete t1")
        # 这次提交只含 a.txt；b.txt 的改动仍留在工作树（不被捎带）
        changed = git(self.root, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(changed, ["a.txt"])
        self.assertIn("b.txt", scope.uncommitted_paths(self.root))

    def test_glob_grant_expands_to_real_paths_only(self):
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "x.py").write_text("x\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "pkg")
        (self.root / "pkg" / "x.py").write_text("x2\n", encoding="utf-8")
        result = tasks_mod._commit_paths(self.root, ["pkg/**"], "wf: complete t1")
        self.assertTrue(result["committed"])
        self.assertIn("pkg/x.py", result["paths"])


if __name__ == "__main__":
    unittest.main()

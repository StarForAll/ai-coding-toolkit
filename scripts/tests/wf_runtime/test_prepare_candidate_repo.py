"""候选仓库引导（`full/prepare_candidate_repo.py`）：tag / 干净工作树 / 版本一致 / meta 位置。

为什么必须有这一步：`install.py` 的 `resolve_tag()` / `_committed_bytes()` / `_worktree_clean()`
要求 `--source` 是**带 tag 的干净 git 仓库根**；作者树里的 `docs/workflows/wf-release`
既没有匹配 tag、也不该被当作候选。这里用合成树验证引导契约本身。
"""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FULL = Path(__file__).resolve().parents[0] / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = _load("wf_prepare_candidate_repo", FULL / "prepare_candidate_repo.py")


def make_tree(root, version="9.9.9"):
    os.makedirs(os.path.join(root, "wf-release"), exist_ok=True)
    with open(os.path.join(root, "install.py"), "w", encoding="utf-8") as handle:
        handle.write("#!/usr/bin/env python3\nprint('installer')\n")
    with open(os.path.join(root, "wf-release", "task-flow.md"), "w", encoding="utf-8") as handle:
        handle.write("# flow\n")
    with open(os.path.join(root, "wf-release.json"), "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 1, "version": version, "assets": [],
                   "compatibility": {"rules_digest": "sha256:" + "0" * 64}}, handle)
    return root


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="wf-candidate-")
        self.addCleanup(lambda: shutil.rmtree(self.work, ignore_errors=True))
        self.tree = make_tree(os.path.join(self.work, "tree"))
        self.out = os.path.join(self.work, "candidate")

    def test_builds_tagged_clean_repo_with_meta_outside(self):
        root, meta, status = candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertEqual(status, "BUILT")
        self.assertTrue(os.path.isdir(os.path.join(root, ".git")))
        self.assertEqual(meta["ref"], "refs/tags/wf-v9.9.9")
        self.assertTrue(os.path.isfile(root + ".meta.json"), "meta 必须在仓库根之外")
        self.assertTrue(os.path.isfile(root + ".owner"))
        self.assertFalse(os.path.exists(os.path.join(root, ".meta.json")))
        status = candidate.git(root, "status", "--porcelain", check=False)
        self.assertEqual(status.stdout.strip(), "", "候选仓库根必须干净")
        resolved = candidate.git(root, "rev-parse", "refs/tags/wf-v9.9.9^{commit}", check=False)
        self.assertEqual(resolved.returncode, 0)
        self.assertEqual(resolved.stdout.strip(), meta["commit"])

    def test_reuse_when_tree_and_version_unchanged(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        root, meta, status = candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertEqual(status, "REUSED")

    def test_rebuild_when_tree_changes(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        with open(os.path.join(self.tree, "wf-release", "task-flow.md"), "a", encoding="utf-8") as handle:
            handle.write("changed\n")
        root, meta, status = candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertEqual(status, "BUILT")

    def test_tree_version_mismatch_is_refused(self):
        with self.assertRaises(candidate.CandidateError):
            candidate.ensure(self.tree, "1.2.3", self.out)

    def test_dirty_worktree_fails_check(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        with open(os.path.join(self.out, "wf-release", "extra.md"), "w", encoding="utf-8") as handle:
            handle.write("dirty\n")
        with self.assertRaises(candidate.CandidateError) as caught:
            candidate.check(self.tree, "9.9.9", self.out)
        self.assertIn("不干净", str(caught.exception))

    def test_missing_tag_fails_check(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        candidate.git(self.out, "tag", "-d", "wf-v9.9.9")
        with self.assertRaises(candidate.CandidateError) as caught:
            candidate.check(self.tree, "9.9.9", self.out)
        self.assertIn("wf-v9.9.9", str(caught.exception))

    def test_check_requires_meta(self):
        with self.assertRaises(candidate.CandidateError):
            candidate.check(self.tree, "9.9.9", self.out)

    def test_output_inside_repository_is_refused(self):
        with self.assertRaises(candidate.CandidateError):
            candidate.check_out_path(str(REPO / "docs" / "workflows" / "wf-release"))
        with self.assertRaises(candidate.CandidateError):
            candidate.check_out_path(str(REPO))

    def test_version_must_be_semver(self):
        with self.assertRaises(candidate.CandidateError):
            candidate.ensure(self.tree, "9.9", self.out)


if __name__ == "__main__":
    unittest.main()

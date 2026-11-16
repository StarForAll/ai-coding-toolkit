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

    def test_input_a_candidate_b_is_never_reused(self):
        """输入树/候选内容不一致（A→B）不得误报 REUSED，也不能借 meta 升级。"""
        candidate.ensure(self.tree, "9.9.9", self.out)
        with open(os.path.join(self.tree, "wf-release", "task-flow.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# other content\n")
        with self.assertRaises(candidate.CandidateError):
            candidate.check(self.tree, "9.9.9", self.out)
        root, meta, status = candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertEqual(status, "BUILT")
        self.assertEqual(meta["input_tree_digest"], candidate.common.tree_digest(self.tree))

    def test_tag_head_and_meta_drift_are_refused(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        with open(self.out + ".meta.json", encoding="utf-8") as handle:
            meta = json.load(handle)
        for field, value in (("commit", "0" * 40), ("tree_digest", "sha256:" + "0" * 64),
                             ("schema_version", 1), ("tag", "wf-v0.0.0")):
            with self.subTest(field=field):
                tampered = dict(meta)
                tampered[field] = value
                with open(self.out + ".meta.json", "w", encoding="utf-8") as handle:
                    json.dump(tampered, handle)
                with self.assertRaises(candidate.CandidateError):
                    candidate.check(self.tree, "9.9.9", self.out)
        with open(self.out + ".meta.json", "w", encoding="utf-8") as handle:
            json.dump(meta, handle)
        # HEAD 与 tag 提交不一致（额外提交但未改 tag）
        candidate.git(self.out, "commit", "--allow-empty", "-qm", "drift")
        with self.assertRaises(candidate.CandidateError):
            candidate.check(self.tree, "9.9.9", self.out)

    def test_unowned_output_is_never_adopted_or_overwritten(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, "keep"), "w", encoding="utf-8") as handle:
            handle.write("mine\n")
        with self.assertRaises(candidate.CandidateError):
            candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "keep")))

    def test_failed_rebuild_keeps_the_valid_previous_generation(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        before = candidate.verify_candidate(self.tree, "9.9.9", self.out)
        # 让新代构建失败：产物内容与输入树不一致（在 copy 后注入，模拟发布验证失败）。
        original_copy = candidate.copy_tree

        def broken_copy(tree, dest):
            original_copy(tree, dest)
            with open(os.path.join(dest, "extra.md"), "w", encoding="utf-8") as handle:
                handle.write("unexpected\n")

        with open(os.path.join(self.tree, "wf-release", "task-flow.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# changed input\n")
        candidate.copy_tree = broken_copy
        try:
            with self.assertRaises(candidate.CandidateError):
                candidate.ensure(self.tree, "9.9.9", self.out)
        finally:
            candidate.copy_tree = original_copy
        # 旧代仍在，并可通过旧输入树完整验证（恢复能力未丢）。
        with open(os.path.join(self.tree, "wf-release", "task-flow.md"), "w",
                  encoding="utf-8") as handle:
            handle.write("# flow\n")
        after = candidate.verify_candidate(self.tree, "9.9.9", self.out)
        self.assertEqual(after["commit"], before["commit"])
        self.assertEqual(after["tree_digest"], before["tree_digest"])

    def test_check_does_not_refresh_the_git_index(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        index = Path(self.out) / ".git" / "index"
        before = (index.stat().st_ino, index.stat().st_mtime_ns, index.stat().st_size)
        candidate.check(self.tree, "9.9.9", self.out)
        after = (index.stat().st_ino, index.stat().st_mtime_ns, index.stat().st_size)
        self.assertEqual(after, before, "check 必须使用 GIT_OPTIONAL_LOCKS=0，不刷新索引")

    def test_reuse_is_read_only_and_stable(self):
        candidate.ensure(self.tree, "9.9.9", self.out)
        before = (os.stat(self.out + ".meta.json").st_mtime_ns,
                  candidate.common.tree_digest(self.out))
        root, meta, status = candidate.ensure(self.tree, "9.9.9", self.out)
        self.assertEqual(status, "REUSED")
        after = (os.stat(self.out + ".meta.json").st_mtime_ns,
                 candidate.common.tree_digest(self.out))
        self.assertEqual(after, before, "复用不得改写候选或刷新证明")


if __name__ == "__main__":
    unittest.main()

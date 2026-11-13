"""测试发行隔离（`scripts/tests/wf_test_release.py`）：版本解析、输出边界、meta 新鲜度。

关键契约：
- 测试发行只写缓存根，**绝不**写 `docs/workflows/wf-release`；
- 所有权标记与 meta 都在输出根之外（进树会破坏字节复现）；
- `--no-build` 的 `--check` 必须核对 meta 的 source_tree_digest / version / manifest_digest，
  任一不符就拒绝，不静默使用旧副本。
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TESTS = REPO / "scripts" / "tests"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(REPO / "scripts"))
test_release = _load("wf_test_release", TESTS / "wf_test_release.py")
import wf_release_common as common  # noqa: E402


class VersionTest(unittest.TestCase):
    def test_placeholder_dev_manifest_falls_back_to_test_constant(self):
        self.assertEqual(test_release.resolve_version(None, {"version": "0.0.0-dev"}), "0.1.0")

    def test_real_dev_manifest_version_is_followed(self):
        self.assertEqual(test_release.resolve_version(None, {"version": "0.1.2"}), "0.1.2")

    def test_conflicting_request_is_refused(self):
        with self.assertRaises(test_release.TestReleaseError):
            test_release.resolve_version("0.1.0", {"version": "0.1.2"})

    def test_explicit_version_wins_over_placeholder(self):
        self.assertEqual(test_release.resolve_version("0.2.0", {"version": "0.0.0-dev"}), "0.2.0")


class OutputBoundaryTest(unittest.TestCase):
    def test_repository_and_product_tree_are_refused(self):
        for path in (str(REPO), str(REPO / "docs" / "workflows" / "wf-release"),
                     str(REPO / "docs" / "workflows"), str(REPO / "scripts")):
            with self.assertRaises(test_release.TestReleaseError):
                test_release.check_output_root(path)

    def test_symlink_root_is_refused(self):
        root = tempfile.mkdtemp(prefix="wf-test-release-link-")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        link = os.path.join(root, "link")
        os.symlink(os.path.join(root, "target"), link)
        with self.assertRaises(test_release.TestReleaseError):
            test_release.check_output_root(link)

    def test_foreign_non_empty_root_is_refused(self):
        root = tempfile.mkdtemp(prefix="wf-test-release-foreign-")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        with open(os.path.join(root, "keep.txt"), "w", encoding="utf-8") as handle:
            handle.write("mine\n")
        with self.assertRaises(test_release.TestReleaseError):
            test_release.ensure_release(root, "0.1.0", {"version": "0.0.0-dev"})


class EnsureAndCheckTest(unittest.TestCase):
    def setUp(self):
        self.cache = tempfile.mkdtemp(prefix="wf-test-release-cache-")
        self.addCleanup(lambda: shutil.rmtree(self.cache, ignore_errors=True))
        self.dev = {"version": "0.0.0-dev"}
        self.root = os.path.join(self.cache, "0.1.0")

    def test_build_keeps_product_tree_and_marks_outside(self):
        before = common.tree_digest(str(REPO / "docs" / "workflows" / "wf-release"))
        root, meta = test_release.ensure_release(self.root, "0.1.0", self.dev)
        after = common.tree_digest(str(REPO / "docs" / "workflows" / "wf-release"))
        self.assertEqual(before, after, "测试发行构建不得改写产品发行树")
        self.assertTrue(os.path.isfile(os.path.join(root, "wf-release.json")))
        self.assertTrue(os.path.isfile(root + ".meta.json"), "meta 必须在输出根之外")
        self.assertTrue(os.path.isfile(root + ".owner"), "所有权标记必须在输出根之外")
        self.assertFalse(os.path.exists(os.path.join(root, ".owner")))
        self.assertEqual(meta["version"], "0.1.0")
        self.assertEqual(meta["release_ref"], "refs/tags/wf-v0.1.0")
        self.assertEqual(meta["source_tree_digest"], common.source_tree_digest())

    def test_check_accepts_fresh_copy(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        meta = test_release.check_meta(self.root, "0.1.0", self.dev)
        self.assertEqual(meta["version"], "0.1.0")

    def test_check_refuses_stale_source_digest(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        path = self.root + ".meta.json"
        with open(path, encoding="utf-8") as handle:
            meta = json.load(handle)
        meta["source_tree_digest"] = "sha256:" + "0" * 64
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle)
        with self.assertRaises(test_release.TestReleaseError) as caught:
            test_release.check_meta(self.root, "0.1.0", self.dev)
        self.assertIn("过期", str(caught.exception))

    def test_check_refuses_missing_meta(self):
        os.makedirs(self.root)
        with self.assertRaises(test_release.TestReleaseError):
            test_release.check_meta(self.root, "0.1.0", self.dev)

    def test_check_refuses_tampered_manifest(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        manifest_path = os.path.join(self.root, "wf-release.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["version"] = "0.9.9"
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        with self.assertRaises(test_release.TestReleaseError):
            test_release.check_meta(self.root, "0.1.0", self.dev)

    def test_rebuild_is_reused_when_source_unchanged(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        stamp = os.stat(self.root + ".meta.json").st_mtime_ns
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        self.assertEqual(stamp, os.stat(self.root + ".meta.json").st_mtime_ns,
                         "源树未变时应复用缓存，不重建")


if __name__ == "__main__":
    unittest.main()

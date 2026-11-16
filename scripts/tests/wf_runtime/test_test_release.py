"""测试发行隔离（`scripts/tests/wf_test_release.py`）：版本解析、输出边界、meta 新鲜度。

关键契约：
- 测试发行只写缓存根，**绝不**写 `docs/workflows/wf-release`；
- 所有权标记与 meta 都在输出根之外（进树会破坏字节复现）；
- `--no-build` 的 `--check` 必须核对 meta 的 source_tree_digest / version / manifest_digest，
  任一不符就拒绝，不静默使用旧副本。
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
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


class GitInjectionTest(unittest.TestCase):
    """HEAD 读取失败：`WF_GIT_BIN` 只做测试注入，失败必须如实返回 None（不猜、不签发）。"""

    def test_broken_git_bin_makes_head_unreadable(self):
        root = tempfile.mkdtemp(prefix="wf-git-bin-")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        shim = os.path.join(root, "git-broken.sh")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/bash\nexit 1\n")
        os.chmod(shim, 0o755)
        with mock.patch.dict(os.environ, {"WF_GIT_BIN": shim}):
            self.assertIsNone(common.git_head())
            self.assertIsNone(common.git_describe())
            # 模板身份把 HEAD 当作可空输入：读不到时仍产出稳定摘要，由调用方决定是否用缓存。
            self.assertTrue(common.fixture_template_inputs_digest("dev", "0.1.0").startswith("sha256:"))


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


class InputIdentityTest(unittest.TestCase):
    """cache 输入身份（AC1/V1）：资产、manifest、工具、dirty 字节与 dev HEAD 都必须参与。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-input-identity-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        (self.source / "payload" / "lib" / "wflib").mkdir(parents=True)
        (self.source / "payload" / "lib" / "wflib" / "a.py").write_text("a\n", encoding="utf-8")
        (self.source / "dev-manifest.json").write_text(
            '{"assets": [{"source_path": "payload/lib/wflib/a.py"}]}\n', encoding="utf-8")
        self.tools = self.root / "tools.py"
        self.tools.write_text("tool\n", encoding="utf-8")

    def digest(self):
        return common.test_release_inputs_digest("0.1.0", str(self.source))

    def test_same_inputs_are_stable_and_touch_does_not_invalidate(self):
        first = self.digest()
        os.utime(self.source / "payload" / "lib" / "wflib" / "a.py", (1, 1))
        self.assertEqual(first, self.digest())

    def test_asset_and_manifest_bytes_change_the_digest(self):
        first = self.digest()
        (self.source / "payload" / "lib" / "wflib" / "a.py").write_text("dirty\n", encoding="utf-8")
        changed_asset = self.digest()
        self.assertNotEqual(first, changed_asset)
        (self.source / "dev-manifest.json").write_text(
            '{"assets": [{"source_path": "payload/lib/wflib/a.py"}]}\n\n', encoding="utf-8")
        self.assertNotEqual(changed_asset, self.digest())

    def test_build_tool_bytes_change_the_digest(self):
        with mock.patch.object(common, "_build_tool_files", return_value=[str(self.tools)]):
            before = self.digest()
            self.tools.write_text("tool changed\n", encoding="utf-8")
            self.assertNotEqual(before, self.digest())

    def test_missing_input_is_refused(self):
        (self.source / "payload" / "lib" / "wflib" / "a.py").unlink()
        with self.assertRaises(common.ReleaseError):
            self.digest()

    def test_template_inputs_bind_dev_head_but_candidate_binds_release_subject(self):
        with mock.patch.object(common, "_helper_identity", return_value={"role": "x"}):
            with mock.patch.object(common, "git_head", return_value="head-a"):
                first = common.fixture_template_inputs_digest("dev", str(self.source))
            with mock.patch.object(common, "git_head", return_value="head-b"):
                self.assertNotEqual(first, common.fixture_template_inputs_digest("dev", str(self.source)))
            with mock.patch.object(common, "git_head", return_value="head-a"):
                self.assertEqual(
                    common.fixture_template_inputs_digest(
                        "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "subject-a", str(self.source)),
                    common.fixture_template_inputs_digest(
                        "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "subject-a", str(self.source)))
                self.assertNotEqual(
                    common.fixture_template_inputs_digest(
                        "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "subject-a", str(self.source)),
                    common.fixture_template_inputs_digest(
                        "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "subject-b", str(self.source)))
            # HEAD 不可读：显式空串落进输入（不签发 unknown），同一状态仍稳定
            with mock.patch.object(common, "git_head", return_value=None):
                self.assertEqual(common.fixture_template_inputs_digest("dev", str(self.source)),
                                 common.fixture_template_inputs_digest("dev", str(self.source)))

    def test_input_identity_stays_within_the_cost_budget(self):
        """身份核验是公共 barrier 级工作：不能靠逐目录 walk 变成秒级成本。"""
        import time

        started = time.monotonic()
        common.test_release_inputs_digest("0.1.0")
        common.fixture_template_inputs_digest("dev", "0.1.0")
        self.assertLess(time.monotonic() - started, 3.0, "身份解析超出 3 秒预算")

    def test_template_slot_is_injective_and_keeps_candidate_parts(self):
        first = common.template_cache_slot("3.11", "candidate", "0.1.2", "refs/tags/wf-v0.1.2")
        second = common.template_cache_slot("3.11", "candidate", "0.1.2", "refs/tags/wf-v0.1.3")
        self.assertNotEqual(first, second)
        for value in (first, second):
            self.assertRegex(value, r"^[A-Za-z0-9_-]+$")
        self.assertNotEqual(common.template_cache_slot("3.11", "dev"),
                            common.template_cache_slot("3.12", "dev"))
        key = common.template_cache_key("sha256:" + "a" * 64, "3.11", "dev")
        self.assertTrue(key.startswith("a" * 12 + "-"))
        with self.assertRaises(common.ReleaseError):
            common.template_cache_key("not-a-digest", "3.11", "dev")


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

    def test_meta_carries_build_inputs_and_output_tree_digest(self):
        _, meta = test_release.ensure_release(self.root, "0.1.0", self.dev)
        self.assertEqual(meta["schema_version"], 2)
        self.assertEqual(meta["build_inputs"], common.test_release_inputs_digest("0.1.0"))
        self.assertEqual(meta["output_tree_digest"], common.tree_digest(self.root))
        self.assertFalse(os.path.exists(self.root + ".journal.json"), "提交后 journal 必须清掉")

    def test_check_refuses_tampered_release_tree(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        target = Path(self.root) / "wf-release.json"
        target.write_text(target.read_text() + "\n", encoding="utf-8")
        with self.assertRaises(test_release.TestReleaseError) as caught:
            test_release.check_meta(self.root, "0.1.0", self.dev)
        self.assertIn("树摘要", str(caught.exception))

    def test_rebuild_is_reused_when_source_unchanged(self):
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        stamp = os.stat(self.root + ".meta.json").st_mtime_ns
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        self.assertEqual(stamp, os.stat(self.root + ".meta.json").st_mtime_ns,
                         "源树未变时应复用缓存，不重建")

    def test_build_leaves_no_staging_or_backup_litter(self):
        """发布成功后不留下 `<root>.staging-*` / `.backup-*` 空壳（父目录也要回收）。"""
        test_release.ensure_release(self.root, "0.1.0", self.dev)
        parent = Path(self.root).parent
        litter = sorted(path.name for path in parent.iterdir()
                        if ".staging-" in path.name or ".backup-" in path.name)
        self.assertEqual(litter, [], f"发布后残留 staging/backup：{litter}")
        self.assertTrue(Path(self.root + ".meta.json").is_file())
        self.assertTrue(Path(self.root + ".owner").is_file())

    def test_cli_json_reports_built_then_reused_and_cumulative_builds(self):
        """成本账目（AC5）：首次 built + builds=1，同输入再来 reused 且 builds 不增。"""

        def run(flag):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = test_release.main([flag, "--json", "--root", self.root, "--version", "0.1.0"])
            self.assertEqual(code, 0)
            return json.loads(buffer.getvalue())

        payload = run("--ensure")
        self.assertEqual((payload["status"], payload["builds"]), ("built", 1))
        payload = run("--ensure")
        self.assertEqual((payload["status"], payload["builds"]), ("reused", 1),
                         "同输入复用不增加构建计数")
        self.assertEqual(run("--check")["status"], "checked")


if __name__ == "__main__":
    unittest.main()

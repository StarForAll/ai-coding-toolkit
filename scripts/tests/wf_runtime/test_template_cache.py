"""模板缓存（`full/template_cache.py`）：输入身份、命中核验与 legacy 迁移边界（AC1/AC4）。

断言锚在**条目状态**上：dirty/HEAD 变化改 key；命中必须 meta/root/输入/tree digest 全match；
迁移只认同槽位且 owner/root/身份完整的 legacy key，其他目录原地不动。
"""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FULL = Path(__file__).resolve().parents[0] / "full"
REPO = FULL.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(FULL))

spec = importlib.util.spec_from_file_location("wf_template_cache", FULL / "template_cache.py")
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)
import fixture_scope  # noqa: E402

INPUTS = "sha256:" + "a" * 64


class Args:
    def __init__(self, cache_root, deploy="dev", version=None, ref=None, release_root=None,
                 subject=None, results_dir=None):
        self.cache_root = str(cache_root)
        self.deploy = deploy
        self.version = version
        self.ref = ref
        self.release_root = release_root
        self.subject = subject
        self.results_dir = results_dir


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-template-cache-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "template"
        self.root.mkdir(parents=True)
        self.args = Args(self.root)
        patcher = mock.patch.object(cache, "_check_identity", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def key(self, args=None, inputs=INPUTS):
        return cache.key_for(args or self.args, inputs)

    def entry(self, name, inputs=INPUTS, deploy="dev", version="", ref="", tree_marker="body",
              meta_overrides=None, owned=True):
        entry = self.root / name
        fixture_scope.reset(entry)
        (entry / "content").write_text(tree_marker + "\n", encoding="utf-8")
        meta = {"schema_version": 1, "key": name, "inputs_digest": inputs,
                "output_tree_digest": cache.common.tree_digest(str(entry)),
                "deploy": deploy, "version": version, "ref": ref,
                "pyver": f"{sys.version_info[0]}.{sys.version_info[1]}",
                "root": os.path.realpath(entry)}
        meta.update(meta_overrides or {})
        cache._write_json(cache.meta_path(str(entry)), meta)
        if not owned:
            fixture_scope.marker(Path(entry)).unlink()
        return entry

    def meta_text(self, entry):
        return Path(cache.meta_path(str(entry))).read_text()

    def write_meta(self, entry, meta):
        cache._write_json(cache.meta_path(str(entry)), meta)

    def lookup(self, args=None):
        args = args or self.args
        return cache.main(["lookup", "--cache-root", str(self.root), "--deploy", args.deploy,
                           *(["--version", args.version, "--ref", args.ref] if args.version else [])])

    def migrate(self, args=None):
        args = args or self.args
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = cache.main(["migrate", "--cache-root", str(self.root), "--deploy", args.deploy,
                               *(["--version", args.version, "--ref", args.ref] if args.version else [])])
        self.assertEqual(code, 0)
        return buffer.getvalue().strip()


class KeyTest(Base):
    def test_key_is_stable_and_bound_to_inputs_and_slot(self):
        self.assertEqual(self.key(), self.key())
        self.assertNotEqual(self.key(), self.key(inputs="sha256:" + "c" * 64))
        candidate = Args(self.root, "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "/candidate")
        other = Args(self.root, "candidate", "0.1.3", "refs/tags/wf-v0.1.3", "/candidate")
        self.assertNotEqual(self.key(candidate), self.key(other))

    def test_candidate_requires_version_and_ref(self):
        with self.assertRaises(cache.CacheError):
            cache.version_ref(Args(self.root, "candidate"))


class LookupTest(Base):
    def test_valid_entry_is_a_hit(self):
        entry = self.entry(self.key())
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            self.assertEqual(self.lookup(), 0)
            self.assertTrue(entry.is_dir())

    def test_changed_inputs_or_tree_are_misses(self):
        self.entry(self.key())
        with mock.patch.object(cache, "inputs_digest", return_value="sha256:" + "f" * 64):
            self.assertEqual(self.lookup(), 10)
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            (self.root / self.key() / "content").write_text("dirty\n", encoding="utf-8")
            self.assertEqual(self.lookup(), 10)

    def test_legacy_schema_moved_root_and_missing_meta_are_misses(self):
        key = self.key()
        entry = self.entry(key, meta_overrides={"schema_version": None})
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            self.assertEqual(self.lookup(), 10)
            meta = json.loads(self.meta_text(entry))
            meta["schema_version"] = 1
            meta["root"] = str(self.root / "elsewhere")
            self.write_meta(entry, meta)
            self.assertEqual(self.lookup(), 10)
            (self.root / "other").mkdir()
        self.assertTrue(entry.is_dir())

    def test_identity_failure_is_a_miss(self):
        self.entry(self.key())
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS), \
                mock.patch.object(cache, "_check_identity", return_value="空态失败"):
            self.assertEqual(self.lookup(), 10)


class MigrateTest(Base):
    pyver = f"{sys.version_info[0]}.{sys.version_info[1]}"

    def legacy(self, name, **kwargs):
        return self.entry(name, **kwargs)

    def test_same_slot_legacy_entry_is_renamed(self):
        source = self.legacy(f"aaaaaaaabbbb-{self.pyver}-dev")
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            key = self.migrate()
        self.assertTrue((self.root / key).is_dir())
        self.assertFalse(source.exists())
        self.assertTrue((self.root / key / "content").exists())
        self.assertTrue(Path(cache.meta_path(str(self.root / key))).is_file())

    def test_other_python_deploy_version_and_unowned_entries_stay(self):
        other_py = self.legacy(f"aaaaaaaabbbb-9.9-dev")
        other_deploy = self.legacy(f"aaaaaaaabbbb-{self.pyver}-candidate-0.1.2-refs-tags-wf-v0.1.2",
                                  deploy="candidate", version="0.1.2", ref="refs/tags/wf-v0.1.2")
        unowned = self.legacy(f"aaaaaaaabbbb-{self.pyver}-dev-unowned", owned=False)
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            key = self.migrate()
        self.assertTrue(other_py.is_dir())
        self.assertTrue(other_deploy.is_dir())
        self.assertTrue(unowned.is_dir())
        self.assertNotEqual(key, unowned.name)

    def test_existing_target_blocks_migration(self):
        source = self.legacy(f"aaaaaaaabbbb-{self.pyver}-dev")
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            key = self.migrate()
        self.assertTrue((self.root / key).is_dir())
        other = self.legacy(f"ccccccccdddd-{self.pyver}-dev")
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            self.assertEqual(self.migrate(), key)
        self.assertTrue(other.is_dir())
        self.assertTrue(source.exists() is False)

    def test_candidate_migration_requires_same_version_and_ref(self):
        source = self.legacy(f"aaaaaaaabbbb-{self.pyver}-candidate-0.1.2-refs-tags-wf-v0.1.2",
                             deploy="candidate", version="0.1.2", ref="refs/tags/wf-v0.1.2")
        target = Args(self.root, "candidate", "0.1.2", "refs/tags/wf-v0.1.2", "/candidate")
        with mock.patch.object(cache, "inputs_digest", return_value=INPUTS):
            key = self.migrate(target)
            self.assertTrue((self.root / key).is_dir())
            self.assertFalse(source.exists())
            mismatch = Args(self.root, "candidate", "0.1.3", "refs/tags/wf-v0.1.3", "/candidate")
            self.assertEqual(self.migrate(mismatch), self.key(mismatch))


class RecoveryTest(Base):
    def journal(self, entry, staging, old):
        cache._write_json(cache.journal_path(str(self.root), entry.name),
                          {"schema_version": 1, "key": entry.name, "transaction": "tx",
                           "old": old, "new": {"digest": cache.common.tree_digest(str(staging)),
                                              "staging": str(staging),
                                              "backup": str(entry) + ".backup-tx", "meta": "{}\n"}})

    def test_recovery_rolls_back_without_touching_siblings(self):
        entry = self.entry("k1", tree_marker="old")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        sibling = self.root / "keep.txt"
        sibling.write_text("keep\n", encoding="utf-8")
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, old)
        fixture_scope.move(entry, Path(str(entry) + ".backup-tx"))
        (staging / "content").write_text("corrupted\n", encoding="utf-8")
        self.assertEqual(cache.recover(str(entry), str(self.root), "k1"), "rolled-back")
        self.assertEqual((entry / "content").read_text(), "old\n")
        self.assertEqual(sibling.read_text(), "keep\n")
        self.assertFalse(Path(str(entry) + ".backup-tx").exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_unverifiable_generations_fail_closed(self):
        entry = self.entry("k1")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, old)
        (staging / "content").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(cache.CacheError):
            cache.recover(str(entry), str(self.root), "k1")
        self.assertTrue(Path(cache.journal_path(str(self.root), "k1")).exists())


if __name__ == "__main__":
    unittest.main()

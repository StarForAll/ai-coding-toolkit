"""模板缓存（`full/template_cache.py`）：输入身份、命中核验与 legacy 迁移边界（AC1/AC4）。

断言锚在**条目状态**上：dirty/HEAD 变化改 key；命中必须 meta/root/输入/tree digest 全match；
迁移只认同槽位且 owner/root/身份完整的 legacy key，其他目录原地不动。
"""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
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


class PublishCostTest(Base):
    """成本账目（AC5）：同输入复建才累计 builds，命中不增。"""

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def publish(self, inputs=INPUTS):
        buffer = io.StringIO()
        with mock.patch.object(cache, "inputs_digest", return_value=inputs), \
                mock.patch.object(cache, "subprocess") as subprocess_mock:
            subprocess_mock.run.return_value = self._Completed()
            with contextlib.redirect_stdout(buffer):
                code = cache.main(["publish", "--cache-root", str(self.root), "--deploy", "dev",
                                   "--results-dir", str(self.root / "results")])
        self.assertEqual(code, 0)
        return buffer.getvalue().strip().splitlines()

    def builder(self):
        def build(_args, staging):
            fixture_scope.reset(staging)
            (pathlib.Path(staging) / "content").write_text("body\n", encoding="utf-8")
        return mock.patch.object(cache, "_build", side_effect=build)

    def test_alternating_inputs_each_resolve_to_their_own_entry_and_a_third_misses(self):
        """双输入交替（AC4/AC11）：A/B 各自命中自己的条目，未出现过的输入必须 miss。"""
        first = "sha256:" + "1" * 64
        second = "sha256:" + "2" * 64
        with self.builder():
            entry_a = Path(self.publish(first)[0])
            entry_b = Path(self.publish(second)[0])
        self.assertNotEqual(entry_a, entry_b, "输入变化必须换 key")
        self.assertEqual(json.loads(self.meta_text(entry_a))["inputs_digest"], first)
        self.assertEqual(json.loads(self.meta_text(entry_b))["inputs_digest"], second)
        with mock.patch.object(cache, "inputs_digest", return_value=first):
            self.assertEqual(self.lookup(), 0)
        with mock.patch.object(cache, "inputs_digest", return_value=second):
            self.assertEqual(self.lookup(), 0)
        with mock.patch.object(cache, "inputs_digest", return_value="sha256:" + "3" * 64):
            self.assertEqual(self.lookup(), 10, "未发布过的输入必须 miss，不得复用别的槽位")

    def test_rebuild_accumulates_builds_and_reuse_does_not(self):
        with self.builder():
            lines = self.publish()
        entry = Path(lines[0])
        self.assertEqual(json.loads(self.meta_text(entry))["builds"], 1)
        with self.builder():
            self.publish()
        self.assertEqual(json.loads(self.meta_text(entry))["builds"], 1, "命中不重建、不增计数")



class ObserveTest(Base):
    def setUp(self):
        self.scope = fixture_scope.create_test_scope()
        self.addCleanup(shutil.rmtree, self.scope, True)
        self.root = Path(tempfile.mkdtemp(prefix="cache-observe-", dir=self.scope))
        self.cache_root = self.root / "template"
        self.cache_root.mkdir()
        self.results = self.root / "results"
        self.results.mkdir()

    def publish(self):
        return run_template_cli("publish", self.cache_root, self.results, self.scope)

    def key(self):
        return next(name for name in os.listdir(self.cache_root)
                    if name.endswith("-cHkzLjE0-ZGV2"))

    def test_observe_is_shallow_and_names_the_control_records(self):
        self.assertEqual(self.publish().returncode, 0)
        import wf_release_common as common
        with mock.patch.object(common, "tree_digest",
                               side_effect=AssertionError("observe must not walk trees")):
            report = cache.observe(str(self.cache_root))
        self.assertEqual(report["status"], "complete", report)
        self.assertEqual(report["counts"].get("valid"), 1)
        self.assertEqual(report["capacity"], "not-measured")
        self.assertTrue(report["observed_at"])
        self.assertIn("inventory --cache-root", report["inventory_hint"])

    def test_observe_reports_pending_journal_and_materials_without_recovery(self):
        self.assertEqual(self.publish().returncode, 0)
        key = self.key()
        journal = Path(cache.journal_path(str(self.cache_root), key))
        journal.write_text('{"schema_version": 1, "key": "broken"}')
        staging = Path(str(self.cache_root / key) + ".staging-tx")
        staging.mkdir()
        report = cache.observe(str(self.cache_root))
        self.assertEqual(report["status"], "partial")
        self.assertGreaterEqual(report["counts"].get("recovery-required", 0), 1)
        self.assertGreaterEqual(report["counts"].get("orphan-like", 0), 1)
        self.assertTrue(journal.exists(), "observe 不得恢复/删除")


class LookupJournalTest(Base):
    def test_lookup_refuses_pending_journal_without_writing(self):
        inputs = cache.inputs_digest(self.args)
        key = cache.key_for(self.args, inputs)
        entry = self.entry(key, inputs=inputs)
        journal = Path(cache.journal_path(str(self.root), key))
        journal.write_text('{"schema_version": 1, "key": "k1", "root": "/elsewhere"}')
        before = sorted(os.listdir(self.root))
        code = cache.main(["lookup", "--cache-root", str(self.root), "--deploy", "dev"])
        self.assertEqual(code, 10)
        self.assertEqual(sorted(os.listdir(self.root)), before)
        self.assertTrue(journal.exists())


class FinishFailureTest(Base):
    def test_material_cleanup_failure_keeps_the_journal(self):
        entry = self.entry("k1", tree_marker="old")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n")
        journal = {"schema_version": 1, "key": "k1", "transaction": "tx",
                   "old": old,
                   "new": {"digest": None, "staging": str(staging),
                           "backup": str(entry) + ".backup-tx", "meta": None}}
        cache._write_json(cache.journal_path(str(self.root), "k1"), journal)
        import shutil as _shutil
        original = _shutil.rmtree

        def failing(path, *args, **kwargs):
            if str(path) == str(staging):
                raise OSError("injected cleanup failure")
            return original(path, *args, **kwargs)

        with mock.patch.object(_shutil, "rmtree", side_effect=failing):
            with self.assertRaises(cache.CacheError):
                cache.recover(str(entry), str(self.root), "k1")
        self.assertTrue(cache.journal_path(str(self.root), "k1").__class__ and
                        Path(cache.journal_path(str(self.root), "k1")).exists())


class CheckpointGateTest(Base):
    def test_invalid_checkpoint_needs_switch_and_owned_scope(self):
        with mock.patch.dict(os.environ, {"WF_TEMPLATE_TXN_STOP_AFTER": "bogus"}, clear=False):
            with self.assertRaises(cache.CacheError):
                cache.validate_checkpoint()
        with mock.patch.dict(os.environ, {"WF_TEST_FAULT_INJECTION": "1",
                                          "WF_TEMPLATE_TXN_STOP_AFTER": "bogus"}, clear=False):
            with self.assertRaises(cache.CacheError):
                cache.validate_checkpoint()
        with mock.patch.dict(os.environ, {"WF_TEST_FAULT_INJECTION": "1",
                                          "WF_TEMPLATE_TXN_STOP_AFTER": "after-journal"},
                             clear=False):
            with mock.patch.object(cache, "_owned_scope", return_value=False):
                with self.assertRaises(cache.CacheError):
                    cache.validate_checkpoint()


class RecoveryTest(Base):
    def journal(self, entry, staging, old, digest="__auto__", meta="{}\n"):
        if digest == "__auto__":
            digest = cache.common.tree_digest(str(staging))
        cache._write_json(cache.journal_path(str(self.root), entry.name),
                          {"schema_version": 1, "key": entry.name, "transaction": "tx",
                           "old": old, "new": {"digest": digest, "staging": str(staging),
                                               "backup": str(entry) + ".backup-tx", "meta": meta}})

    def recover(self, entry, key=None):
        return cache.recover(str(entry), str(self.root), key or entry.name)

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
        self.assertEqual(self.recover(entry), "rolled-back")
        self.assertEqual((entry / "content").read_text(), "old\n")
        self.assertEqual(sibling.read_text(), "keep\n")
        self.assertFalse(Path(str(entry) + ".backup-tx").exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_window_journal_written_before_old_moved_rolls_back_in_place(self):
        """journal 已落（新代摘要未确认）、旧条目未移：旧条目原位完好 → 回滚完成，不要求 backup。"""
        entry = self.entry("k1", tree_marker="old")
        meta_text = self.meta_text(entry)
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)), "meta": meta_text}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, old, digest=None, meta=None)
        sibling = self.root / "keep.txt"
        sibling.write_text("keep\n", encoding="utf-8")
        self.assertEqual(self.recover(entry), "rolled-back")
        self.assertEqual((entry / "content").read_text(), "old\n")
        self.assertEqual(self.meta_text(entry), meta_text)
        self.assertFalse(staging.exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())
        self.assertEqual(sibling.read_text(), "keep\n")

    def test_window_old_moved_before_new_installed_rolls_forward(self):
        """移旧未装新：旧条目在 backup、staging 可验证 → 前滚安装并清 backup/journal。"""
        entry = self.entry("k1", tree_marker="old")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        new_digest = cache.common.tree_digest(str(staging))
        new_meta_text = json.dumps({"schema_version": 1, "key": "k1", "inputs_digest": INPUTS,
                                    "output_tree_digest": new_digest, "deploy": "dev", "version": "",
                                    "ref": "", "pyver": f"{sys.version_info[0]}.{sys.version_info[1]}",
                                    "root": os.path.realpath(entry)}, sort_keys=True) + "\n"
        self.journal(entry, staging, old, meta=new_meta_text)
        fixture_scope.move(entry, Path(str(entry) + ".backup-tx"))     # 只移走旧代
        self.assertEqual(self.recover(entry), "rolled-forward")
        self.assertEqual((entry / "content").read_text(), "new\n")
        self.assertEqual(cache.common.tree_digest(str(entry)), new_digest)
        self.assertEqual(self.meta_text(entry), new_meta_text)
        self.assertFalse(Path(str(entry) + ".backup-tx").exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_window_new_installed_before_repoint_rolls_back_from_backup(self):
        """装新未 repoint（journal 还没记摘要）：两代都可验证但新代未确认 → 按旧代回滚。"""
        entry = self.entry("k1", tree_marker="old")
        meta_text = self.meta_text(entry)
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)), "meta": meta_text}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, old, digest=None, meta=None)      # 摘要尚未确认
        fixture_scope.move(entry, Path(str(entry) + ".backup-tx"))
        fixture_scope.move(staging, entry)                             # 新树已就位，未 repoint/meta
        self.assertEqual(self.recover(entry), "rolled-back")
        self.assertEqual((entry / "content").read_text(), "old\n")
        self.assertEqual(self.meta_text(entry), meta_text)
        self.assertFalse(staging.exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_window_new_generation_installed_before_meta_is_completed(self):
        """装新条目但 meta 未写：前滚按 journal 冻结的 meta 原文写入并核 tree digest。"""
        entry = self.entry("k1", tree_marker="old")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        new_digest = cache.common.tree_digest(str(staging))
        new_meta_text = json.dumps({"schema_version": 1, "key": "k1", "inputs_digest": INPUTS,
                                    "output_tree_digest": new_digest, "deploy": "dev", "version": "",
                                    "ref": "", "pyver": f"{sys.version_info[0]}.{sys.version_info[1]}",
                                    "root": os.path.realpath(entry)}, sort_keys=True) + "\n"
        self.journal(entry, staging, old, meta=new_meta_text)
        fixture_scope.move(entry, Path(str(entry) + ".backup-tx"))
        fixture_scope.move(staging, entry)                 # 半完成：新树已就位，meta 未写
        self.assertEqual(self.recover(entry), "rolled-forward")
        self.assertEqual((entry / "content").read_text(), "new\n")
        self.assertEqual(self.meta_text(entry), new_meta_text)
        self.assertEqual(cache.common.tree_digest(str(entry)), new_digest)
        self.assertFalse(Path(str(entry) + ".backup-tx").exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_window_meta_written_before_journal_cleared_is_finished(self):
        """meta 已写、journal 未清：前滚复写冻结 meta、清 staging/backup/journal。"""
        entry = self.entry("k1", tree_marker="old")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        new_digest = cache.common.tree_digest(str(staging))
        new_meta_text = json.dumps({"schema_version": 1, "key": "k1", "inputs_digest": INPUTS,
                                    "output_tree_digest": new_digest, "deploy": "dev", "version": "",
                                    "ref": "", "pyver": f"{sys.version_info[0]}.{sys.version_info[1]}",
                                    "root": os.path.realpath(entry)}, sort_keys=True) + "\n"
        self.journal(entry, staging, old, meta=new_meta_text)
        fixture_scope.move(entry, Path(str(entry) + ".backup-tx"))
        fixture_scope.move(staging, entry)
        cache._write_json(cache.meta_path(str(entry)), None, new_meta_text)
        self.assertEqual(self.recover(entry), "rolled-forward")
        self.assertEqual(self.meta_text(entry), new_meta_text)
        self.assertFalse(Path(str(entry) + ".backup-tx").exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())

    def test_window_first_publication_partial_install_is_undone(self):
        """首次发布的半安装：只撤销本事务的不完整新代，兄弟条目与 sibling 不动。"""
        keep = self.entry("keep", tree_marker="keep")
        entry = self.root / "k1"
        entry.mkdir()
        (entry / "partial").write_text("half\n", encoding="utf-8")
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, {"present": False})
        shutil.rmtree(staging)            # 半安装：staging 已被移走/丢失，entry 仍不完整
        self.assertEqual(self.recover(entry), "rolled-back-absent")
        self.assertFalse(entry.exists())
        self.assertFalse(staging.exists())
        self.assertFalse(Path(cache.journal_path(str(self.root), "k1")).exists())
        self.assertEqual((keep / "content").read_text(), "keep\n")

    def test_unverifiable_generations_fail_closed(self):
        entry = self.entry("k1")
        old = {"present": True, "digest": cache.common.tree_digest(str(entry)),
               "meta": self.meta_text(entry)}
        staging = Path(str(entry) + ".staging-tx")
        fixture_scope.reset(staging)
        (staging / "content").write_text("new\n", encoding="utf-8")
        self.journal(entry, staging, old)
        (staging / "content").write_text("tampered\n", encoding="utf-8")
        # 旧条目也必须在场且不可验证：否则“旧代原位完好”是合法可恢复窗口（R1 修复）。
        (entry / "content").write_text("tampered-old\n", encoding="utf-8")
        with self.assertRaises(cache.CacheError):
            self.recover(entry)
        self.assertTrue(Path(cache.journal_path(str(self.root), "k1")).exists())


if __name__ == "__main__":
    unittest.main()


# ---- C3：真实发布器的确定性窗口、盘点与退役 ---------------------------------

import hashlib  # noqa: E402
import pty  # noqa: E402
import select  # noqa: E402
import signal  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402

import resource_lifecycle as lifecycle  # noqa: E402


def run_template_cli(command, cache_root, results_dir, scope, env_extra=None, analysis=None):
    env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    env.update({"WF_TEST_SCOPE_ROOT": str(scope),
                "WF_FIXTURE_LEASE_FD": str(analysis["lease_fd"]) if analysis else "",
                "WF_FIXTURE_LEASE_PID": str(analysis["lease_pid"]) if analysis else ""})
    if results_dir:
        env["PYTHONPYCACHEPREFIX"] = str(Path(results_dir) / "pycache")
    env = {key: value for key, value in env.items() if value != ""}
    env.update(env_extra or {})
    args = [sys.executable, str(FULL / "template_cache.py"), command,
            "--cache-root", str(cache_root)]
    if command in ("publish", "acquire", "lookup", "migrate", "key"):
        args += ["--deploy", "dev"]
    if results_dir:
        args += ["--results-dir", str(results_dir)]
    return subprocess.run(args,
                          capture_output=True, text=True, env=env, cwd=str(REPO), timeout=180)


def run_retire_pty(args, env, phrase, timeout=60):
    """真实 PTY：确认提示走 stderr；短语预先写入 tty，等子进程收口。"""
    master, slave = pty.openpty()
    proc = subprocess.Popen([sys.executable, str(FULL / "template_cache.py"), "retire", *args],
                            stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, cwd=str(REPO))
    os.close(slave)
    try:
        time.sleep(0.5)
        try:
            os.write(master, (phrase + "\n").encode())
        except OSError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=10)
            stderr += "\nPTY-CHILD-TIMEOUT"
    finally:
        try:
            os.close(master)
        except OSError:
            pass
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)
    return proc.returncode, stdout, stderr


class CheckpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = fixture_scope.create_test_scope()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scope, ignore_errors=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="cache-", dir=self.scope))
        self.cache_root = self.root / "template"
        self.cache_root.mkdir()
        self.results = self.root / "results"
        self.results.mkdir()

    def publish(self, env_extra=None):
        return run_template_cli("publish", self.cache_root, self.results, self.scope, env_extra)

    def acquire(self, env_extra=None):
        return run_template_cli("acquire", self.cache_root, self.results, self.scope, env_extra)

    def inventory(self):
        proc = run_template_cli("inventory", self.cache_root, None, self.scope)
        return json.loads(proc.stdout)

    def key(self):
        return next(name for name in os.listdir(self.cache_root)
                    if name.endswith("-cHkzLjE0-ZGV2") and not name.endswith((".json", ".owner")))

    def valid_meta(self, key):
        meta = json.loads((self.cache_root / f"{key}.meta.json").read_text())
        import wf_release_common as common
        return (meta["root"] == os.path.realpath(self.cache_root / key)
                and meta["output_tree_digest"] == common.tree_digest(str(self.cache_root / key)))

    def test_w1_to_w5_and_f1_real_publisher_windows(self):
        scenarios = {
            "after-journal": ("rolled-back", True),
            "after-old-moved": ("rolled-back", True),
            "after-new-installed": ("rolled-back", True),
            "after-meta": ("rolled-forward", True),
            "after-material-cleanup-before-journal-remove": ("rolled-forward", True),
        }
        for point, (status, old) in scenarios.items():
            with self.subTest(point=point):
                shutil.rmtree(self.cache_root, ignore_errors=True)
                self.cache_root.mkdir()
                self.assertEqual(self.publish().returncode, 0)
                key = self.key()
                fault = {"WF_TEST_FAULT_INJECTION": "1",
                         "WF_TEMPLATE_TXN_REBUILD": "1",
                         "WF_TEMPLATE_TXN_STOP_AFTER": point}
                failed = self.publish(fault)
                self.assertEqual(failed.returncode, 97, failed.stderr)
                self.assertIn("WF-TEMPLATE-TXN-STOP", failed.stderr)
                recovered = self.acquire()
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
                self.assertIn(f"TEMPLATE-CACHE-RECOVERED: {status}", recovered.stderr)
                self.assertFalse((self.cache_root / f"{key}.journal.json").exists())
                self.assertTrue(self.valid_meta(key))
        # W5：首次发布（old absent）在新代摘要确认前撤销，随后真实入口正常发布。
        shutil.rmtree(self.cache_root, ignore_errors=True)
        self.cache_root.mkdir()
        failed = self.publish({"WF_TEST_FAULT_INJECTION": "1",
                               "WF_TEMPLATE_TXN_STOP_AFTER": "after-new-installed"})
        self.assertEqual(failed.returncode, 97)
        recovered = self.acquire()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn("rolled-back-absent", recovered.stderr)
        self.assertTrue(self.valid_meta(self.key()))

    def test_o1_staging_orphan_is_owned_and_safe_legacy(self):
        failed = self.publish({"WF_TEST_FAULT_INJECTION": "1",
                               "WF_TEMPLATE_TXN_STOP_AFTER": "after-staging-before-journal"})
        self.assertEqual(failed.returncode, 97)
        report = self.inventory()
        self.assertEqual(report["status"], "complete")
        staging = [item for item in report["entries"] if item["kind"] == "template-staging"]
        self.assertEqual(len(staging), 1)
        self.assertEqual(staging[0]["provenance"], "owned")
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "template-cache",
                                         "root": report["root"], "entries": [staging[0]]}))
        retire_report = self.root / "retire.json"
        # 走真实 CLI 时必须带 selection/report；用独立进程避免继承测试进程的 lease 环境。
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env.update({"WF_TEST_SCOPE_ROOT": str(self.scope),
                    "PYTHONPYCACHEPREFIX": str(Path(self.results) / "pycache")})
        proc = subprocess.run([sys.executable, str(FULL / "template_cache.py"), "retire",
                               "--cache-root", str(self.cache_root),
                               "--selection", str(selection),
                               "--retirement-mode", "safe-legacy",
                               "--confirm-retirement", "--report", str(retire_report)],
                              capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(Path(staging[0]["path"]).exists())
        self.assertEqual(json.loads(retire_report.read_text())["results"][0]["state"], "removed")

    def test_rebuild_injection_is_one_shot_and_builds_increment(self):
        self.assertEqual(self.publish().returncode, 0)
        key = self.key()
        before = json.loads((self.cache_root / f"{key}.meta.json").read_text())["builds"]
        proc = self.publish({"WF_TEST_FAULT_INJECTION": "1",
                             "WF_TEMPLATE_TXN_REBUILD": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("TEMPLATE-CACHE-HIT=0", proc.stdout)
        after = json.loads((self.cache_root / f"{key}.meta.json").read_text())["builds"]
        self.assertEqual(after, before + 1)
        second = self.acquire()
        self.assertIn("TEMPLATE-CACHE-HIT=1", second.stdout, "注入只能影响本次命中")
        self.assertEqual(json.loads((self.cache_root / f"{key}.meta.json").read_text())["builds"],
                         after)
        # 成功事务不得留下 staging/backup 的树或兄弟 marker；entry 自身 marker/meta 保留。
        leftovers = [name for name in os.listdir(self.cache_root)
                     if ".staging-" in name or ".backup-" in name]
        self.assertEqual(leftovers, [], f"事务材料/marker 残留：{leftovers}")

    def test_inventory_flags_bad_journal_and_retire_resets_then_rebuilds(self):
        self.assertEqual(self.publish().returncode, 0)
        key = self.key()
        journal = self.cache_root / f"{key}.journal.json"
        journal.write_text("{broken")
        report = self.inventory()
        self.assertEqual(report["status"], "partial")
        self.assertTrue(any(item["kind"] == "journal" and item["blocked"] for item in
                            report["entries"]))
        selection = self.root / "selection.json"
        entries = [item for item in report["entries"]
                   if item["path"] in (str(journal), str(self.cache_root / key))]
        selection.write_text(json.dumps({"schema_version": 1, "domain": "template-cache",
                                         "root": report["root"],
                                         "entries": [item for item in entries]}))
        # 非 TTY 的 manual-retained 必须零删除。
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env.update({"WF_TEST_SCOPE_ROOT": str(self.scope),
                    "PYTHONPYCACHEPREFIX": str(Path(self.results) / "pycache")})
        report_path = self.root / "bad-journal-report.json"
        proc = subprocess.run([sys.executable, str(FULL / "template_cache.py"), "retire",
                               "--cache-root", str(self.cache_root), "--selection", str(selection),
                               "--retirement-mode", "manual-retained", "--confirm-retirement",
                               "--report", str(report_path)],
                              capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("TTY", proc.stderr)
        self.assertTrue((self.cache_root / key).exists())
        self.assertTrue(journal.exists())
        # 真实 PTY 确认后：材料 → marker → journal，最后真实入口重建同 key。
        entries_sorted = lifecycle.selection_entries(
            json.loads(selection.read_text()), "template-cache")
        digest = lifecycle.selection_digest(entries_sorted)
        phrase = f"template-cache {report['root']} {digest} abandon"
        rc, stdout, stderr = run_retire_pty(
            ["--cache-root", str(self.cache_root), "--selection", str(selection),
             "--retirement-mode", "manual-retained", "--confirm-retirement",
             "--report", str(report_path)], env, phrase)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertIn("MANUAL-RETAINED-CONFIRM", stderr)
        self.assertFalse(journal.exists())
        self.assertFalse((self.cache_root / key).exists())
        self.assertFalse((self.cache_root / f"{key}.meta.json").exists(),
                         "条目退役必须同时移除正式 meta")
        rebuilt = self.acquire()
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
        self.assertIn("TEMPLATE-CACHE-HIT=0", rebuilt.stdout)
        self.assertTrue(self.valid_meta(self.key()))

    def test_safe_legacy_refuses_a_current_template_entry(self):
        self.assertEqual(self.publish().returncode, 0)
        report = self.inventory()
        entry = next(item for item in report["entries"] if item["kind"] == "template-entry")
        selection = self.root / "entry.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "template-cache",
                                         "root": report["root"], "entries": [entry]}))
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        proc = subprocess.run([sys.executable, str(FULL / "template_cache.py"), "retire",
                               "--cache-root", str(self.cache_root), "--selection", str(selection),
                               "--retirement-mode", "safe-legacy", "--confirm-retirement",
                               "--report", str(self.root / "entry-report.json")],
                              capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("有效模板条目", proc.stderr)
        self.assertTrue(Path(entry["path"]).exists())

    def test_selection_and_report_outside_scope_are_refused(self):
        self.assertEqual(self.publish().returncode, 0)
        report = self.inventory()
        entry = next(item for item in report["entries"] if item["kind"] == "template-entry")
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "template-cache",
                                         "root": report["root"], "entries": [entry]}))
        outside = Path(tempfile.mkdtemp(prefix="outside-report-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        proc = subprocess.run([sys.executable, str(FULL / "template_cache.py"), "retire",
                               "--cache-root", str(self.cache_root), "--selection", str(selection),
                               "--retirement-mode", "manual-retained", "--confirm-retirement",
                               "--report", str(outside / "report.json")],
                              capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("escapes the test scope", proc.stderr)

    def test_unproven_material_requires_explicit_unproven_confirmation(self):
        orphan = self.cache_root / ("e" * 12 + "-cHkzLjE0-ZGV2.staging-deadbeef")
        orphan.mkdir()
        (orphan / "payload").write_text("x")
        report = self.inventory()
        item = next(entry for entry in report["entries"] if entry["path"] == str(orphan))
        self.assertEqual(item["provenance"], "unproven")
        selection = self.root / "unproven.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "template-cache",
                                         "root": report["root"], "entries": [item]}))
        env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
        env.update({"WF_TEST_SCOPE_ROOT": str(self.scope),
                    "PYTHONPYCACHEPREFIX": str(Path(self.results) / "pycache")})
        # safe-legacy 拒绝 unproven。
        proc = subprocess.run([sys.executable, str(FULL / "template_cache.py"), "retire",
                               "--cache-root", str(self.cache_root), "--selection", str(selection),
                               "--retirement-mode", "safe-legacy", "--confirm-retirement",
                               "--report", str(self.root / "safe.json")],
                              capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(orphan.exists())
        # manual-retained 缺少 unproven-cache 短语 → 零删除。
        digest = lifecycle.selection_digest([item])
        phrase = f"template-cache {report['root']} {digest} abandon"
        report_path = self.root / "unproven-report.json"
        rc, stdout, stderr = run_retire_pty(
            ["--cache-root", str(self.cache_root), "--selection", str(selection),
             "--retirement-mode", "manual-retained", "--confirm-retirement",
             "--report", str(report_path)], env, phrase)
        self.assertNotEqual(rc, 0)
        self.assertTrue(orphan.exists())
        # 正确短语（含 unproven-cache）才删除，并在报告如实保留 unproven 归属事实。
        phrase = f"template-cache {report['root']} {digest} abandon unproven-cache"
        rc, stdout, stderr = run_retire_pty(
            ["--cache-root", str(self.cache_root), "--selection", str(selection),
             "--retirement-mode", "manual-retained", "--confirm-retirement",
             "--report", str(self.root / "unproven-ok.json")], env, phrase)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertFalse(orphan.exists())
        saved = json.loads((self.root / "unproven-ok.json").read_text())
        self.assertEqual(saved["selected"][0]["provenance"], "unproven")

    def test_observe_reports_counts_without_writing(self):
        self.assertEqual(self.publish().returncode, 0)
        template_cache = cache
        report = template_cache.observe(str(self.cache_root))
        self.assertEqual(report["status"], "complete")
        self.assertGreater(sum(report["counts"].values()), 0)
        self.assertIn("inventory", report["inventory_hint"])
        self.assertFalse((self.cache_root / "obs.json").exists())
